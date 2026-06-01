from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Query, Session

from app.models import AlertPreference, IngestionJob, Opportunity, OpportunityWorkflow, SavedSearch
from app.services.search import search_opportunities


def _json_safe(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value


def _opportunity_card(opportunity: Opportunity) -> dict:
    return _json_safe(
        {
            "id": opportunity.id,
            "title": opportunity.title,
            "agency": opportunity.agency,
            "state": opportunity.state,
            "location": opportunity.location,
            "due_date": opportunity.due_date,
            "source": opportunity.source,
            "source_type": opportunity.source_type,
            "source_url": opportunity.source_url,
            "estimated_value": opportunity.estimated_value,
            "value_confidence": opportunity.value_confidence,
            "minimum_value_match": opportunity.minimum_value_match,
            "project_type": opportunity.project_type,
            "fit_score": opportunity.fit_score,
            "fit_explanation": opportunity.fit_explanation,
        }
    )


def _opportunity_search_record(opportunity: Opportunity) -> dict:
    record = _opportunity_card(opportunity)
    record["description"] = opportunity.description
    record["extracted_specs"] = opportunity.extracted_specs or {}
    record["bid_status"] = opportunity.bid_status
    return _json_safe(record)


def _coerce_bool(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _coerce_date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _apply_saved_search_filters(query: Query, filters: Mapping[str, Any]) -> Query:
    due_before = _coerce_date(filters.get("due_before"))
    due_after = _coerce_date(filters.get("due_after"))
    if due_before:
        query = query.filter(Opportunity.due_date <= due_before)
    if due_after:
        query = query.filter(Opportunity.due_date >= due_after)
    if filters.get("state"):
        query = query.filter(Opportunity.state == str(filters["state"]).upper()[:2])
    if filters.get("project_type"):
        query = query.filter(Opportunity.project_type == filters["project_type"])
    if filters.get("min_fit_score") not in (None, ""):
        query = query.filter(Opportunity.fit_score >= int(filters["min_fit_score"]))
    if filters.get("min_value") not in (None, ""):
        query = query.filter(Opportunity.estimated_value >= Decimal(str(filters["min_value"])))
    minimum_value_match = _coerce_bool(filters.get("minimum_value_match"))
    if minimum_value_match is not None:
        query = query.filter(Opportunity.minimum_value_match == minimum_value_match)
    if filters.get("value_confidence"):
        query = query.filter(Opportunity.value_confidence == filters["value_confidence"])
    if filters.get("source"):
        query = query.filter(Opportunity.source == filters["source"])
    if filters.get("source_type"):
        query = query.filter(Opportunity.source_type == filters["source_type"])
    if filters.get("bid_status"):
        query = query.filter(Opportunity.bid_status == filters["bid_status"])
    if _coerce_bool(filters.get("open_only")):
        query = query.filter(Opportunity.bid_status == "open")
    if _coerce_bool(filters.get("real_only")):
        query = query.filter(Opportunity.source != "seed")
    return query


def saved_search_results(db: Session, tenant_id: str, saved_search: SavedSearch, limit: int = 10) -> list[dict]:
    filters = saved_search.filters or {}
    hidden_ids = {
        item.opportunity_id
        for item in db.query(OpportunityWorkflow.opportunity_id)
        .filter(OpportunityWorkflow.tenant_id == tenant_id, OpportunityWorkflow.hidden == True)  # noqa: E712
        .all()
    }
    query = _apply_saved_search_filters(db.query(Opportunity), filters)
    if hidden_ids:
        query = query.filter(Opportunity.id.notin_(hidden_ids))

    opportunities = query.order_by(Opportunity.due_date.asc().nullslast(), Opportunity.fit_score.desc().nullslast()).limit(250).all()
    if saved_search.query and saved_search.query.strip():
        ranked = search_opportunities(saved_search.query, [_opportunity_search_record(item) for item in opportunities])
        return ranked[:limit]
    return [
        {
            "opportunity": _opportunity_card(item),
            "rank_score": item.fit_score or 0,
            "search_explanation": "Matches saved filters.",
        }
        for item in opportunities[:limit]
    ]


def get_or_create_alert_preference(db: Session, tenant_id: str) -> AlertPreference:
    preference = db.query(AlertPreference).filter(AlertPreference.tenant_id == tenant_id).first()
    if preference:
        return preference
    preference = AlertPreference(tenant_id=tenant_id)
    db.add(preference)
    db.commit()
    db.refresh(preference)
    return preference


def build_alert_digest(db: Session, tenant_id: str, preference: AlertPreference) -> dict:
    today = date.today()
    due_cutoff = today + timedelta(days=preference.due_within_days)
    hidden_ids = {
        item.opportunity_id
        for item in db.query(OpportunityWorkflow.opportunity_id)
        .filter(OpportunityWorkflow.tenant_id == tenant_id, OpportunityWorkflow.hidden == True)  # noqa: E712
        .all()
    }

    high_fit_query = db.query(Opportunity).filter(
        Opportunity.source != "seed",
        Opportunity.bid_status == "open",
        Opportunity.minimum_value_match == True,  # noqa: E712
        Opportunity.fit_score >= preference.min_fit_score,
    )
    due_soon_query = db.query(Opportunity).filter(
        Opportunity.source != "seed",
        Opportunity.bid_status == "open",
        Opportunity.due_date.isnot(None),
        Opportunity.due_date <= due_cutoff,
    )
    if hidden_ids:
        high_fit_query = high_fit_query.filter(Opportunity.id.notin_(hidden_ids))
        due_soon_query = due_soon_query.filter(Opportunity.id.notin_(hidden_ids))

    watched_ids = {
        item.opportunity_id
        for item in db.query(OpportunityWorkflow.opportunity_id)
        .filter(
            OpportunityWorkflow.tenant_id == tenant_id,
            (OpportunityWorkflow.saved == True) | (OpportunityWorkflow.watched == True),  # noqa: E712
        )
        .all()
    }
    watched = []
    if watched_ids:
        watched = (
            db.query(Opportunity)
            .filter(Opportunity.id.in_(watched_ids), Opportunity.bid_status == "open")
            .order_by(Opportunity.due_date.asc().nullslast(), Opportunity.fit_score.desc().nullslast())
            .limit(15)
            .all()
        )

    source_failures = []
    if preference.include_source_failures:
        for job in db.query(IngestionJob).filter(IngestionJob.status == "failed").order_by(IngestionJob.updated_at.desc()).limit(12).all():
            params = job.params or {}
            source_failures.append(
                _json_safe(
                    {
                        "adapter": job.adapter,
                        "source": params.get("job_label") or params.get("source") or job.adapter,
                        "error": job.error,
                        "updated_at": job.updated_at,
                    }
                )
            )

    saved_search_blocks = []
    saved_search_match_count = 0
    for saved_search in (
        db.query(SavedSearch)
        .filter(SavedSearch.tenant_id == tenant_id, SavedSearch.enabled == True, SavedSearch.email_digest == True)  # noqa: E712
        .order_by(SavedSearch.updated_at.desc())
        .limit(20)
        .all()
    ):
        matches = saved_search_results(db, tenant_id, saved_search, limit=10)
        saved_search_match_count += len(matches)
        saved_search_blocks.append(
            _json_safe(
                {
                    "id": saved_search.id,
                    "name": saved_search.name,
                    "query": saved_search.query,
                    "filters": saved_search.filters or {},
                    "matches": matches,
                }
            )
        )

    high_fit = (
        high_fit_query.order_by(Opportunity.fit_score.desc().nullslast(), Opportunity.due_date.asc().nullslast()).limit(20).all()
    )
    due_soon = due_soon_query.order_by(Opportunity.due_date.asc(), Opportunity.fit_score.desc().nullslast()).limit(20).all()
    digest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tenant_id": tenant_id,
        "settings": {
            "min_fit_score": preference.min_fit_score,
            "due_within_days": preference.due_within_days,
            "include_source_failures": preference.include_source_failures,
            "enabled": preference.enabled,
            "email_to": preference.email_to,
        },
        "counts": {
            "high_fit": len(high_fit),
            "due_soon": len(due_soon),
            "watched": len(watched),
            "source_failures": len(source_failures),
            "saved_searches": len(saved_search_blocks),
            "saved_search_matches": saved_search_match_count,
        },
        "high_fit": [_opportunity_card(item) for item in high_fit],
        "due_soon": [_opportunity_card(item) for item in due_soon],
        "watched": [_opportunity_card(item) for item in watched],
        "saved_searches": saved_search_blocks,
        "source_failures": source_failures,
    }
    return digest
