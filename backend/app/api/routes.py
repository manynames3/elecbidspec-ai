from __future__ import annotations

import hmac
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Response, UploadFile
from sqlalchemy import Integer, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import (
    AlertPreference,
    AlertRun,
    AuthSession,
    CompanyProfile,
    IngestionJob,
    Opportunity,
    OpportunityAttachmentExtraction,
    OpportunityWorkflow,
    SavedSearch,
    User,
)
from app.schemas import (
    AlertPreferenceRead,
    AlertPreferenceUpdate,
    AlertRunRead,
    AttachmentExtractionRead,
    AttachmentIngestionResult,
    CompanyProfileCreate,
    CompanyProfileRead,
    IngestionJobCreate,
    IngestionJobRead,
    LoginRequest,
    LoginResponse,
    OpportunityCreate,
    OpportunityRead,
    OpportunityWorkflowRead,
    OpportunityWorkflowUpdate,
    ProposalRead,
    SavedSearchCreate,
    SavedSearchRead,
    SavedSearchUpdate,
    SearchRequest,
    AccountStatusRead,
    UserRead,
)
from app.services.auth import create_session_token, hash_session_token, session_expiry, verify_password
from app.services.alerts import build_alert_digest, get_or_create_alert_preference
from app.services.attachment_ingestion import ingest_opportunity_attachments
from app.services.classification import classify_bid
from app.services.extraction import extract_specs, parse_attachment
from app.services.fit_scoring import score_fit
from app.services.email_alerts import send_alert_digest_email
from app.services.ingestion.defaults import (
    DEFAULT_SOURCE_CATALOG,
    available_default_public_bid_jobs,
    missing_required_setting,
    skipped_default_public_bid_jobs,
)
from app.services.ingestion.sam_gov import resolve_sam_api_key
from app.services.proposal_cache import enhance_proposal, get_or_create_fast_proposal
from app.services.proposal_docx import generate_proposal_docx
from app.services.proposal_pdf import generate_proposal_pdf
from app.services.search import (
    PROJECT_QUERY_MAP,
    parse_due_before,
    parse_owner_type,
    parse_project_stage,
    parse_state_filter,
    parse_value_threshold,
    search_opportunities,
)
from app.services.storage import store_upload
from app.services.tenancy import PUBLIC_TENANT_ID
from app.services.value_assessment import assess_value, infer_owner_type, infer_project_stage, infer_signal_type, infer_source_type, normalize_bid_status
from app.worker import process_job

router = APIRouter()
SEARCH_CANDIDATE_LIMIT = 500
SEARCH_STOP_WORDS = {
    "above",
    "active",
    "bids",
    "days",
    "does",
    "find",
    "have",
    "into",
    "need",
    "needs",
    "next",
    "open",
    "over",
    "projects",
    "public",
    "require",
    "requires",
    "show",
    "that",
    "the",
    "which",
    "with",
}


