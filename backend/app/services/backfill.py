from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.models import CompanyProfile, Opportunity
from app.services.classification import classify_bid
from app.services.extraction import extract_specs
from app.services.fit_scoring import score_fit
from app.services.pursuit_intelligence import add_pursuit_intelligence
from app.services.value_assessment import assess_value, infer_owner_type, infer_project_stage, infer_signal_type, infer_source_type, normalize_bid_status


def _profile_data(db: Session, tenant_id: str | None = None) -> dict | None:
    profile = None
    if tenant_id:
        profile = db.query(CompanyProfile).filter(CompanyProfile.tenant_id == tenant_id).first()
    profile = profile or db.query(CompanyProfile).filter(CompanyProfile.tenant_id == "default").first() or db.query(CompanyProfile).first()
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


def _money(value: Decimal | float | int | None) -> float | None:
    if value is None:
        return None
    return float(value)


def opportunity_to_backfill_data(opportunity: Opportunity) -> dict[str, Any]:
    return {
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
        "estimated_value": _money(opportunity.estimated_value),
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


def rescore_opportunity_payload(data: dict[str, Any], profile: dict | None = None) -> dict[str, Any]:
    specs = data.get("extracted_specs") or extract_specs(data.get("description") or "")
    data["extracted_specs"] = specs
    classification = classify_bid(data.get("title") or "", data.get("description") or "", specs)
    data["project_type"] = classification["project_type"]
    data["confidence_score"] = classification["confidence_score"]
    data["classification_explanation"] = classification["explanation"]
    inferred_source_type = infer_source_type(data.get("source"), data.get("agency"))
    if not data.get("source_type") or (data.get("source_type") == "manual" and inferred_source_type != "manual"):
        data["source_type"] = inferred_source_type
    data["bid_status"] = normalize_bid_status(data.get("bid_status"), data.get("due_date"))
    data["owner_type"] = infer_owner_type(data)
    data["project_stage"] = infer_project_stage(data)
    data["signal_type"] = infer_signal_type(data)
    data.update(assess_value(data))
    if profile:
        data.update(score_fit(data, profile))
    return add_pursuit_intelligence(data, profile)


def apply_backfilled_data(opportunity: Opportunity, data: dict[str, Any]) -> None:
    for key in [
        "source_type",
        "bid_status",
        "project_stage",
        "signal_type",
        "owner_type",
        "estimated_value",
        "value_confidence",
        "value_explanation",
        "minimum_value_match",
        "extracted_specs",
        "project_type",
        "confidence_score",
        "classification_explanation",
        "fit_score",
        "fit_explanation",
    ]:
        if key in data:
            setattr(opportunity, key, data[key])


def backfill_existing_opportunities(
    db: Session,
    *,
    tenant_id: str | None = None,
    source: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    query = db.query(Opportunity).order_by(Opportunity.updated_at.desc(), Opportunity.id.desc())
    if tenant_id:
        query = query.filter(Opportunity.tenant_id == tenant_id)
    if source:
        query = query.filter(Opportunity.source == source)
    if limit:
        query = query.limit(limit)

    updated = 0
    failed: list[dict[str, Any]] = []
    profiles: dict[str, dict | None] = {}
    started_at = datetime.utcnow().isoformat()
    for opportunity in query.all():
        try:
            if opportunity.tenant_id not in profiles:
                profiles[opportunity.tenant_id] = _profile_data(db, opportunity.tenant_id)
            data = rescore_opportunity_payload(opportunity_to_backfill_data(opportunity), profiles[opportunity.tenant_id])
            apply_backfilled_data(opportunity, data)
            updated += 1
            if updated % 100 == 0:
                db.commit()
        except Exception as exc:  # noqa: BLE001 - bulk backfill should continue and report per-record errors
            failed.append({"id": opportunity.id, "title": opportunity.title, "error": str(exc)})
    db.commit()
    return {
        "status": "complete",
        "started_at": started_at,
        "updated": updated,
        "failed": len(failed),
        "failures": failed[:25],
    }
