from __future__ import annotations

import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Any


HV_TERMS = [
    "extra high voltage",
    "ehv",
    "high voltage",
    "hvdc",
    "765 kv",
    "500 kv",
    "345 kv",
    "230 kv",
    "138 kv",
    "115 kv",
]
DATA_CENTER_TERMS = ["data center", "datacenter", "hyperscale", "ai infrastructure", "large load", "gpu", "compute campus"]
SUBSTATION_TERMS = ["substation", "switchyard", "transformer", "breaker", "switchgear"]
LOAD_TERMS = ["large load", "load growth", "load interconnection", "data center interconnection", "new load", "load-serving"]
UNDERGROUND_TERMS = ["underground", "duct bank", "conduit", "trenching"]
CABLE_SCOPE_TERMS = [
    "cable",
    "xlpe",
    "conductor",
    "duct bank",
    "feeder",
    "feeders",
    "cable laying",
    "cable-laying",
    "cable terminal",
    "cable accessories",
    "underground cable",
    "submarine cable",
    "busduct",
    "busway",
]
UTILITY_POSITIONING_TERMS = ["investor-owned utility", "iou", "utility", "puc", "public utility commission", "ccn", "certificate of convenience", "rate case"]
NAMED_UTILITY_TERMS = [
    "aep",
    "atsi",
    "american electric power",
    "appalachian power",
    "bge",
    "central hudson",
    "centerpoint",
    "comed",
    "commonwealth edison",
    "coned",
    "consolidated edison",
    "deok",
    "dominion",
    "dominion energy",
    "duke energy",
    "eversource",
    "firstenergy",
    "georgia power",
    "jcpl",
    "jcp&l",
    "met-ed",
    "national grid",
    "northern states power",
    "nyseg",
    "nypa",
    "oncor",
    "pepco",
    "potomac electric power",
    "ppl",
    "ppl electric",
    "pseg",
    "sce",
    "southern california edison",
    "texas new mexico power",
    "tnmp",
    "xcel",
]
GENERIC_UTILITY_NAMES = {
    "",
    "pjm transmission owner",
    "public utility commission of texas",
    "public utility commission",
    "virginia state corporation commission",
    "georgia public service commission",
}


def _as_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(_as_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_as_text(item) for item in value)
    return str(value or "")


def _opportunity_text(data: Mapping[str, Any]) -> str:
    specs = data.get("extracted_specs") or {}
    return " ".join(
        [
            str(data.get("title") or ""),
            str(data.get("agency") or ""),
            str(data.get("description") or ""),
            str(data.get("source") or ""),
            str(data.get("source_type") or ""),
            str(data.get("project_type") or ""),
            str(data.get("project_stage") or ""),
            str(data.get("signal_type") or ""),
            str(data.get("owner_type") or ""),
            _as_text(specs.get("keywords")),
            _as_text(specs.get("required_materials")),
            _as_text(specs.get("installation_scope")),
            _as_text(specs.get("evidence_excerpts")),
        ]
    ).lower()


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def _has_voltage(text: str) -> bool:
    return re.search(r"\b(?:1[1-9][05]|2[0-9]{2}|3[0-9]{2}|500|765)\s?kv\b", text) is not None


def _has_named_utility(data: Mapping[str, Any], text: str) -> bool:
    agency = str(data.get("agency") or "").strip().lower()
    if agency and agency not in GENERIC_UTILITY_NAMES and _contains_any(agency, NAMED_UTILITY_TERMS):
        return True
    return _contains_any(text, NAMED_UTILITY_TERMS)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped = []
    for item in items:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped


