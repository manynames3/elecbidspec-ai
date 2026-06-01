from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import quote

import httpx

from app.services.classification import classify_bid
from app.services.extraction import extract_specs
from app.services.ingestion.base import IngestionAdapter
from app.services.value_assessment import normalize_bid_status

TXDOT_BID_ITEMS_API_URL = "https://data.texas.gov/resource/qh8x-rm8r.json"
TXDOT_DATASET_URL = "https://data.texas.gov/Transportation/Official-and-Unofficial-Bid-Items/qh8x-rm8r"

DEFAULT_KEYWORDS = [
    "electrical",
    "electric",
    "illumination",
    "lighting",
    "conduit",
    "conductor",
    "cable",
    "fiber",
    "traffic signal",
    "signal cable",
    "switchgear",
    "transformer",
    "ground box",
    "pull box",
    "duct bank",
]


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace(",", "").replace("$", ""))
    except (InvalidOperation, ValueError):
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


def _project_key(record: dict[str, Any]) -> str:
    return str(
        record.get("controlling_project_id_ccsj")
        or record.get("control_section_job_csj")
        or record.get("project_id")
        or record.get("project_number")
        or ""
    )


def _project_title(record: dict[str, Any]) -> str:
    pieces = [
        "TxDOT",
        record.get("highway"),
        record.get("county"),
        record.get("project_classification") or record.get("project_type"),
        record.get("project_number"),
    ]
    return " - ".join(str(piece).strip() for piece in pieces if str(piece or "").strip())


class TxdotBidItemsAdapter(IngestionAdapter):
    name = "txdot_bid_items"
    description = "No-key TxDOT official bid item adapter with project-level deduping."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        limit = int(params.get("limit") or 25)
        source_limit = int(params.get("source_limit") or max(limit * 80, 1000))
        due_after = params.get("due_after") or date.today().isoformat()
        keywords = _keyword_terms(params)

        query_params = {
            "$limit": min(source_limit, 5000),
            "$order": "bid_recieved_until_date_and ASC",
            "$where": f'bid_recieved_until_date_and >= "{due_after}T00:00:00"',
        }
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(params.get("url") or TXDOT_BID_ITEMS_API_URL, params=query_params)
            response.raise_for_status()
            rows = response.json()

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            if not isinstance(row, dict):
                continue
            searchable = " ".join(
                str(row.get(field) or "")
                for field in [
                    "bid_item_description",
                    "specification_description",
                    "project_classification",
                    "project_type",
                    "highway",
                    "county",
                    "district_division",
                ]
            )
            if keywords and not _matches_keywords(searchable, keywords):
                continue
            key = _project_key(row)
            if key:
                grouped[key].append(row)

        opportunities: list[dict[str, Any]] = []
        for key, project_rows in grouped.items():
            first = project_rows[0]
            due_date = _parse_date(first.get("bid_recieved_until_date_and") or first.get("bids_will_be_opened_date"))
            item_lines = [
                f"{row.get('bid_item_description')} ({row.get('specification_description')})"
                for row in project_rows[:12]
                if row.get("bid_item_description") or row.get("specification_description")
            ]
            description = "\n".join(
                part
                for part in [
                    f"Project: {first.get('project_number') or key}",
                    f"CSJ: {first.get('control_section_job_csj') or key}",
                    f"District: {first.get('district_division')}" if first.get("district_division") else "",
                    f"County: {first.get('county')}" if first.get("county") else "",
                    f"Highway: {first.get('highway')}" if first.get("highway") else "",
                    f"Let type: {first.get('let_type')}" if first.get("let_type") else "",
                    f"Proposal status: {first.get('proposal_status')}" if first.get("proposal_status") else "",
                    f"Proposal guarantee amount: {first.get('proposal_guarantee_amount')}" if first.get("proposal_guarantee_amount") else "",
                    "Relevant bid items: " + "; ".join(item_lines) if item_lines else "",
                ]
                if part
            )
            title = _project_title(first) or f"TxDOT project {key}"
            specs = extract_specs(f"{title}. {description}")
            classification = classify_bid(title, description, specs)
            source_url = f"{TXDOT_DATASET_URL}?controlling_project_id_ccsj={quote(key)}"
            opportunities.append(
                {
                    "title": title,
                    "agency": "Texas Department of Transportation",
                    "location": ", ".join(part for part in [first.get("county"), "TX"] if part),
                    "state": "TX",
                    "due_date": due_date,
                    "naics_code": None,
                    "description": description,
                    "source": self.name,
                    "source_type": "state_local",
                    "source_url": source_url,
                    "bid_status": normalize_bid_status("open", due_date),
                    "estimated_value": _parse_decimal(first.get("sealed_engineer_s_estimate_1") or first.get("sealed_engineer_s_estimate")),
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
