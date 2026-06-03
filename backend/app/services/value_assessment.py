from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


DEFAULT_MINIMUM_VALUE = Decimal("5000000")

HIGH_VALUE_SCOPE_TERMS = {
    "data center": 4,
    "datacenter": 4,
    "hyperscale": 5,
    "colocation": 4,
    "ai infrastructure": 5,
    "artificial intelligence": 4,
    "hpc": 4,
    "high performance computing": 4,
    "gpu": 4,
    "compute campus": 5,
    "critical power": 4,
    "ups": 3,
    "uninterruptible power supply": 3,
    "power distribution unit": 3,
    "pdu": 2,
    "busduct": 2,
    "busway": 2,
    "utility interconnection": 3,
    "substation": 4,
    "transmission": 4,
    "high voltage": 3,
    "medium voltage": 2,
    "electrical": 2,
    "low voltage": 2,
    "transformer": 2,
    "switchgear": 2,
    "conduit": 2,
    "underground": 2,
    "duct bank": 2,
    "shore power": 3,
    "power hub": 3,
    "electric work": 3,
    "electrical installations": 3,
    "job order contract": 2,
    "requirements contract": 2,
    "water filtration plant": 2,
    "fire alarm": 2,
    "campus": 2,
    "airport": 2,
    "utility": 2,
    "distribution feeder": 2,
    "multi-site": 2,
    "performance bond": 1,
    "payment bond": 1,
    "bid bond": 1,
    "capital plan": 3,
    "capital program": 3,
    "integrated resource plan": 3,
    "rate case": 3,
    "puc docket": 3,
    "transmission expansion": 4,
    "interconnection queue": 4,
    "large load": 3,
    "ehv": 4,
    "xlpe": 4,
}

INVESTOR_OWNED_UTILITY_TERMS = {
    "investor-owned utility",
    "investor owned utility",
    "iou",
    "dominion energy",
    "duke energy",
    "american electric power",
    "aep",
    "xcel energy",
    "pg&e",
    "pacific gas and electric",
    "southern california edison",
    "sce",
    "san diego gas & electric",
    "sdg&e",
    "centerpoint energy",
    "oncor",
    "entergy",
    "firstenergy",
    "national grid",
    "eversource",
    "dte energy",
    "consumers energy",
    "arizona public service",
    "florida power & light",
    "fpl",
    "nextera",
    "ppl electric",
    "we energies",
    "ameren",
    "con edison",
    "consolidated edison",
    "pseg",
    "pse&g",
}

PUBLIC_AGENCY_SOURCE_TYPES = {
    "airport_authority",
    "education",
    "federal",
    "state_dot",
    "state_local",
    "transit",
    "university",
    "water_authority",
}

EARLY_SIGNAL_TERMS = {
    "capital improvement program",
    "capital plan",
    "capital program",
    "integrated resource plan",
    "irp",
    "rate case",
    "puc",
    "public utility commission",
    "docket",
    "transmission plan",
    "transmission expansion",
    "rto",
    "iso",
    "pjm",
    "ercot",
    "caiso",
    "miso",
    "spp",
    "interconnection queue",
    "large load",
    "zoning",
    "right-of-way",
    "right of way",
    "substation permit",
    "data center interconnection",
}

PRE_RFP_TERMS = {
    "pre-rfp",
    "pre rfp",
    "pre solicitation",
    "pre-solicitation",
    "sources sought",
    "request for information",
    "rfi",
    "request for qualifications",
    "rfq",
    "prequalification",
    "pre-qualified",
    "supplier registration",
    "approved vendor list",
    "avl",
}

SIGNAL_TYPE_TERMS = [
    ("puc_docket", ["puc", "public utility commission", "rate case", "docket", "commission filing"]),
    ("rto_transmission_plan", ["rto", "iso", "pjm", "ercot", "caiso", "miso", "spp", "transmission plan", "transmission expansion"]),
    ("data_center_interconnection", ["data center interconnection", "large load", "load interconnection", "hyperscale", "ai infrastructure", "gpu"]),
    ("zoning_or_permit", ["zoning", "right-of-way", "right of way", "permit", "substation permit", "council approval"]),
    ("capital_plan", ["capital plan", "capital program", "capital improvement program", "integrated resource plan", "irp"]),
    ("prequalification", ["prequalification", "pre-qualified", "supplier registration", "approved vendor list", "avl"]),
]