def _bearer_token(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _user_from_token(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    token_hash = hash_session_token(token)
    session = (
        db.query(AuthSession)
        .filter(AuthSession.token_hash == token_hash, AuthSession.revoked_at.is_(None))
        .order_by(AuthSession.created_at.desc())
        .first()
    )
    if not session or _aware(session.expires_at) <= datetime.now(timezone.utc):
        return None
    user = db.get(User, session.user_id)
    if not user or not user.is_active:
        return None
    return user


def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    token = _bearer_token(authorization)
    if not token:
        return None
    user = _user_from_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session.")
    return user


def require_user(current_user: User | None = Depends(get_current_user_optional)) -> User:
    if not current_user:
        raise HTTPException(status_code=401, detail="Login required.")
    return current_user


def request_tenant_id(current_user: User | None) -> str:
    if current_user:
        return current_user.tenant_id
    if get_settings().auth_required:
        raise HTTPException(status_code=401, detail="Login required.")
    return "default"


def require_admin(
    authorization: str | None = Header(default=None),
    x_admin_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> None:
    settings = get_settings()
    bearer = _bearer_token(authorization)
    session_user = _user_from_token(db, bearer)
    if session_user and session_user.role == "admin":
        return

    expected = settings.admin_api_token
    if not expected:
        raise HTTPException(status_code=503, detail="Admin API token is not configured.")
    provided = x_admin_token or bearer
    if not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Admin token required.")


def opportunity_to_dict(opportunity: Opportunity) -> dict:
    data = {
        "id": opportunity.id,
        "tenant_id": opportunity.tenant_id,
        "title": opportunity.title,
        "agency": opportunity.agency,
        "location": opportunity.location,
        "state": opportunity.state,
        "due_date": opportunity.due_date,
        "naics_code": opportunity.naics_code,
        "description": opportunity.description,
        "source": opportunity.source,
        "source_type": opportunity.source_type,
        "source_url": opportunity.source_url,
        "bid_status": opportunity.bid_status,
        "project_stage": opportunity.project_stage,
        "signal_type": opportunity.signal_type,
        "owner_type": opportunity.owner_type,
        "forecast_rfp_date": opportunity.forecast_rfp_date,
        "estimated_value": float(opportunity.estimated_value) if opportunity.estimated_value is not None else None,
        "value_confidence": opportunity.value_confidence,
        "value_explanation": opportunity.value_explanation,
        "minimum_value_match": opportunity.minimum_value_match,
        "attachments": opportunity.attachments or [],
        "extracted_specs": opportunity.extracted_specs or {},
        "project_type": opportunity.project_type,
        "confidence_score": opportunity.confidence_score,
        "classification_explanation": opportunity.classification_explanation,
        "fit_score": opportunity.fit_score,
        "fit_explanation": opportunity.fit_explanation,
        "created_at": opportunity.created_at,
        "updated_at": opportunity.updated_at,
    }
    return data


def opportunity_to_dict_for_profile(opportunity: Opportunity, profile: dict | None) -> dict:
    data = opportunity_to_dict(opportunity)
    if profile:
        fit = score_fit(data, profile)
        data["fit_score"] = fit.get("fit_score")
        data["fit_explanation"] = fit.get("fit_explanation")
    return data


def get_profile_data(db: Session) -> dict | None:
    profile = db.query(CompanyProfile).filter(CompanyProfile.tenant_id == "default").first() or db.query(CompanyProfile).first()
    if not profile:
        return None
    return {
        "name": profile.name,
        "states_served": profile.states_served,
        "bonding_capacity": float(profile.bonding_capacity) if profile.bonding_capacity is not None else None,
        "cable_types_supplied": profile.cable_types_supplied,
        "installation_capabilities": profile.installation_capabilities,
        "labor_type": profile.labor_type,
        "experience": profile.experience,
    }


def get_profile_data_for_user(db: Session, current_user: User | None) -> dict | None:
    if not current_user:
        return get_profile_data(db)
    profile = db.query(CompanyProfile).filter(CompanyProfile.tenant_id == current_user.tenant_id).first()
    if not profile:
        return get_profile_data(db)
    return {
        "name": profile.name,
        "states_served": profile.states_served,
        "bonding_capacity": float(profile.bonding_capacity) if profile.bonding_capacity is not None else None,
        "cable_types_supplied": profile.cable_types_supplied,
        "installation_capabilities": profile.installation_capabilities,
        "labor_type": profile.labor_type,
        "experience": profile.experience,
    }


def enrich_opportunity_data(data: dict, db: Session) -> dict:
    specs = data.get("extracted_specs") or extract_specs(data.get("description") or "")
    classification = classify_bid(data.get("title") or "", data.get("description") or "", specs)
    enriched = {
        **data,
        "extracted_specs": specs,
        "project_type": classification["project_type"],
        "confidence_score": classification["confidence_score"],
        "classification_explanation": classification["explanation"],
    }
    inferred_source_type = infer_source_type(enriched.get("source"), enriched.get("agency"))
    if not enriched.get("source_type") or (enriched.get("source_type") == "manual" and inferred_source_type != "manual"):
        enriched["source_type"] = inferred_source_type
    enriched["bid_status"] = normalize_bid_status(enriched.get("bid_status"), enriched.get("due_date"))
    enriched["owner_type"] = infer_owner_type(enriched)
    enriched["project_stage"] = infer_project_stage(enriched)
    enriched["signal_type"] = infer_signal_type(enriched)
    enriched.update(assess_value(enriched))
    profile = get_profile_data(db)
    if profile:
        enriched.update(score_fit(enriched, profile))
    return enriched


def _job_label(job: IngestionJob) -> str:
    params = job.params or {}
    return str(params.get("job_label") or params.get("source") or job.adapter)


def _is_portal_gated_error(error: str | None) -> bool:
    if not error:
        return False
    lower = error.lower()
    return any(
        marker in lower
        for marker in [
            "403",
            "forbidden",
            "cloudflare",
            "akamai",
            "captcha",
            "browser check",
            "just a moment",
            "challenge",
            "certificate_verify_failed",
        ]
    )


def _source_health(source_rows: list, latest_jobs: list[IngestionJob]) -> list[dict]:
    settings = get_settings()
    refresh_hours = settings.default_ingestion_refresh_hours
    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=max(refresh_hours * 2, 12))
    counts_by_source = {
        source: {
            "source": source,
            "source_type": source_type,
            "count": int(count or 0),
            "target_matches": int(target_matches or 0),
            "last_seen_at": last_seen_at,
        }
        for source, source_type, count, target_matches, last_seen_at in source_rows
    }
    jobs_by_label: dict[str, IngestionJob] = {}
    for job in latest_jobs:
        label = _job_label(job)
        if label not in jobs_by_label:
            jobs_by_label[label] = job

    def has_required_setting(name: str | None) -> bool:
        if not name:
            return True
        if name == "sam_gov_api_key":
            return bool(settings.sam_gov_api_key or settings.sam_gov_api_key_secret_arn)
        return bool(getattr(settings, name, None))

    def aware_datetime(value):
        if value and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    health = []
    for catalog in DEFAULT_SOURCE_CATALOG:
        source = catalog["source"]
        latest_job = jobs_by_label.get(source)
        count_row = counts_by_source.get(source)
        missing_setting = catalog.get("requires_setting")
        latest_job_at = aware_datetime(latest_job.updated_at) if latest_job else None
        recently_refreshed = bool(latest_job and latest_job.status == "complete" and latest_job_at and latest_job_at >= stale_cutoff)
        if missing_setting and not has_required_setting(str(missing_setting)):
            status = "missing_config"
        elif latest_job and latest_job.status == "failed" and (_is_portal_gated_error(latest_job.error) or catalog.get("portal_gated")):
            status = "portal_gated"
        elif latest_job and latest_job.status == "failed":
            status = "failed"
        elif catalog.get("portal_gated") and (not count_row or not count_row["count"]):
            status = "portal_gated"
        elif catalog.get("covered_by_source") and (not count_row or not count_row["count"]):
            status = "covered_by_source"
        elif catalog.get("directory_only") and (not count_row or not count_row["count"]):
            status = "directory_only"
        elif latest_job and latest_job.status == "complete" and (not count_row or not count_row["count"]):
            status = "no_current_matches"
        elif not count_row or not count_row["count"]:
            status = "no_records"
        elif recently_refreshed:
            status = "healthy"
        else:
            last_seen = aware_datetime(count_row.get("last_seen_at"))
            status = "stale" if last_seen and last_seen < stale_cutoff else "healthy"

        health.append(
            {
                **catalog,
                "status": status,
                "count": count_row["count"] if count_row else 0,
                "target_matches": count_row["target_matches"] if count_row else 0,
                "last_seen_at": count_row.get("last_seen_at") if count_row else None,
                "last_job_status": latest_job.status if latest_job else None,
                "last_job_error": latest_job.error if latest_job else None,
                "last_job_at": latest_job.updated_at if latest_job else None,
            }
        )
    return health


def _source_count_rows(db: Session) -> list:
    return (
        db.query(
            Opportunity.source,
            Opportunity.source_type,
            func.count(Opportunity.id).label("count"),
            func.sum(func.cast(Opportunity.minimum_value_match, Integer)).label("target_matches"),
            func.max(Opportunity.updated_at).label("last_seen_at"),
        )
        .filter(Opportunity.tenant_id == PUBLIC_TENANT_ID)
        .group_by(Opportunity.source, Opportunity.source_type)
        .order_by(func.count(Opportunity.id).desc())
        .all()
    )


def _visible_opportunities_query(db: Session, current_user: User | None):
    query = db.query(Opportunity)
    if current_user:
        return query.filter(or_(Opportunity.tenant_id == PUBLIC_TENANT_ID, Opportunity.tenant_id == current_user.tenant_id))
    return query.filter(Opportunity.tenant_id == PUBLIC_TENANT_ID)


def _get_visible_opportunity(db: Session, opportunity_id: int, current_user: User | None) -> Opportunity | None:
    return _visible_opportunities_query(db, current_user).filter(Opportunity.id == opportunity_id).first()


def _search_text_terms(user_query: str) -> list[str]:
    lower_query = user_query.lower()
    phrases = [phrase for phrase in PROJECT_QUERY_MAP if " " in phrase and phrase in lower_query]
    words = [
        word
        for word in {item for item in lower_query.replace("$", " ").split() if len(item) > 3}
        if word not in SEARCH_STOP_WORDS and not word.isdigit()
    ]
    return [*phrases, *sorted(words)[:8]]


def _candidate_opportunities_for_search(db: Session, user_query: str, current_user: User | None) -> list[Opportunity]:
    query = _visible_opportunities_query(db, current_user)
    lower_query = user_query.lower()
    desired_project_type = next((ptype for phrase, ptype in PROJECT_QUERY_MAP.items() if phrase in lower_query), None)
    desired_state = parse_state_filter(user_query)
    desired_project_stage = parse_project_stage(user_query)
    desired_owner_type = parse_owner_type(user_query)
    due_before = parse_due_before(user_query)
    value_threshold = parse_value_threshold(user_query)

    if any(term in lower_query for term in ["open", "active", "bidding", "solicitation"]):
        query = query.filter(Opportunity.bid_status == "open")
    if desired_project_type:
        query = query.filter(Opportunity.project_type == desired_project_type)
    if desired_project_stage:
        query = query.filter(Opportunity.project_stage == desired_project_stage)
    if desired_owner_type:
        query = query.filter(Opportunity.owner_type == desired_owner_type)
    if desired_state:
        query = query.filter(Opportunity.state == desired_state)
    if due_before:
        query = query.filter(Opportunity.due_date.is_not(None), Opportunity.due_date <= due_before)
    if value_threshold:
        value_filter = Opportunity.estimated_value >= Decimal(value_threshold)
        if value_threshold <= 5_000_000:
            value_filter = or_(value_filter, Opportunity.minimum_value_match == True)  # noqa: E712
        query = query.filter(value_filter)

    text_clauses = []
    for term in _search_text_terms(user_query):
        pattern = f"%{term}%"
        text_clauses.extend(
            [
                Opportunity.title.ilike(pattern),
                Opportunity.description.ilike(pattern),
                Opportunity.agency.ilike(pattern),
                Opportunity.source_type.ilike(pattern),
                Opportunity.signal_type.ilike(pattern),
                Opportunity.owner_type.ilike(pattern),
            ]
        )
    if text_clauses:
        query = query.filter(or_(*text_clauses))

    ordered_query = query.order_by(
        Opportunity.minimum_value_match.desc(),
        Opportunity.fit_score.desc(),
        Opportunity.updated_at.desc(),
    )
    candidates = ordered_query.limit(SEARCH_CANDIDATE_LIMIT).all()
    if candidates:
        return candidates

    fallback_query = _visible_opportunities_query(db, current_user)
    if text_clauses:
        fallback_query = fallback_query.filter(or_(*text_clauses))
    return (
        fallback_query.order_by(
            Opportunity.minimum_value_match.desc(),
            Opportunity.fit_score.desc(),
            Opportunity.updated_at.desc(),
        )
        .limit(SEARCH_CANDIDATE_LIMIT)
        .all()
    )


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ElecBidSpec AI"}


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    raw_token = create_session_token()
    expires_at = session_expiry(get_settings().auth_session_ttl_hours)
    db.add(AuthSession(user_id=user.id, token_hash=hash_session_token(raw_token), expires_at=expires_at))
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return {"token": raw_token, "user": user, "expires_at": expires_at}


@router.get("/auth/me", response_model=UserRead)
def get_me(current_user: User = Depends(require_user)) -> User:
    return current_user


@router.post("/auth/logout")
def logout(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_user),
) -> dict:
    token = _bearer_token(authorization)
    if token:
        session = db.query(AuthSession).filter(AuthSession.token_hash == hash_session_token(token), AuthSession.revoked_at.is_(None)).first()
        if session:
            session.revoked_at = datetime.now(timezone.utc)
            db.commit()
    return {"status": "ok"}


@router.get("/account/status", response_model=AccountStatusRead)
def account_status(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict:
    tenant_id = current_user.tenant_id if current_user else "default"
    role = current_user.role if current_user else "demo"
    source_rows = _source_count_rows(db)
    latest_jobs = db.query(IngestionJob).order_by(IngestionJob.updated_at.desc()).limit(50).all()
    source_health = _source_health(source_rows, latest_jobs)
    tenant_profile = db.query(CompanyProfile).filter(CompanyProfile.tenant_id == tenant_id).first() if current_user else None
    profile = tenant_profile or db.query(CompanyProfile).filter(CompanyProfile.tenant_id == "default").first()
    alert_preference = db.query(AlertPreference).filter(AlertPreference.tenant_id == tenant_id).first() if current_user else None
    authenticated = bool(current_user)
    return {
        "authenticated": authenticated,
        "user": current_user,
        "role": role,
        "tenant_id": tenant_id,
        "plan": "paid_pilot" if authenticated else "demo_preview",
        "plan_label": "Paid pilot workspace" if authenticated else "Demo preview",
        "feature_flags": {
            "admin_refresh": bool(current_user and current_user.role == "admin"),
            "ai_enhance": authenticated,
            "proposal_exports": authenticated,
            "saved_search_alerts": authenticated,
            "custom_source_requests": authenticated,
        },
        "onboarding": {
            "has_profile": bool(tenant_profile) if current_user else False,
            "saved_search_count": db.query(SavedSearch).filter(SavedSearch.tenant_id == tenant_id).count() if current_user else 0,
            "alert_configured": bool(alert_preference and alert_preference.enabled and alert_preference.email_to),
            "source_summary_loaded": bool(source_health),
            "live_importing_sources": len([source for source in source_health if source["status"] == "healthy"]),
            "total_sources": len(source_health),
            "real_opportunity_count": db.query(Opportunity).filter(Opportunity.tenant_id == PUBLIC_TENANT_ID, Opportunity.source != "seed").count(),
        },
    }


@router.get("/opportunities", response_model=list[OpportunityRead])
def list_opportunities(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
    due_before: date | None = Query(default=None),
    due_after: date | None = Query(default=None),
    state: str | None = Query(default=None, min_length=2, max_length=2),
    project_type: str | None = Query(default=None),
    min_fit_score: int | None = Query(default=None, ge=0, le=100),
    min_value: Decimal | None = Query(default=None),
    minimum_value_match: bool | None = Query(default=None),
    value_confidence: str | None = Query(default=None),
    source: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    project_stage: str | None = Query(default=None),
    signal_type: str | None = Query(default=None),
    owner_type: str | None = Query(default=None),
    bid_status: str | None = Query(default=None),
    open_only: bool = Query(default=False),
    real_only: bool = Query(default=False),
    saved_only: bool = Query(default=False),
    watched_only: bool = Query(default=False),
    include_hidden: bool = Query(default=False),
) -> list[dict]:
    query = _visible_opportunities_query(db, current_user)
    if (saved_only or watched_only or include_hidden) and not current_user:
        raise HTTPException(status_code=401, detail="Login required for workflow filters.")
    tenant_id = current_user.tenant_id if current_user else None
    if current_user and not include_hidden:
        hidden_select = (
            select(OpportunityWorkflow.opportunity_id)
            .filter(OpportunityWorkflow.tenant_id == tenant_id, OpportunityWorkflow.hidden == True)  # noqa: E712
        )
        query = query.filter(Opportunity.id.notin_(hidden_select))
    if current_user and (saved_only or watched_only):
        workflow_query = db.query(OpportunityWorkflow.opportunity_id).filter(OpportunityWorkflow.tenant_id == tenant_id)
        if saved_only:
            workflow_query = workflow_query.filter(OpportunityWorkflow.saved == True)  # noqa: E712
        if watched_only:
            workflow_query = workflow_query.filter(OpportunityWorkflow.watched == True)  # noqa: E712
        query = query.filter(Opportunity.id.in_(workflow_query.subquery()))
    if due_before:
        query = query.filter(Opportunity.due_date <= due_before)
    if due_after:
        query = query.filter(Opportunity.due_date >= due_after)
    if state:
        query = query.filter(Opportunity.state == state.upper())
    if project_type:
        query = query.filter(Opportunity.project_type == project_type)
    tenant_profile = get_profile_data_for_user(db, current_user) if current_user else None
    if min_fit_score is not None and not current_user:
        query = query.filter(Opportunity.fit_score >= min_fit_score)
    if min_value is not None:
        query = query.filter(Opportunity.estimated_value >= min_value)
    if minimum_value_match is not None:
        query = query.filter(Opportunity.minimum_value_match == minimum_value_match)
    if value_confidence:
        query = query.filter(Opportunity.value_confidence == value_confidence)
    if source:
        query = query.filter(Opportunity.source == source)
    if source_type:
        query = query.filter(Opportunity.source_type == source_type)
    if project_stage:
        query = query.filter(Opportunity.project_stage == project_stage)
    if signal_type:
        query = query.filter(Opportunity.signal_type == signal_type)
    if owner_type:
        query = query.filter(Opportunity.owner_type == owner_type)
    if bid_status:
        query = query.filter(Opportunity.bid_status == bid_status)
    if open_only:
        query = query.filter(Opportunity.bid_status == "open")
    if real_only:
        query = query.filter(Opportunity.source != "seed")
    opportunities = query.order_by(Opportunity.due_date.asc().nullslast(), Opportunity.fit_score.desc().nullslast()).all()
    records = [opportunity_to_dict_for_profile(opportunity, tenant_profile) for opportunity in opportunities]
    if min_fit_score is not None and current_user:
        records = [record for record in records if (record.get("fit_score") or 0) >= min_fit_score]
    return records


@router.post("/opportunities", response_model=OpportunityRead, status_code=201)
def create_opportunity(
    payload: OpportunityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> Opportunity:
    data = enrich_opportunity_data({**payload.model_dump(), "tenant_id": current_user.tenant_id}, db)
    profile = get_profile_data_for_user(db, current_user)
    if profile:
        data.update(score_fit(data, profile))
    opportunity = Opportunity(**data)
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityRead)
def get_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict:
    opportunity = _get_visible_opportunity(db, opportunity_id, current_user)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    profile = get_profile_data_for_user(db, current_user) if current_user else None
    return opportunity_to_dict_for_profile(opportunity, profile)


def _get_or_create_workflow(db: Session, opportunity_id: int, tenant_id: str) -> OpportunityWorkflow:
    workflow = (
        db.query(OpportunityWorkflow)
        .filter(OpportunityWorkflow.opportunity_id == opportunity_id, OpportunityWorkflow.tenant_id == tenant_id)
        .first()
    )
    if workflow:
        return workflow
    workflow = OpportunityWorkflow(opportunity_id=opportunity_id, tenant_id=tenant_id)
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("/opportunities/{opportunity_id}/workflow", response_model=OpportunityWorkflowRead)
def get_opportunity_workflow(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> OpportunityWorkflow:
    if not _get_visible_opportunity(db, opportunity_id, current_user):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return _get_or_create_workflow(db, opportunity_id, request_tenant_id(current_user))


@router.put("/opportunities/{opportunity_id}/workflow", response_model=OpportunityWorkflowRead)
def update_opportunity_workflow(
    opportunity_id: int,
    payload: OpportunityWorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> OpportunityWorkflow:
    if not _get_visible_opportunity(db, opportunity_id, current_user):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    workflow = _get_or_create_workflow(db, opportunity_id, request_tenant_id(current_user))
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(workflow, key, value)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("/workflow/opportunities")
def list_workflow_opportunities(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    saved_only: bool = Query(default=True),
    watched_only: bool = Query(default=False),
) -> list[dict]:
    tenant_id = request_tenant_id(current_user)
    workflow_query = db.query(OpportunityWorkflow).filter(OpportunityWorkflow.tenant_id == tenant_id, OpportunityWorkflow.hidden == False)  # noqa: E712
    if saved_only:
        workflow_query = workflow_query.filter(OpportunityWorkflow.saved == True)  # noqa: E712
    if watched_only:
        workflow_query = workflow_query.filter(OpportunityWorkflow.watched == True)  # noqa: E712
    rows = workflow_query.order_by(OpportunityWorkflow.updated_at.desc()).limit(100).all()
    if not rows:
        return []
    opportunities_by_id = {item.id: item for item in _visible_opportunities_query(db, current_user).filter(Opportunity.id.in_([row.opportunity_id for row in rows])).all()}
    return [
        {"workflow": row, "opportunity": opportunity_to_dict(opportunities_by_id[row.opportunity_id])}
        for row in rows
        if row.opportunity_id in opportunities_by_id
    ]


@router.post("/opportunities/{opportunity_id}/rescore", response_model=OpportunityRead)
def rescore_opportunity(
    opportunity_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> Opportunity:
    opportunity = db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    enriched = enrich_opportunity_data(opportunity_to_dict(opportunity), db)
    for key, value in enriched.items():
        if hasattr(opportunity, key) and key not in {"id", "created_at", "updated_at"}:
            setattr(opportunity, key, value)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.get("/opportunities/{opportunity_id}/proposal", response_model=ProposalRead)
def get_proposal(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> dict:
    opportunity = _get_visible_opportunity(db, opportunity_id, current_user)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    tenant_id = current_user.tenant_id if current_user else PUBLIC_TENANT_ID
    return get_or_create_fast_proposal(
        db,
        opportunity,
        get_profile_data_for_user(db, current_user),
        tenant_id,
        opportunity_to_dict,
    )


@router.post("/opportunities/{opportunity_id}/proposal/enhance", response_model=ProposalRead)
def enhance_opportunity_proposal(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> dict:
    opportunity = _get_visible_opportunity(db, opportunity_id, current_user)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return enhance_proposal(
        db,
        opportunity,
        get_profile_data_for_user(db, current_user),
        current_user.tenant_id,
        opportunity_to_dict,
    )


@router.get("/opportunities/{opportunity_id}/proposal.docx")
def download_proposal_docx(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> Response:
    opportunity = _get_visible_opportunity(db, opportunity_id, current_user)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opportunity_data = opportunity_to_dict(opportunity)
    profile = get_profile_data_for_user(db, current_user)
    proposal = get_or_create_fast_proposal(db, opportunity, profile, current_user.tenant_id, opportunity_to_dict)
    content = generate_proposal_docx(opportunity_data, proposal, profile)
    filename = "".join(char if char.isalnum() else "-" for char in opportunity.title.lower()).strip("-")[:80] or "proposal"
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}-proposal.docx"'},
    )


@router.get("/opportunities/{opportunity_id}/proposal.pdf")
def download_proposal_pdf(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> Response:
    opportunity = _get_visible_opportunity(db, opportunity_id, current_user)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    opportunity_data = opportunity_to_dict(opportunity)
    profile = get_profile_data_for_user(db, current_user)
    proposal = get_or_create_fast_proposal(db, opportunity, profile, current_user.tenant_id, opportunity_to_dict)
    content = generate_proposal_pdf(opportunity_data, proposal, profile)
    filename = "".join(char if char.isalnum() else "-" for char in opportunity.title.lower()).strip("-")[:80] or "proposal"
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}-proposal.pdf"'},
    )


@router.post("/search")
def natural_language_search(
    payload: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> list[dict]:
    profile = get_profile_data_for_user(db, current_user) if current_user else None
    opportunities = [opportunity_to_dict_for_profile(item, profile) for item in _candidate_opportunities_for_search(db, payload.query, current_user)]
    results = search_opportunities(payload.query, opportunities)
    return results[:25]


@router.post("/uploads", response_model=OpportunityRead, status_code=201)
async def upload_opportunity_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    title: str | None = Form(default=None),
    agency: str | None = Form(default=None),
    location: str | None = Form(default=None),
    state: str | None = Form(default=None),
    due_date: date | None = Form(default=None),
    naics_code: str | None = Form(default=None),
    estimated_value: Decimal | None = Form(default=None),
    source_url: str | None = Form(default=None),
) -> Opportunity:
    content = await file.read()
    attachment = store_upload(content, file.filename, file.content_type)

    text = parse_attachment(content, file.filename or attachment["stored_path"])
    specs = extract_specs(text)
    data = {
        "title": title or Path(file.filename or "Uploaded RFP").stem,
        "agency": agency,
        "location": location,
        "state": state.upper() if state else None,
        "due_date": due_date,
        "naics_code": naics_code,
        "description": text[:6000],
        "tenant_id": current_user.tenant_id,
        "source": "manual_upload",
        "source_type": "manual",
        "source_url": source_url,
        "bid_status": "open",
        "estimated_value": estimated_value,
        "attachments": [attachment],
        "extracted_specs": specs,
    }
    enriched = enrich_opportunity_data(data, db)
    profile = get_profile_data_for_user(db, current_user)
    if profile:
        enriched.update(score_fit(enriched, profile))
    opportunity = Opportunity(**enriched)
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.post("/opportunities/{opportunity_id}/attachments/ingest", response_model=AttachmentIngestionResult)
def ingest_opportunity_documents(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
    max_links: int = Query(default=8, ge=1, le=20),
) -> dict:
    opportunity = _get_visible_opportunity(db, opportunity_id, current_user)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    extractions = ingest_opportunity_attachments(db, opportunity, max_links=max_links)
    enriched = enrich_opportunity_data(opportunity_to_dict(opportunity), db)
    for key, value in enriched.items():
        if hasattr(opportunity, key) and key not in {"id", "created_at", "updated_at"}:
            setattr(opportunity, key, value)
    db.commit()
    db.refresh(opportunity)
    return {"opportunity": opportunity, "extractions": extractions}


@router.get("/opportunities/{opportunity_id}/attachments/extractions", response_model=list[AttachmentExtractionRead])
def list_attachment_extractions(
    opportunity_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> list[OpportunityAttachmentExtraction]:
    if not _get_visible_opportunity(db, opportunity_id, current_user):
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return (
        db.query(OpportunityAttachmentExtraction)
        .filter(OpportunityAttachmentExtraction.opportunity_id == opportunity_id)
        .order_by(OpportunityAttachmentExtraction.updated_at.desc())
        .all()
    )


@router.get("/company-profile", response_model=CompanyProfileRead)
def get_company_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> CompanyProfile:
    profile = (
        db.query(CompanyProfile).filter(CompanyProfile.tenant_id == current_user.tenant_id).first()
        or db.query(CompanyProfile).filter(CompanyProfile.tenant_id == "default").first()
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found. Seed or create a profile first.")
    return profile


@router.put("/company-profile", response_model=CompanyProfileRead)
def upsert_company_profile(
    payload: CompanyProfileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> CompanyProfile:
    tenant_id = current_user.tenant_id
    profile = db.query(CompanyProfile).filter(CompanyProfile.tenant_id == tenant_id).first()
    if profile:
        for key, value in {**payload.model_dump(), "tenant_id": tenant_id}.items():
            setattr(profile, key, value)
    else:
        profile = CompanyProfile(**{**payload.model_dump(), "tenant_id": tenant_id})
        db.add(profile)
    db.commit()
    db.refresh(profile)
    profile_data = {
        "name": profile.name,
        "states_served": profile.states_served,
        "bonding_capacity": float(profile.bonding_capacity) if profile.bonding_capacity is not None else None,
        "cable_types_supplied": profile.cable_types_supplied,
        "installation_capabilities": profile.installation_capabilities,
        "labor_type": profile.labor_type,
        "experience": profile.experience,
    }
    for opportunity in db.query(Opportunity).filter(Opportunity.tenant_id == tenant_id).all():
        fit = score_fit(opportunity_to_dict(opportunity), profile_data)
        opportunity.fit_score = fit.get("fit_score")
        opportunity.fit_explanation = fit.get("fit_explanation")
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/alerts/preferences", response_model=AlertPreferenceRead)
def get_alert_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> AlertPreference:
    return get_or_create_alert_preference(db, current_user.tenant_id)


@router.put("/alerts/preferences", response_model=AlertPreferenceRead)
def update_alert_preferences(
    payload: AlertPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> AlertPreference:
    preference = get_or_create_alert_preference(db, current_user.tenant_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(preference, key, value)
    db.commit()
    db.refresh(preference)
    return preference


@router.get("/saved-searches", response_model=list[SavedSearchRead])
def list_saved_searches(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> list[SavedSearch]:
    tenant_id = current_user.tenant_id
    return db.query(SavedSearch).filter(SavedSearch.tenant_id == tenant_id).order_by(SavedSearch.updated_at.desc()).all()


@router.post("/saved-searches", response_model=SavedSearchRead, status_code=201)
def create_saved_search(
    payload: SavedSearchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> SavedSearch:
    tenant_id = current_user.tenant_id
    name = payload.name.strip()
    existing = db.query(SavedSearch).filter(SavedSearch.tenant_id == tenant_id, SavedSearch.name == name).first()
    data = payload.model_dump()
    data["name"] = name
    data["tenant_id"] = tenant_id
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    saved_search = SavedSearch(**data)
    db.add(saved_search)
    db.commit()
    db.refresh(saved_search)
    return saved_search


@router.put("/saved-searches/{saved_search_id}", response_model=SavedSearchRead)
def update_saved_search(
    saved_search_id: int,
    payload: SavedSearchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> SavedSearch:
    tenant_id = current_user.tenant_id
    saved_search = db.query(SavedSearch).filter(SavedSearch.id == saved_search_id, SavedSearch.tenant_id == tenant_id).first()
    if not saved_search:
        raise HTTPException(status_code=404, detail="Saved search not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(saved_search, key, value.strip() if key == "name" and isinstance(value, str) else value)
    db.commit()
    db.refresh(saved_search)
    return saved_search


@router.delete("/saved-searches/{saved_search_id}", status_code=204)
def delete_saved_search(
    saved_search_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> Response:
    tenant_id = current_user.tenant_id
    saved_search = db.query(SavedSearch).filter(SavedSearch.id == saved_search_id, SavedSearch.tenant_id == tenant_id).first()
    if not saved_search:
        raise HTTPException(status_code=404, detail="Saved search not found.")
    db.delete(saved_search)
    db.commit()
    return Response(status_code=204)


@router.post("/alerts/run", response_model=AlertRunRead)
def run_alert_digest(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> AlertRun:
    tenant_id = current_user.tenant_id
    preference = get_or_create_alert_preference(db, tenant_id)
    digest = build_alert_digest(db, tenant_id, preference, get_profile_data_for_user(db, current_user))
    delivery = send_alert_digest_email(preference.email_to if preference.enabled else None, digest)
    run = AlertRun(
        tenant_id=tenant_id,
        status=delivery["status"] or "complete",
        digest=digest,
        sent_to=preference.email_to if preference.enabled and preference.email_to and delivery["status"] == "sent" else None,
        error=delivery["error"],
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("/alerts/latest", response_model=AlertRunRead)
def get_latest_alert_digest(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
) -> AlertRun:
    run = (
        db.query(AlertRun)
        .filter(AlertRun.tenant_id == current_user.tenant_id)
        .order_by(AlertRun.created_at.desc())
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail="No alert digest has been generated yet.")
    return run


@router.post("/ingestion/jobs", response_model=IngestionJobRead, status_code=202)
def create_ingestion_job(
    payload: IngestionJobCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> IngestionJob:
    from app.services.ingestion.registry import ADAPTERS

    if payload.adapter not in ADAPTERS:
        raise HTTPException(status_code=400, detail=f"Unknown adapter. Available adapters: {', '.join(sorted(ADAPTERS))}.")
    job = IngestionJob(adapter=payload.adapter, params=payload.params, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/ingestion/jobs", response_model=list[IngestionJobRead])
def list_ingestion_jobs(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> list[IngestionJob]:
    return db.query(IngestionJob).order_by(IngestionJob.created_at.desc()).limit(50).all()


@router.get("/ingestion/adapters")
def list_ingestion_adapters() -> list[dict]:
    from app.services.ingestion.registry import ADAPTERS

    return [{"name": name, "description": adapter.description} for name, adapter in sorted(ADAPTERS.items())]


@router.get("/ingestion/sam-gov/status")
def sam_gov_status() -> dict:
    settings = get_settings()
    api_key = resolve_sam_api_key()
    return {
        "configured": bool(api_key),
        "source": "env" if settings.sam_gov_api_key else "secrets_manager" if settings.sam_gov_api_key_secret_arn else None,
        "base_url": settings.sam_gov_api_base_url,
    }


@router.post("/ingestion/sam-gov/verify", response_model=IngestionJobRead)
def verify_sam_gov(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> IngestionJob:
    if not resolve_sam_api_key():
        raise HTTPException(status_code=503, detail="SAM_GOV_API_KEY or SAM_GOV_API_KEY_SECRET_ARN is not configured.")
    job = IngestionJob(
        adapter="sam_gov",
        params={
            "job_label": "sam_gov",
            "limit": 5,
            "posted_window_days": 30,
            "ptype": "o",
            "status": "active",
            "keyword": "electrical cable OR high voltage OR medium voltage OR substation OR conduit OR transformer",
            "update_existing": True,
            "verify": True,
        },
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    try:
        process_job(db, job)
    except Exception as exc:  # noqa: BLE001 - persist SAM verification failure for admin inspection
        job.status = "failed"
        job.error = str(exc)
        db.commit()
    db.refresh(job)
    return job


@router.get("/ingestion/summary")
def ingestion_summary(db: Session = Depends(get_db)) -> dict:
    source_counts = _source_count_rows(db)
    latest_jobs = db.query(IngestionJob).order_by(IngestionJob.updated_at.desc()).limit(50).all()
    real_count = db.query(Opportunity).filter(Opportunity.tenant_id == PUBLIC_TENANT_ID, Opportunity.source != "seed").count()
    target_count = db.query(Opportunity).filter(Opportunity.tenant_id == PUBLIC_TENANT_ID, Opportunity.source != "seed", Opportunity.minimum_value_match == True).count()  # noqa: E712
    return {
        "real_opportunity_count": real_count,
        "sample_opportunity_count": db.query(Opportunity).filter(Opportunity.tenant_id == PUBLIC_TENANT_ID, Opportunity.source == "seed").count(),
        "real_target_match_count": target_count,
        "sources": [
            {
                "source": source,
                "source_type": source_type,
                "count": count,
                "target_matches": int(target_matches or 0),
                "last_seen_at": last_seen_at,
            }
            for source, source_type, count, target_matches, last_seen_at in source_counts
        ],
        "latest_jobs": [
            {
                "id": job.id,
                "adapter": job.adapter,
                "status": job.status,
                "result": job.result or {},
                "error": job.error,
                "updated_at": job.updated_at,
            }
            for job in latest_jobs
        ],
        "source_health": _source_health(source_counts, latest_jobs),
    }


@router.post("/ingestion/refresh-defaults")
def refresh_default_ingestion(
    db: Session = Depends(get_db),
    process_portals_inline: bool = Query(default=False),
    _: None = Depends(require_admin),
) -> dict:
    jobs = []
    settings = get_settings()
    for skipped_spec in skipped_default_public_bid_jobs(settings):
        jobs.append(
            {
                "id": 0,
                "adapter": skipped_spec["adapter"],
                "status": "skipped",
                "result": {"skipped": 1},
                "error": f"Missing required setting: {missing_required_setting(settings, skipped_spec)}",
                "updated_at": datetime.now(timezone.utc),
            }
        )
    for job_spec in available_default_public_bid_jobs(settings):
        job = IngestionJob(
            adapter=job_spec["adapter"],
            params={**job_spec["params"], "manual_refresh": True, "update_existing": True},
            status="queued",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        if job.adapter == "public_portal_links" and not process_portals_inline:
            job.result = {"queued": 1}
            db.commit()
        else:
            try:
                process_job(db, job)
            except Exception as exc:  # noqa: BLE001 - source refresh should report per-source failures
                job.status = "failed"
                job.error = str(exc)
                db.commit()
        db.refresh(job)
        jobs.append(
            {
                "id": job.id,
                "adapter": job.adapter,
                "status": job.status,
                "result": job.result or {},
                "error": job.error,
                "updated_at": job.updated_at,
            }
        )
    return {"jobs": jobs}