def assess_taihan_intelligence(data: Mapping[str, Any]) -> dict[str, Any]:
    text = _opportunity_text(data)
    source_type = str(data.get("source_type") or "")
    project_stage = str(data.get("project_stage") or "")
    owner_type = str(data.get("owner_type") or "")
    signal_type = str(data.get("signal_type") or "")
    fit_score = int(data.get("fit_score") or 0)

    has_named_utility = _has_named_utility(data, text)
    has_explicit_voltage = _contains_any(text, HV_TERMS) or _has_voltage(text)
    is_data_center = _contains_any(text, DATA_CENTER_TERMS)
    has_load_evidence = is_data_center or _contains_any(text, LOAD_TERMS)
    has_cable_scope = _contains_any(text, CABLE_SCOPE_TERMS)
    is_substation = _contains_any(text, SUBSTATION_TERMS)
    is_underground = _contains_any(text, UNDERGROUND_TERMS)
    is_utility = owner_type == "investor_owned_utility" or source_type in {"utility", "regulatory", "rto_iso"} or _contains_any(text, UTILITY_POSITIONING_TERMS)

    score = 0
    reasons: list[str] = []
    angles: list[str] = []
    risk_flags: list[str] = []

    if project_stage in {"early_signal", "pre_rfp"}:
        score += 8
        reasons.append("Early-stage signal gives BD time before formal procurement.")
        risk_flags.append("No posted bid deadline; this is upstream intelligence, not a formal solicitation.")
    elif project_stage == "active_bid":
        score += 6
        reasons.append("Active bid can move directly into proposal review.")

    if source_type in {"rto_iso", "regulatory", "land_use"}:
        score += 8
        reasons.append("Official upstream source points to future grid or data-center power demand.")

    if has_load_evidence:
        score += 20
        reasons.append("Data center, AI infrastructure, or large-load evidence detected.")
        angles.append("Data center power infrastructure")

    if has_named_utility:
        score += 18
        reasons.append("Named utility or transmission owner detected.")
        angles.append("Utility AVL and transmission-owner positioning")

    if has_explicit_voltage:
        score += 16
        reasons.append("Explicit HV/EHV voltage evidence detected.")
        angles.append("HV/EHV cable package")

    if has_cable_scope:
        score += 16
        reasons.append("Cable, conductor, feeder, busduct, or duct-bank scope detected.")
        angles.append("Cable supply package")

    if is_substation:
        score += 6
        reasons.append("Substation, switchyard, transformer, or switchgear scope detected.")
        angles.append("Substation and switchyard cable/accessories")

    if is_underground:
        score += 4
        reasons.append("Underground, conduit, duct bank, or cable-laying scope detected.")
        angles.append("Underground cable and duct-bank scope")

    if is_utility:
        score += 4
        reasons.append("Utility, IOU, PUC, or transmission-owner context detected.")

    if data.get("minimum_value_match"):
        score += 4
        reasons.append("Record meets or likely exceeds the $5M pursuit threshold.")
    if str(data.get("value_confidence") or "") == "likely" and not data.get("estimated_value"):
        risk_flags.append("No dollar value was posted; value is inferred from scope indicators.")

    if fit_score >= 85:
        score += 4
        reasons.append("Strong fit against the current Taihan capability profile.")
    elif fit_score >= 70:
        score += 2
        reasons.append("Worth review against the current Taihan capability profile.")

    if signal_type in {"puc_docket", "rto_transmission_plan", "data_center_interconnection"}:
        risk_flags.append("Procurement may run through an EPC, utility AVL, or developer relationship rather than a public bid portal.")

    if owner_type == "investor_owned_utility" or source_type == "utility":
        procurement_path = "utility_rfp_or_avl"
    elif source_type == "regulatory":
        procurement_path = "utility_rfp_or_epc_partner"
    elif source_type == "rto_iso":
        procurement_path = "epc_partner_or_utility_planning"
    elif source_type == "land_use" or owner_type == "private_developer":
        procurement_path = "developer_or_epc_partner"
    elif project_stage == "active_bid":
        procurement_path = "public_bid"
    else:
        procurement_path = "monitor_for_procurement_path"

    if procurement_path in {"epc_partner_or_utility_planning", "developer_or_epc_partner", "utility_rfp_or_epc_partner"}:
        angles.append("Partner-led EPC pursuit")

    evidence_signals = {
        "named_utility": has_named_utility,
        "explicit_voltage": has_explicit_voltage,
        "data_center_or_load": has_load_evidence,
        "cable_specific_scope": has_cable_scope,
    }
    evidence_signal_count = sum(1 for present in evidence_signals.values() if present)

    bounded_score = max(0, min(100, score))
    if bounded_score >= 82 and evidence_signal_count >= 3:
        tier = "high"
        recommended_action = "Prioritize BD review: identify owner/transmission utility, confirm AVL or vendor-registration path, and map EPC/design partners before RFP."
    elif bounded_score >= 55 or (bounded_score >= 45 and evidence_signal_count >= 2):
        tier = "medium"
        recommended_action = "Assign BD watch: validate cable scope, owner, procurement path, and expected timing from source evidence."
    else:
        tier = "low"
        recommended_action = "Monitor only unless source documents reveal more concrete owner, voltage, data-center/load, or cable-scope evidence."

    if has_cable_scope and (has_explicit_voltage or is_data_center or is_substation):
        cable_relevance = "high"
    elif has_explicit_voltage or has_load_evidence or is_substation or is_underground or is_utility:
        cable_relevance = "medium"
    else:
        cable_relevance = "low"

    return {
        "score": bounded_score,
        "tier": tier,
        "cable_relevance": cable_relevance,
        "procurement_path": procurement_path,
        "taihan_angle": _dedupe(angles)[:5],
        "recommended_action": recommended_action,
        "evidence_strength": evidence_signals,
        "reasons": _dedupe(reasons)[:6],
        "risk_flags": _dedupe(risk_flags)[:4],
    }


def add_taihan_intelligence(data: dict[str, Any]) -> dict[str, Any]:
    specs = deepcopy(data.get("extracted_specs") or {})
    enriched = {**data, "extracted_specs": specs}
    specs["taihan_intelligence"] = assess_taihan_intelligence(enriched)
    enriched["extracted_specs"] = specs
    return enriched
