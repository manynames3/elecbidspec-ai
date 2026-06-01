from __future__ import annotations

import re
from datetime import date, datetime
from html.parser import HTMLParser
from typing import Any

import httpx

from app.services.classification import classify_bid
from app.services.extraction import extract_specs
from app.services.ingestion.base import IngestionAdapter
from app.services.value_assessment import normalize_bid_status

NYC_CITY_RECORD_API_URL = "https://data.cityofnewyork.us/resource/3khw-qi8f.json"
NYC_CITY_RECORD_DETAIL_URL = "https://a856-cityrecord.nyc.gov/RequestDetail/{request_id}"

DEFAULT_KEYWORDS = [
    "electrical",
    "electric",
    "power",
    "shore power",
    "low voltage",
    "medium voltage",
    "high voltage",
    "cable",
    "conduit",
    "switchgear",
    "transformer",
    "substation",
    "feeder",
    "generator",
    "lighting",
    "fire alarm",
    "charging",
    "energization",
]


class _HtmlTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        return " ".join(self.parts)


def _html_to_text(value: Any) -> str:
    parser = _HtmlTextParser()
    parser.feed(str(value or ""))
    return parser.text()


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _keyword_terms(params: dict[str, Any]) -> list[str]:
    keywords = params.get("keywords") or DEFAULT_KEYWORDS
    if isinstance(keywords, str):
        keywords = [part.strip() for part in keywords.split(",")]
    return [str(keyword).lower() for keyword in keywords if str(keyword).strip()]


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    for keyword in keywords:
        pattern = r"\b" + r"\s+".join(re.escape(part) for part in keyword.split()) + r"\b"
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False


def _matches_any_text(text: str, terms: list[str]) -> bool:
    return any(term.lower() in text.lower() for term in terms)


class NycCityRecordAdapter(IngestionAdapter):
    name = "nyc_city_record"
    description = "No-key NYC City Record/Open Data adapter for current public solicitations."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        limit = int(params.get("limit") or 25)
        source_limit = int(params.get("source_limit") or max(limit * 8, 100))
        due_after = params.get("due_after") or date.today().isoformat()
        keywords = _keyword_terms(params)
        agency_terms = params.get("agency_keywords") or []
        if isinstance(agency_terms, str):
            agency_terms = [part.strip() for part in agency_terms.split(",")]

        query_params = {
            "$limit": min(source_limit, 500),
            "$order": "due_date ASC",
            "$where": f"due_date >= '{due_after}T00:00:00' AND type_of_notice_description = 'Solicitation'",
        }
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(params.get("url") or NYC_CITY_RECORD_API_URL, params=query_params)
            response.raise_for_status()
            records = response.json()

        opportunities: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            title = record.get("short_title") or record.get("title")
            if not title:
                continue
            description = _html_to_text(record.get("additional_description_1"))
            searchable = " ".join(
                [
                    str(title),
                    str(record.get("category_description") or ""),
                    str(record.get("selection_method_description") or ""),
                    description,
                ]
            ).lower()
            if keywords and not _matches_keywords(searchable, keywords):
                continue

            request_id = record.get("request_id")
            due_date = _parse_date(record.get("due_date"))
            agency = record.get("agency_name")
            if agency_terms and not _matches_any_text(str(agency or ""), [str(term) for term in agency_terms]):
                continue
            full_description = "\n".join(
                part
                for part in [
                    f"Category: {record.get('category_description')}" if record.get("category_description") else "",
                    f"Method: {record.get('selection_method_description')}" if record.get("selection_method_description") else "",
                    f"PIN: {record.get('pin')}" if record.get("pin") else "",
                    f"Contact: {record.get('email')}" if record.get("email") else "",
                    description,
                ]
                if part
            )
            specs = extract_specs(f"{title}. {full_description}")
            classification = classify_bid(str(title), full_description, specs)
            opportunities.append(
                {
                    "title": str(title),
                    "agency": agency,
                    "location": record.get("address_to_request") or "New York, NY",
                    "state": "NY",
                    "due_date": due_date,
                    "naics_code": None,
                    "description": full_description,
                    "source": params.get("source") or self.name,
                    "source_type": params.get("source_type") or "state_local",
                    "source_url": NYC_CITY_RECORD_DETAIL_URL.format(request_id=request_id) if request_id else None,
                    "bid_status": normalize_bid_status("open", due_date),
                    "estimated_value": None,
                    "attachments": [],
                    "extracted_specs": specs,
                    "project_type": classification["project_type"],
                    "confidence_score": classification["confidence_score"],
                    "classification_explanation": classification["explanation"],
                }
            )
            if len(opportunities) >= limit:
                break
        return opportunities
