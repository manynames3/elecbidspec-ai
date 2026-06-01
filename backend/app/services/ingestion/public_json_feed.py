from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import httpx

from app.services.classification import classify_bid
from app.services.extraction import extract_specs
from app.services.ingestion.base import IngestionAdapter
from app.services.value_assessment import infer_source_type, normalize_bid_status


def _get_path(data: dict[str, Any], path: str | None) -> Any:
    if not path:
        return data
    current: Any = data
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _field(record: dict[str, Any], mapping: dict[str, str], field_name: str, default_key: str | None = None) -> Any:
    path = mapping.get(field_name) or default_key or field_name
    return _get_path(record, path)


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", "").replace("$", ""))
    except Exception:
        return None


class PublicJsonFeedAdapter(IngestionAdapter):
    name = "public_json_feed"
    description = "Configurable JSON feed adapter for state, local, utility, school, and authority bid portals."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        url = params.get("url")
        if not url:
            raise ValueError("public_json_feed requires params.url")

        mapping = params.get("mapping") or {}
        records_path = params.get("records_path")
        source = params.get("source") or "public_json_feed"
        source_type = params.get("source_type") or "state_local"

        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=params.get("headers") or {})
            response.raise_for_status()
            payload = response.json()

        records = _get_path(payload, records_path)
        if isinstance(records, dict):
            records = records.get("items") or records.get("data") or records.get("results")
        if not isinstance(records, list):
            raise ValueError("public_json_feed expected a list of records")

        opportunities: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            title = _field(record, mapping, "title") or record.get("name")
            if not title:
                continue
            description = _field(record, mapping, "description") or record.get("summary") or ""
            agency = _field(record, mapping, "agency")
            due_date = _parse_date(_field(record, mapping, "due_date"))
            specs = extract_specs(f"{title}. {description}")
            classification = classify_bid(title, description, specs)
            record_source_type = _field(record, mapping, "source_type") or source_type
            state = _field(record, mapping, "state")
            opportunities.append(
                {
                    "title": title,
                    "agency": agency,
                    "location": _field(record, mapping, "location"),
                    "state": str(state)[:2].upper() if state else None,
                    "due_date": due_date,
                    "naics_code": _field(record, mapping, "naics_code"),
                    "description": description,
                    "source": source,
                    "source_type": record_source_type or infer_source_type(source, agency),
                    "source_url": _field(record, mapping, "source_url") or record.get("url"),
                    "bid_status": normalize_bid_status(_field(record, mapping, "bid_status", "status"), due_date),
                    "estimated_value": _parse_decimal(_field(record, mapping, "estimated_value")),
                    "attachments": _field(record, mapping, "attachments") or [],
                    "extracted_specs": specs,
                    "project_type": classification["project_type"],
                    "confidence_score": classification["confidence_score"],
                    "classification_explanation": classification["explanation"],
                }
            )
        return opportunities
