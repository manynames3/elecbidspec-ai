from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

PROPOSAL_KEYS = {
    "bid_summary",
    "scope_checklist",
    "missing_information_checklist",
    "required_documents_checklist",
    "risk_flags",
    "draft_executive_summary",
    "partner_email_template",
}


def _json_safe(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _list_text(items: list[str] | None, fallback: str) -> str:
    if not items:
        return fallback
    return ", ".join(items)


def _company_name(company_profile: Mapping | None) -> str:
    return str((company_profile or {}).get("name") or "our team")


def _company_capability_sentence(company_profile: Mapping | None) -> str:
    profile = company_profile or {}
    supplied = _list_text(profile.get("cable_types_supplied") or [], "cable, conduit, and electrical materials")
    installed = _list_text(profile.get("installation_capabilities") or [], "field execution and installation support")
    states = _list_text(profile.get("states_served") or [], "the project region")
    bonding = profile.get("bonding_capacity")
    bonding_phrase = f" with bonding capacity up to ${float(bonding):,.0f}" if bonding else ""
    return f"{_company_name(profile)} supports {supplied}, {installed}, and service coverage in {states}{bonding_phrase}."


def generate_deterministic_proposal(opportunity: Mapping, company_profile: Mapping | None = None) -> dict:
    specs = opportunity.get("extracted_specs") or {}
    title = opportunity.get("title") or "the opportunity"
    agency = opportunity.get("agency") or "the issuing agency"
    project_type = (opportunity.get("project_type") or "general_electrical").replace("_", " ")
    due_date = opportunity.get("due_date") or "the posted due date"
    fit_score = opportunity.get("fit_score")
    company_name = _company_name(company_profile)
    capability_sentence = _company_capability_sentence(company_profile)

    materials = specs.get("required_materials") or ["Confirm cable, conduit, equipment, and accessory requirements."]
    scope_items = specs.get("installation_scope") or ["Confirm supply, installation, testing, commissioning, and closeout scope."]
    bonding = specs.get("bonding_insurance_requirements") or ["Verify bid bond, performance bond, payment bond, and insurance requirements."]
    submission = specs.get("submission_instructions") or ["Confirm portal, format, delivery address, and submission deadline."]

    risk_flags = []
    if not opportunity.get("estimated_value"):
        risk_flags.append("Estimated value is missing; validate bonding and pricing exposure before pursuing.")
    if fit_score is not None and fit_score < 60:
        risk_flags.append("Fit score is below target; consider teaming or no-bid review.")
    if opportunity.get("value_confidence") in {"unknown", "likely"}:
        risk_flags.append("Estimated value needs validation before committing bid resources.")
    if opportunity.get("bid_status") != "open":
        risk_flags.append("Opportunity is not marked open; confirm bidding status before outreach.")
    if not specs.get("deadlines"):
        risk_flags.append("Intermediate deadlines were not extracted; review the full solicitation manually.")
    if not bonding:
        risk_flags.append("Bonding and insurance requirements need manual confirmation.")

    bid_summary = (
        f"{agency} is seeking bids for {title}, classified as {project_type}. "
        f"The response is due by {due_date}. {capability_sentence} Key extracted keywords include "
        f"{', '.join(specs.get('keywords', []) or ['general electrical scope'])}."
    )

    return {
        "bid_summary": bid_summary,
        "scope_checklist": [f"Review and price material requirement: {item}." for item in materials[:8]]
        + [f"Validate field scope: {item}" for item in scope_items[:5]],
        "missing_information_checklist": [
            "Confirm final drawings, one-line diagrams, cable schedules, and addenda.",
            "Confirm site access, outage windows, phasing, and owner-furnished equipment.",
            "Confirm liquidated damages, warranty terms, wage rules, and permitting responsibilities.",
            f"Confirm which scope items {company_name} will self-perform versus subcontract or partner.",
        ],
        "required_documents_checklist": [
            "Completed bid form and pricing schedule.",
            "Bid bond and bonding letter.",
            "Certificate of insurance and safety record.",
            "Relevant project references and resumes.",
            "Manufacturer cut sheets or material compliance documentation.",
            f"{company_name} capability statement and project-specific material compliance narrative.",
        ],
        "risk_flags": risk_flags,
        "draft_executive_summary": (
            f"{company_name} understands that {agency} requires a responsive electrical infrastructure partner for {title}. "
            f"{capability_sentence} We will align compliant material sourcing, experienced execution resources, disciplined safety practices, "
            "and schedule-focused project management to deliver the work with minimal operational disruption."
        ),
        "partner_email_template": (
            "Subject: Partner review requested - "
            f"{title}\n\n"
            "Hi team,\n\n"
            f"{company_name} is reviewing {title} for {agency}. The opportunity appears to involve {project_type} work and is due {due_date}. "
            "Please review the attached scope, confirm whether your team can support pricing, labor, schedule, and any specialty equipment, "
            "and send exclusions or clarifications we should include in the proposal.\n\n"
            "Thanks,"
        ),
    }


def _proposal_prompt(opportunity: Mapping, company_profile: Mapping | None, baseline: Mapping) -> str:
    payload = {
        "company_profile": _json_safe(company_profile or {}),
        "opportunity": _json_safe(opportunity),
        "baseline_proposal": _json_safe(baseline),
        "output_schema": {key: "string" if key in {"bid_summary", "draft_executive_summary", "partner_email_template"} else "array of strings" for key in sorted(PROPOSAL_KEYS)},
    }
    return (
        "Create an optimized bid-readiness and proposal-prep package for the company profile and public bid opportunity below. "
        "Use the company profile as authoritative context. Do not invent certifications, factory locations, project references, "
        "bonding limits, installation crews, or legal commitments that are not in the profile or opportunity. If something is needed "
        "but not provided, place it in missing_information_checklist or risk_flags. Tailor the executive summary to the named company, "
        "especially cable supply, material compliance, schedule reliability, and any partner/self-perform boundary. Return only valid JSON "
        "with exactly these keys: bid_summary, scope_checklist, missing_information_checklist, required_documents_checklist, risk_flags, "
        "draft_executive_summary, partner_email_template.\n\n"
        f"{json.dumps(payload, indent=2)}"
    )


def _extract_json_object(text: str) -> dict:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fenced:
        cleaned = fenced.group(1)
    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            cleaned = cleaned[start : end + 1]
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict):
        raise ValueError("Bedrock response was not a JSON object")
    return parsed