OPEN_STATUS_TERMS = {
    "open",
    "active",
    "solicitation",
    "pre_solicitation",
    "sources_sought",
    "request_for_bid",
    "request_for_proposal",
    "rfp",
    "ifb",
}
CLOSED_STATUS_TERMS = {"closed", "cancelled", "canceled", "awarded", "expired", "inactive", "no_longer_open"}


def decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def contains_scope_term(text: str, term: str) -> bool:
    if term == "hpc":
        return (
            "high performance computing" in text
            or re.search(
                r"\bhpc\b(?=.{0,80}\b(ai|compute|computing|gpu|server|data center|datacenter|hyperscale)\b)|"
                r"\b(ai|compute|computing|gpu|server|data center|datacenter|hyperscale)\b.{0,80}\bhpc\b",
                text,
            )
            is not None
        )
    if term == "ups":
        return (
            re.search(
                r"\bups\b(?=.{0,64}\b(power|battery|distribution|system|room|electrical|critical|backup|busduct|switchgear|feeder|feeders|data center|infrastructure)\b)|"
                r"\b(power|battery|distribution|system|room|electrical|critical|backup|busduct|switchgear|feeder|feeders|data center|infrastructure)\b.{0,64}\bups\b",
                text,
            )
            is not None
        )
    if re.fullmatch(r"[a-z0-9]+", term):
        return re.search(rf"\b{re.escape(term)}\b", text) is not None
    return term in text


def parse_money_value(raw_amount: str, raw_unit: str | None = None) -> Decimal | None:
    try:
        amount = Decimal(raw_amount.replace(",", ""))
    except InvalidOperation:
        return None
    unit = (raw_unit or "").lower()
    if unit in {"m", "mm", "mil", "million", "millions"}:
        amount *= Decimal("1000000")
    elif unit in {"k", "thousand"}:
        amount *= Decimal("1000")
    return amount


def infer_estimated_value(text: str) -> Decimal | None:
    values: list[Decimal] = []
    patterns = [
        r"\$\s?(\d[\d,]*(?:\.\d+)?)\s?(m|mm|mil|million|millions|k|thousand)?\b",
        r"\b(?:over|above|exceeds?|greater than|estimated at|estimate(?:d)? value(?: of)?|budget(?: of)?)\s+\$?\s?(\d[\d,]*(?:\.\d+)?)\s?(m|mm|mil|million|millions|k|thousand)?\b",
    ]
    for pattern in patterns:
        for amount, unit in re.findall(pattern, text, flags=re.IGNORECASE):
            parsed = parse_money_value(amount, unit)
            if parsed is not None:
                values.append(parsed)
    return max(values) if values else None


def normalize_bid_status(raw_status: str | None, due_date: date | None) -> str:
    if due_date and due_date < date.today():
        return "closed"
    normalized = (raw_status or "").strip().lower().replace(" ", "_").replace("-", "_")
    if normalized:
        if normalized in CLOSED_STATUS_TERMS:
            return "closed"
        if normalized in OPEN_STATUS_TERMS:
            return "open"
        return normalized
    return "open"


def infer_source_type(source: str | None, agency: str | None = None) -> str:
    source_text = (source or "").lower()
    agency_text = (agency or "").lower()
    if source_text == "sam_gov":
        return "federal"
    if any(term in f"{source_text} {agency_text}" for term in INVESTOR_OWNED_UTILITY_TERMS):
        return "investor_owned_utility"
    if any(term in agency_text for term in ["city of", "county", "state", "department of transportation", "public works"]):
        return "state_local"
    if any(term in agency_text for term in ["energy", "electric", "power", "utility", "cooperative"]):
        return "utility"
    if any(term in agency_text for term in ["university", "school", "college"]):
        return "education"
    if source_text in {"manual_upload", "manual"}:
        return "manual"
    return source_text or "other"


