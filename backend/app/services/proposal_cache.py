from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Opportunity, ProposalArtifact
from app.services.proposal import generate_bedrock_proposal, generate_deterministic_proposal

logger = logging.getLogger(__name__)


def _proposal_payload(opportunity: Opportunity, opportunity_to_dict) -> dict:
    return opportunity_to_dict(opportunity)


def _upsert_artifact(
    db: Session,
    opportunity_id: int,
    tenant_id: str,
    content: Mapping,
    source: str,
    status: str = "ready",
    error: str | None = None,
) -> ProposalArtifact:
    artifact = (
        db.query(ProposalArtifact)
        .filter(ProposalArtifact.opportunity_id == opportunity_id, ProposalArtifact.tenant_id == tenant_id)
        .first()
    )
    if artifact:
        artifact.content = dict(content)
        artifact.source = source
        artifact.status = status
        artifact.error = error
        artifact.updated_at = datetime.now(timezone.utc)
    else:
        artifact = ProposalArtifact(
            opportunity_id=opportunity_id,
            tenant_id=tenant_id,
            content=dict(content),
            source=source,
            status=status,
            error=error,
        )
        db.add(artifact)
    db.commit()
    db.refresh(artifact)
    return artifact


def get_or_create_fast_proposal(
    db: Session,
    opportunity: Opportunity,
    profile: Mapping | None,
    tenant_id: str,
    opportunity_to_dict,
) -> dict:
    artifact = (
        db.query(ProposalArtifact)
        .filter(ProposalArtifact.opportunity_id == opportunity.id, ProposalArtifact.tenant_id == tenant_id, ProposalArtifact.status == "ready")
        .first()
    )
    if artifact and artifact.content:
        return dict(artifact.content)

    proposal = generate_deterministic_proposal(_proposal_payload(opportunity, opportunity_to_dict), profile)
    _upsert_artifact(db, opportunity.id, tenant_id, proposal, source="deterministic")
    return proposal


def enhance_proposal(
    db: Session,
    opportunity: Opportunity,
    profile: Mapping | None,
    tenant_id: str,
    opportunity_to_dict,
) -> dict:
    opportunity_data = _proposal_payload(opportunity, opportunity_to_dict)
    baseline = generate_deterministic_proposal(opportunity_data, profile)
    settings = get_settings()
    if not settings.bedrock_proposals_enabled:
        _upsert_artifact(db, opportunity.id, tenant_id, baseline, source="deterministic")
        return baseline
    try:
        proposal = generate_bedrock_proposal(opportunity_data, profile, baseline)
        _upsert_artifact(db, opportunity.id, tenant_id, proposal, source="bedrock")
        return proposal
    except Exception as exc:  # noqa: BLE001 - the user should keep a usable draft if Bedrock is unavailable
        logger.exception("Bedrock proposal enhancement failed")
        fallback = dict(baseline)
        fallback["risk_flags"] = [
            *fallback.get("risk_flags", []),
            f"AI enhancement was unavailable; deterministic fallback used. Reason: {exc}",
        ]
        _upsert_artifact(db, opportunity.id, tenant_id, fallback, source="deterministic", status="ready", error=str(exc))
        return fallback
