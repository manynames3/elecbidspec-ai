from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from app.services.taihan_intelligence import add_taihan_intelligence


def _as_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(_as_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_as_text(item) for item in value)
    return str(value or "")


def _clean(value: Any, limit: int | None = None) -> str:
    text = " ".join(str(value or "").split())
    if limit and len(text) > limit:
        return f"{text[: limit - 3].rstrip()}..."
    return text


def _date_value(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            try:
                return datetime.strptime(value[:10], "%Y-%m-%d").date()
            except ValueError:
                return None
    return None


def _datetime_value(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _money(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _source_evidence(data: Mapping[str, Any]) -> list[dict[str, str]]:
    specs = data.get("extracted_specs") or {}
    candidates = []
    for item in specs.get("evidence_links") or []:
        if isinstance(item, Mapping):
            candidates.append(item)
    for item in data.get("attachments") or []:
        if isinstance(item, Mapping) and str(item.get("type") or "").lower() == "evidence":
            candidates.append(item)

    if not candidates and data.get("source_url"):
        candidates.append(
            {
                "name": data.get("source") or "Source posting",
                "url": data.get("source_url"),
                "source": data.get("source") or "source",
                "excerpt": data.get("description"),
            }
        )

    evidence: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in candidates:
        url = _clean(item.get("url") or item.get("source_url"))
        name = _clean(item.get("name") or item.get("filename") or item.get("source") or url or "Source evidence", 160)
        key = (name, url)
        if key in seen:
            continue
        seen.add(key)
        excerpt = _clean(item.get("excerpt") or item.get("description") or "", 420)
        evidence.append(
            {
                "name": name,
                "url": url,
                "source": _clean(item.get("source") or data.get("source") or "source", 80),
                "type": _clean(item.get("type") or "evidence", 40),
                "excerpt": excerpt,
                "quality": "excerpted" if excerpt else "link_only",
            }
        )
    return evidence[:8]


def evidence_grade(data: Mapping[str, Any]) -> str:
    specs = data.get("extracted_specs") or {}
    intel = specs.get("taihan_intelligence") or {}
    evidence = intel.get("evidence_strength") or {}
    evidence_count = sum(1 for present in evidence.values() if present)
    source_evidence = _source_evidence(data)
    excerpt_count = len([item for item in source_evidence if item.get("excerpt")])
    if evidence_count >= 3 and excerpt_count >= 1:
        return "strong"
    if evidence_count >= 2 or source_evidence:
        return "moderate"
    return "thin"


def signal_change(data: Mapping[str, Any]) -> dict[str, str]:
    specs = data.get("extracted_specs") or {}
    intel = specs.get("taihan_intelligence") or {}
    created_at = _datetime_value(data.get("created_at"))
    updated_at = _datetime_value(data.get("updated_at"))
    today = datetime.now(timezone.utc)
    project_stage = str(data.get("project_stage") or "")
    tier = str(intel.get("tier") or "")

    if project_stage == "active_bid":
        status = "active_bid_handoff"
        explanation = "Formal procurement appears open; move from shaping to bid-readiness."
    elif created_at and (today - created_at).days <= 7:
        status = "new"
        explanation = "Newly observed signal in the current review window."
    elif updated_at and created_at and updated_at.date() != created_at.date() and (today - updated_at).days <= 14:
        status = "updated"
        explanation = "Recently updated source record; review evidence for scope or timing changes."
    elif tier == "high":
        status = "escalated"
        explanation = "High Taihan relevance based on owner, voltage, load, cable scope, or source evidence."
    else:
        forecast = _date_value(data.get("forecast_rfp_date"))
        if forecast and forecast < today.date() and not data.get("due_date"):
            status = "stale"
            explanation = "Forecast RFP timing has passed without a posted deadline; verify whether procurement moved elsewhere."
        else:
            status = "monitor"
            explanation = "Keep on watchlist until owner, procurement path, or source documents strengthen."

    return {
        "status": status,
        "explanation": explanation,
        "last_changed_at": updated_at.isoformat() if updated_at else "",
    }


def why_now(data: Mapping[str, Any]) -> str:
    specs = data.get("extracted_specs") or {}
    intel = specs.get("taihan_intelligence") or {}
    evidence = intel.get("evidence_strength") or {}
    owner = data.get("agency") or "The source"
    stage = str(data.get("project_stage") or "")
    evidence_labels = []
    if evidence.get("named_utility"):
        evidence_labels.append("a named utility/transmission owner")
    if evidence.get("explicit_voltage"):
        evidence_labels.append("explicit HV/EHV voltage")
    if evidence.get("data_center_or_load"):
        evidence_labels.append("data-center or large-load demand")
    if evidence.get("cable_specific_scope"):
        evidence_labels.append("cable-specific scope")
    evidence_text = ", ".join(evidence_labels) if evidence_labels else "early public planning evidence"

    if stage in {"early_signal", "pre_rfp"}:
        return (
            f"{owner} is visible before a formal RFP, and the signal includes {evidence_text}. "
            "This is the window to shape specifications, confirm AVL/vendor path, and reach EPC or utility stakeholders before cable requirements are locked."
        )
    if stage == "active_bid":
        return "The opportunity is already in procurement. Shift from market shaping to compliance review, proposal gating, and partner pricing."
    return "Use this as market intelligence until a clear owner action, procurement date, or source update creates a pursuit window."


def relationship_targets(data: Mapping[str, Any]) -> list[dict[str, str]]:
    specs = data.get("extracted_specs") or {}
    intel = specs.get("taihan_intelligence") or {}
    owner = _clean(data.get("agency") or "Project owner", 120)
    source_type = str(data.get("source_type") or "")
    procurement_path = str(intel.get("procurement_path") or "")
    state = _clean(data.get("state") or data.get("location") or "project region", 80)
    targets = []

    if owner and owner != "Project owner":
        targets.append(
            {
                "role": "Owner / utility",
                "name": owner,
                "rationale": "Named source owner should confirm procurement path, AVL requirements, and engineering owner.",
                "action": "Identify planning, procurement, and transmission engineering contacts from public channels.",
            }
        )
    if source_type == "regulatory":
        targets.append(
            {
                "role": "Regulatory docket",
                "name": f"{state} public utility proceeding",
                "rationale": "Docket activity can reveal cost recovery, CCN timing, transmission scope, and intervenor filings.",
                "action": "Review docket filings for owner testimony, project maps, schedule, and EPC/procurement clues.",
            }
        )
    if source_type == "rto_iso":
        targets.append(
            {
                "role": "RTO/ISO queue stakeholder",
                "name": f"{owner} / interconnection customer",
                "rationale": "Queue records indicate future interconnection and network upgrade needs before sourcing opens.",
                "action": "Map transmission owner, POI, interconnection customer, and expected EPC/design handoff.",
            }
        )
    if procurement_path != "public_bid":
        targets.append(
            {
                "role": "EPC / engineer-of-record",
                "name": "Partner shortlist",
                "rationale": "Taihan may need to influence package specifications through EPC or design teams before public bid release.",
                "action": "Build a partner target list and send capability language tied to HV/MV cable scope.",
            }
        )
    return targets[:5]


def partner_targets(data: Mapping[str, Any], company_profile: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    specs = data.get("extracted_specs") or {}
    intel = specs.get("taihan_intelligence") or {}
    text = _as_text(data).lower()
    partners = [
        {
            "role": "EPC / electrical contractor",
            "need": "Prime or package partner for U.S. execution, installation pricing, and owner relationships.",
            "trigger": "Use when procurement path is EPC-led or owner requires local field execution.",
        },
        {
            "role": "Utility-approved installer",
            "need": "Local installation, termination, testing, outage coordination, and union/labor coverage.",
            "trigger": "Use when scope includes substation, underground, transmission, or utility interconnection.",
        },
    ]
    if "data center" in text or "hyperscale" in text or "large load" in text or intel.get("evidence_strength", {}).get("data_center_or_load"):
        partners.append(
            {
                "role": "Data-center power integrator",
                "need": "Critical power package access, switchgear/UPS coordination, and developer/EPC relationship path.",
                "trigger": "Use for AI, hyperscale, large-load, or campus power signals.",
            }
        )
    if company_profile and company_profile.get("labor_type") == "partner-led":
        partners.append(
            {
                "role": "Partner-led field execution",
                "need": "Taihan capability profile indicates partner-led labor; verify installer coverage before pursuit commitment.",
                "trigger": "Use before bid/no-bid and outreach.",
            }
        )
    return partners[:5]


def next_actions(data: Mapping[str, Any]) -> list[str]:
    specs = data.get("extracted_specs") or {}
    intel = specs.get("taihan_intelligence") or {}
    actions = list(intel.get("next_steps") or [])
    actions.extend(
        [
            "Save the record, assign an analyst owner, and mark it verified only after source evidence is reviewed.",
            "Generate a one-page opportunity brief before outreach so BD, proposal, and partner teams share the same facts.",
        ]
    )
    if evidence_grade(data) == "thin":
        actions.insert(0, "Strengthen evidence: open the source link and ingest/download available filings, maps, or attachments.")
    return list(dict.fromkeys(actions))[:6]


def analyst_review(data: Mapping[str, Any]) -> dict[str, str]:
    grade = evidence_grade(data)
    change = signal_change(data)
    if grade == "strong" and change["status"] in {"new", "updated", "escalated"}:
        recommended_status = "verified_signal"
        guidance = "Source evidence is strong enough for analyst verification and BD assignment."
    elif grade == "thin":
        recommended_status = "needs_evidence"
        guidance = "Do not present as verified until a source excerpt, filing, or attachment is reviewed."
    else:
        recommended_status = "monitor"
        guidance = "Keep on watchlist and verify owner/procurement path before escalation."
    return {
        "recommended_status": recommended_status,
        "confidence": grade,
        "guidance": guidance,
    }


def add_pursuit_intelligence(data: dict[str, Any], company_profile: Mapping[str, Any] | None = None) -> dict[str, Any]:
    enriched = add_taihan_intelligence(deepcopy(data))
    specs = deepcopy(enriched.get("extracted_specs") or {})
    enriched["extracted_specs"] = specs

    source_evidence = _source_evidence(enriched)
    if source_evidence and not specs.get("evidence_links"):
        specs["evidence_links"] = source_evidence
    if source_evidence and not specs.get("evidence_excerpts"):
        specs["evidence_excerpts"] = [item["excerpt"] for item in source_evidence if item.get("excerpt")][:3]

    grade = evidence_grade(enriched)
    specs["pursuit_intelligence"] = {
        "evidence_grade": grade,
        "source_evidence": source_evidence,
        "why_now": why_now(enriched),
        "next_actions": next_actions(enriched),
        "relationship_targets": relationship_targets(enriched),
        "partner_targets": partner_targets(enriched, company_profile),
        "signal_change": signal_change(enriched),
        "analyst_review": analyst_review(enriched),
        "estimated_value": _money(enriched.get("estimated_value")),
    }
    return enriched