def _opportunity_text(data: dict) -> str:
    return " ".join(
        [
            str(data.get("title") or ""),
            str(data.get("agency") or ""),
            str(data.get("description") or ""),
            str(data.get("source") or ""),
            str(data.get("source_type") or ""),
            str(data.get("project_type") or ""),
        ]
    ).lower()


def infer_owner_type(data: dict) -> str:
    explicit = str(data.get("owner_type") or "").strip().lower()

    source_type = str(data.get("source_type") or "").strip().lower()
    text = _opportunity_text(data)
    if source_type == "investor_owned_utility" or any(term in text for term in INVESTOR_OWNED_UTILITY_TERMS):
        return "investor_owned_utility"
    if any(term in text for term in ["private developer", "hyperscale developer", "data center developer", "private campus"]):
        return "private_developer"
    if explicit and explicit not in {"manual", "unknown", "public_agency"}:
        return explicit
    if source_type in PUBLIC_AGENCY_SOURCE_TYPES:
        return "public_agency"
    if source_type == "utility":
        return "public_power_or_utility"
    return "public_agency"


def infer_project_stage(data: dict) -> str:
    explicit = str(data.get("project_stage") or "").strip().lower().replace("-", "_").replace(" ", "_")
    if explicit in {"early_signal", "pre_rfp", "awarded"}:
        return explicit

    text = _opportunity_text(data)
    status = str(data.get("bid_status") or "").lower()
    if "award" in status or "awarded" in text:
        return "awarded"
    if any(term in text for term in PRE_RFP_TERMS):
        return "pre_rfp"
    if any(term in text for term in EARLY_SIGNAL_TERMS):
        return "early_signal"
    return "active_bid"


def infer_signal_type(data: dict) -> str | None:
    explicit = str(data.get("signal_type") or "").strip().lower().replace("-", "_").replace(" ", "_")
    if explicit:
        return explicit
    text = _opportunity_text(data)
    for signal_type, terms in SIGNAL_TYPE_TERMS:
        if any(term in text for term in terms):
            return signal_type
    return None


def high_value_scope_score(data: dict) -> int:
    specs = data.get("extracted_specs") or {}
    text = " ".join(
        [
            str(data.get("title") or ""),
            str(data.get("agency") or ""),
            str(data.get("description") or ""),
            str(data.get("project_type") or ""),
            " ".join(specs.get("keywords", [])),
            " ".join(specs.get("required_materials", [])),
            " ".join(specs.get("installation_scope", [])),
            " ".join(specs.get("bonding_insurance_requirements", [])),
        ]
    ).lower()
    score = sum(weight for term, weight in HIGH_VALUE_SCOPE_TERMS.items() if contains_scope_term(text, term))
    if re.search(r"\b\d{2,4}\s?kv\b", text, flags=re.IGNORECASE):
        score += 3
    return score


def assess_value(data: dict, minimum_value: Decimal = DEFAULT_MINIMUM_VALUE) -> dict:
    estimated_value = decimal_or_none(data.get("estimated_value"))
    text = f"{data.get('title') or ''} {data.get('description') or ''}"
    inferred_value = infer_estimated_value(text)
    if estimated_value is None and inferred_value is not None:
        estimated_value = inferred_value

    if estimated_value is not None and estimated_value >= minimum_value:
        return {
            "estimated_value": estimated_value,
            "value_confidence": "confirmed",
            "minimum_value_match": True,
            "value_explanation": f"Posted or extracted value is at least ${minimum_value:,.0f}.",
        }

    if estimated_value is not None:
        return {
            "estimated_value": estimated_value,
            "value_confidence": "below_threshold",
            "minimum_value_match": False,
            "value_explanation": f"Posted or extracted value is below ${minimum_value:,.0f}.",
        }

    score = high_value_scope_score(data)
    if score >= 5:
        return {
            "estimated_value": None,
            "value_confidence": "likely",
            "minimum_value_match": True,
            "value_explanation": "No value was posted, but scope indicators suggest this may meet the high-value threshold.",
        }

    return {
        "estimated_value": None,
        "value_confidence": "unknown",
        "minimum_value_match": False,
        "value_explanation": "No reliable value was posted or inferred from the available notice text.",
    }
