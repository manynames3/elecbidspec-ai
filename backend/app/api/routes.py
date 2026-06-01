from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import Integer, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import CompanyProfile, IngestionJob, Opportunity
from app.schemas import (
    CompanyProfileCreate,
    CompanyProfileRead,
    IngestionJobCreate,
    IngestionJobRead,
    OpportunityCreate,
    OpportunityRead,
    ProposalRead,
    SearchRequest,
)
from app.services.classification import classify_bid
from app.services.extraction import extract_specs, parse_attachment
from app.services.fit_scoring import score_fit
from app.services.ingestion.defaults import DEFAULT_PUBLIC_BID_JOBS
from app.services.proposal import generate_proposal_package
from app.services.search import search_opportunities
from app.services.storage import store_upload
from app.services.value_assessment import assess_value, infer_source_type, normalize_bid_status
from app.worker import process_job

router = APIRouter()


def opportunity_to_dict(opportunity: Opportunity) -> dict:
    return {
        "id": opportunity.id,
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


def get_profile_data(db: Session) -> dict | None:
    profile = db.query(CompanyProfile).first()
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
    enriched.update(assess_value(enriched))
    profile = get_profile_data(db)
    if profile:
        enriched.update(score_fit(enriched, profile))
    return enriched


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ElecBidSpec AI"}


@router.get("/opportunities", response_model=list[OpportunityRead])
def list_opportunities(
    db: Session = Depends(get_db),
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
    bid_status: str | None = Query(default=None),
    open_only: bool = Query(default=False),
    real_only: bool = Query(default=False),
) -> list[Opportunity]:
    query = db.query(Opportunity)
    if due_before:
        query = query.filter(Opportunity.due_date <= due_before)
    if due_after:
        query = query.filter(Opportunity.due_date >= due_after)
    if state:
        query = query.filter(Opportunity.state == state.upper())
    if project_type:
        query = query.filter(Opportunity.project_type == project_type)
    if min_fit_score is not None:
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
    if bid_status:
        query = query.filter(Opportunity.bid_status == bid_status)
    if open_only:
        query = query.filter(Opportunity.bid_status == "open")
    if real_only:
        query = query.filter(Opportunity.source != "seed")
    return query.order_by(Opportunity.due_date.asc().nullslast(), Opportunity.fit_score.desc().nullslast()).all()


@router.post("/opportunities", response_model=OpportunityRead, status_code=201)
def create_opportunity(payload: OpportunityCreate, db: Session = Depends(get_db)) -> Opportunity:
    data = enrich_opportunity_data(payload.model_dump(), db)
    opportunity = Opportunity(**data)
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityRead)
def get_opportunity(opportunity_id: int, db: Session = Depends(get_db)) -> Opportunity:
    opportunity = db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity


@router.post("/opportunities/{opportunity_id}/rescore", response_model=OpportunityRead)
def rescore_opportunity(opportunity_id: int, db: Session = Depends(get_db)) -> Opportunity:
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
def get_proposal(opportunity_id: int, db: Session = Depends(get_db)) -> dict:
    opportunity = db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return generate_proposal_package(opportunity_to_dict(opportunity), get_profile_data(db))


@router.post("/search")
def natural_language_search(payload: SearchRequest, db: Session = Depends(get_db)) -> list[dict]:
    opportunities = [opportunity_to_dict(item) for item in db.query(Opportunity).all()]
    results = search_opportunities(payload.query, opportunities)
    return results[:25]


@router.post("/uploads", response_model=OpportunityRead, status_code=201)
async def upload_opportunity_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
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
        "source": "manual_upload",
        "source_type": "manual",
        "source_url": source_url,
        "bid_status": "open",
        "estimated_value": estimated_value,
        "attachments": [attachment],
        "extracted_specs": specs,
    }
    opportunity = Opportunity(**enrich_opportunity_data(data, db))
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.get("/company-profile", response_model=CompanyProfileRead)
def get_company_profile(db: Session = Depends(get_db)) -> CompanyProfile:
    profile = db.query(CompanyProfile).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found. Seed or create a profile first.")
    return profile


@router.put("/company-profile", response_model=CompanyProfileRead)
def upsert_company_profile(payload: CompanyProfileCreate, db: Session = Depends(get_db)) -> CompanyProfile:
    profile = db.query(CompanyProfile).first()
    if profile:
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)
    else:
        profile = CompanyProfile(**payload.model_dump())
        db.add(profile)
    db.commit()
    db.refresh(profile)
    for opportunity in db.query(Opportunity).all():
        enriched = enrich_opportunity_data(opportunity_to_dict(opportunity), db)
        opportunity.fit_score = enriched.get("fit_score")
        opportunity.fit_explanation = enriched.get("fit_explanation")
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/ingestion/jobs", response_model=IngestionJobRead, status_code=202)
def create_ingestion_job(payload: IngestionJobCreate, db: Session = Depends(get_db)) -> IngestionJob:
    from app.services.ingestion.registry import ADAPTERS

    if payload.adapter not in ADAPTERS:
        raise HTTPException(status_code=400, detail=f"Unknown adapter. Available adapters: {', '.join(sorted(ADAPTERS))}.")
    job = IngestionJob(adapter=payload.adapter, params=payload.params, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/ingestion/jobs", response_model=list[IngestionJobRead])
def list_ingestion_jobs(db: Session = Depends(get_db)) -> list[IngestionJob]:
    return db.query(IngestionJob).order_by(IngestionJob.created_at.desc()).limit(50).all()


@router.get("/ingestion/adapters")
def list_ingestion_adapters() -> list[dict]:
    from app.services.ingestion.registry import ADAPTERS

    return [{"name": name, "description": adapter.description} for name, adapter in sorted(ADAPTERS.items())]


@router.get("/ingestion/summary")
def ingestion_summary(db: Session = Depends(get_db)) -> dict:
    source_counts = (
        db.query(
            Opportunity.source,
            Opportunity.source_type,
            func.count(Opportunity.id).label("count"),
            func.sum(func.cast(Opportunity.minimum_value_match, Integer)).label("target_matches"),
            func.max(Opportunity.updated_at).label("last_seen_at"),
        )
        .group_by(Opportunity.source, Opportunity.source_type)
        .order_by(func.count(Opportunity.id).desc())
        .all()
    )
    latest_jobs = db.query(IngestionJob).order_by(IngestionJob.updated_at.desc()).limit(10).all()
    real_count = db.query(Opportunity).filter(Opportunity.source != "seed").count()
    target_count = db.query(Opportunity).filter(Opportunity.source != "seed", Opportunity.minimum_value_match == True).count()  # noqa: E712
    return {
        "real_opportunity_count": real_count,
        "sample_opportunity_count": db.query(Opportunity).filter(Opportunity.source == "seed").count(),
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
    }


@router.post("/ingestion/refresh-defaults")
def refresh_default_ingestion(db: Session = Depends(get_db)) -> dict:
    jobs = []
    for job_spec in DEFAULT_PUBLIC_BID_JOBS:
        job = IngestionJob(
            adapter=job_spec["adapter"],
            params={**job_spec["params"], "manual_refresh": True, "update_existing": True},
            status="queued",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
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
