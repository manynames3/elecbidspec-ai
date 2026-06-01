from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

import httpx

from app.services.classification import classify_bid
from app.services.extraction import extract_specs
from app.services.ingestion.base import IngestionAdapter
from app.services.value_assessment import normalize_bid_status

SF_OPEN_BIDS_API_URL = "https://data.sfgov.org/resource/eshn-8t3a.json"

DEFAULT_KEYWORDS = [
    "electrical",
    "electric",
    "power station",
    "power",
    "low voltage",
    "medium voltage",
    "high voltage",
    "cable",
    "conduit",
    "switchgear",
    "transformer",
    "substation",
    "generator",
    "fire alarm",
    "data center",
    "transmission",
    "distribution",
]

OPEN_SF_STATUSES = {"open", "amended"}


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


def _source_url(record: dict[str, Any]) -> str | None:
    link = record.get("sfcitypartner_link")
    if isinstance(link, dict):
        url = link.get("url")
        return str(url) if url else None
    return str(link) if link else None


class SfOpenBidsAdapter(IngestionAdapter):
    name = "sf_open_bids"
    description = "No-key San Francisco Open Bid Opportunities adapter for current public solicitations."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        limit = int(params.get("limit") or 25)
        source_limit = int(params.get("source_limit") or max(limit * 10, 100))
        due_after = params.get("due_after") or date.today().isoformat()
        keywords = _keyword_terms(params)

        query_params = {
            "$limit": min(source_limit, 500),
            "$order": "due_date ASC",
            "$where": f'due_date >= "{due_after}T00:00:00"',
        }
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(params.get("url") or SF_OPEN_BIDS_API_URL, params=query_params)
            response.raise_for_status()
            records = response.json()

        opportunities: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            title = record.get("title")
            if not title:
                continue
            status = str(record.get("status") or "").strip().lower()
            if status and status not in OPEN_SF_STATUSES:
                continue

            searchable = " ".join(
                [
                    str(title),
                    str(record.get("department") or ""),
                    str(record.get("category") or ""),
                    str(record.get("type") or ""),
                ]
            )
            if keywords and not _matches_keywords(searchable, keywords):
                continue

            due_date = _parse_date(record.get("due_date"))
            department = record.get("department")
            agency = f"City and County of San Francisco - {department}" if department else "City and County of San Francisco"
            full_description = "\n".join(
                part
                for part in [
                    f"Department: {department}" if department else "",
                    f"Category: {record.get('category')}" if record.get("category") else "",
                    f"Type: {record.get('type')}" if record.get("type") else "",
                    f"Status: {record.get('status')}" if record.get("status") else "",
                    f"Open date: {record.get('open_date')}" if record.get("open_date") else "",
                    f"Event ID: {record.get('event_id')}" if record.get("event_id") else "",
                ]
                if part
            )
            specs = extract_specs(f"{title}. {full_description}")
            classification = classify_bid(str(title), full_description, specs)
            opportunities.append(
                {
                    "title": str(title),
                    "agency": agency,
                    "location": "San Francisco, CA",
                    "state": "CA",
                    "due_date": due_date,
                    "naics_code": None,
                    "description": full_description,
                    "source": self.name,
                    "source_type": "state_local",
                    "source_url": _source_url(record),
                    "bid_status": normalize_bid_status(record.get("status"), due_date),
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