def _normalize_proposal_payload(payload: Mapping, fallback: Mapping) -> dict:
    normalized = dict(fallback)
    for key in PROPOSAL_KEYS:
        value = payload.get(key)
        if key in {"bid_summary", "draft_executive_summary", "partner_email_template"}:
            if isinstance(value, str) and value.strip():
                normalized[key] = value.strip()
        elif isinstance(value, list):
            normalized[key] = [str(item).strip() for item in value if str(item).strip()]
    return normalized


def generate_bedrock_proposal(opportunity: Mapping, company_profile: Mapping | None, baseline: Mapping) -> dict:
    settings = get_settings()
    if not settings.bedrock_proposals_enabled:
        return dict(baseline)

    try:
        import boto3
    except ImportError as exc:
        raise RuntimeError("boto3 is required for Bedrock proposal generation") from exc

    client = boto3.client("bedrock-runtime", region_name=settings.bedrock_region)
    response = client.converse(
        modelId=settings.bedrock_model_id,
        system=[
            {
                "text": (
                    "You are an expert proposal strategist for electrical cable supply, power infrastructure, utilities, "
                    "data centers, substations, and installation teaming. You write concise, compliant, bid-ready content."
                )
            }
        ],
        messages=[{"role": "user", "content": [{"text": _proposal_prompt(opportunity, company_profile, baseline)}]}],
        inferenceConfig={"maxTokens": settings.bedrock_max_tokens, "temperature": settings.bedrock_temperature},
    )
    content = response.get("output", {}).get("message", {}).get("content", [])
    text = "\n".join(block.get("text", "") for block in content if isinstance(block, dict))
    if not text.strip():
        raise RuntimeError("Bedrock returned an empty proposal response")
    return _normalize_proposal_payload(_extract_json_object(text), baseline)


def generate_proposal_package(opportunity: Mapping, company_profile: Mapping | None = None) -> dict:
    baseline = generate_deterministic_proposal(opportunity, company_profile)
    settings = get_settings()
    if not settings.bedrock_proposals_enabled:
        return baseline
    try:
        return generate_bedrock_proposal(opportunity, company_profile, baseline)
    except Exception as exc:  # noqa: BLE001 - proposal endpoint should degrade gracefully
        logger.exception("Bedrock proposal generation failed")
        fallback = dict(baseline)
        fallback["risk_flags"] = [
            *fallback.get("risk_flags", []),
            f"Bedrock proposal generation was unavailable; deterministic fallback used. Reason: {exc}",
        ]
        return fallback
