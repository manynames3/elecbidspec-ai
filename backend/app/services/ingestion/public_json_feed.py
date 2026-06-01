from __future__ import annotations

import re
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


def _string_value(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, dict):
        nested = value.get("url") or value.get("href") or value.get("link")
        return str(nested) if nested else None
    return str(value)


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


def _format_template(template: str | None, record: dict[str, Any]) -> str | None:
    if not template:
        return None

    def replace(match: re.Match) -> str:
        value = _get_path(record, match.group(1))
        return _string_value(value) or ""

    formatted = re.sub(r"{([^{}]+)}", replace, template)
    return formatted if formatted.strip() else None


def _keyword_terms(params: dict[str, Any]) -> list[str]:
    keywords = params.get("keywords") or []
    if isinstance(keywords, str):
        keywords = [part.strip() for part in keywords.split(",")]
    return [str(keyword).lower() for keyword in keywords if str(keyword).strip()]


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    for keyword in keywords:
        pattern = r"\b" + r"\s+".join(re.escape(part) for part in keyword.split()) + r"\b"
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False


def _record_search_text(record: dict[str, Any], fields: list[str] | None) -> str:
    if not fields:
        return " ".join(str(value) for value in record.values() if value is not None)
    return " ".join(_string_value(_get_path(record, field)) or "" for field in fields)


def _description_from_template(record: dict[str, Any], template: str | None, fallback: Any) -> str:
    if template:
        return _format_template(template, record) or ""
    return _string_value(fallback) or ""


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
        limit = int(params.get("limit") or 25)
        source_limit = int(params.get("source_limit") or max(limit * 10, 100))
        query_params = dict(params.get("query_params") or {})
        query_params.setdefault("$limit", min(source_limit, 5000))
        if params.get("order"):
            query_params.setdefault("$order", params["order"])
        keywords = _keyword_terms(params)
        keyword_fields = params.get("keyword_fields") or []
        status_allow = {str(item).lower() for item in (params.get("status_allow") or [])}
        due_after = _parse_date(params.get("due_after")) or date.today()

        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=params.get("headers") or {}, params=query_params)
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
            status = _field(record, mapping, "bid_status", "status")
            if status_allow and str(status or "").strip().lower() not in status_allow:
                continue
            if not _matches_keywords(_record_search_text(record, keyword_fields), keywords):
                continue

            title = _string_value(_field(record, mapping, "title") or record.get("name"))
            if not title:
                continue
            description = _description_from_template(
                record,
                params.get("description_template"),
                _field(record, mapping, "description") or record.get("summary") or "",
            )
            agency = _string_value(_field(record, mapping, "agency"))
            agency_prefix = params.get("agency_prefix")
            if agency_prefix and agency:
                agency = f"{agency_prefix} - {agency}"
            elif agency_prefix:
                agency = str(agency_prefix)
            due_date = _parse_date(_field(record, mapping, "due_date"))
            if due_date and due_date < due_after:
                continue
            specs = extract_specs(f"{title}. {description}")
            classification = classify_bid(title, description, specs)
            record_source_type = _field(record, mapping, "source_type") or source_type
            state = _field(record, mapping, "state") or params.get("state")
            source_url = (
                _string_value(_field(record, mapping, "source_url"))
                or _string_value(record.get("url"))
                or _format_template(params.get("source_url_template"), record)
            )
            opportunities.append(
                {
                    "title": title,
                    "agency": agency,
                    "location": _string_value(_field(record, mapping, "location")) or params.get("location"),
                    "state": str(state)[:2].upper() if state else None,
                    "due_date": due_date,
                    "naics_code": _string_value(_field(record, mapping, "naics_code")),
                    "description": description,
                    "source": source,
                    "source_type": record_source_type or infer_source_type(source, agency),
                    "source_url": source_url,
                    "bid_status": normalize_bid_status(status, due_date),
                    "estimated_value": _parse_decimal(_field(record, mapping, "estimated_value")),
                    "attachments": _field(record, mapping, "attachments") or [],
                    "extracted_specs": specs,
                    "project_type": classification["project_type"],
                    "confidence_score": classification["confidence_score"],
                    "classification_explanation": classification["explanation"],
                }
            )
            if len(opportunities) >= limit:
                break
        return opportunities
