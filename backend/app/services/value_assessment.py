from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any


DEFAULT_MINIMUM_VALUE = Decimal("5000000")

HIGH_VALUE_SCOPE_TERMS = {
    "data center": 4,
    "substation": 4,
    "transmission": 4,
    "high voltage": 3,
    "medium voltage": 2,
    "transformer": 2,
    "switchgear": 2,
    "duct bank": 2,
    "campus": 2,
    "airport": 2,
    "utility": 2,
    "distribution feeder": 2,
    "multi-site": 2,
    "performance bond": 1,
    "payment bond": 1,
    "bid bond": 1,
}

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
    normalized = (raw_status or "").strip().lower().replace(" ", "_").replace("-", "_")
    if normalized:
        if normalized in CLOSED_STATUS_TERMS:
            return "closed"
        if normalized in OPEN_STATUS_TERMS:
            return "open"
        return normalized
    if due_date and due_date < date.today():
        return "closed"
    return "open"


def infer_source_type(source: str | None, agency: str | None = None) -> str:
    source_text = (source or "").lower()
    agency_text = (agency or "").lower()
    if source_text == "sam_gov":
        return "federal"
    if any(term in agency_text for term in ["city of", "county", "state", "department of transportation", "public works"]):
        return "state_local"
    if any(term in agency_text for term in ["energy", "electric", "power", "utility", "cooperative"]):
        return "utility"
    if any(term in agency_text for term in ["university", "school", "college"]):
        return "education"
    if source_text in {"manual_upload", "manual"}:
        return "manual"
    return source_text or "other"


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
    return sum(weight for term, weight in HIGH_VALUE_SCOPE_TERMS.items() if term in text)


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
    if score >= 6:
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
