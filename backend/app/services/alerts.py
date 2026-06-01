from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models import AlertPreference, IngestionJob, Opportunity, OpportunityWorkflow


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
        },
        "high_fit": [_opportunity_card(item) for item in high_fit],
        "due_soon": [_opportunity_card(item) for item in due_soon],
        "watched": [_opportunity_card(item) for item in watched],
        "source_failures": source_failures,
    }
    return digest
