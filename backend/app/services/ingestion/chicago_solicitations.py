from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any
from urllib.parse import urljoin

import httpx

from app.services.classification import classify_bid
from app.services.extraction import extract_specs
from app.services.ingestion.base import IngestionAdapter
from app.services.ingestion.public_html_scrape import HtmlNode, parse_html
from app.services.value_assessment import normalize_bid_status

CHICAGO_SOLICITATIONS_URL = "https://webapps1.chicago.gov/vcsearch/prtf/solicitations"

DEFAULT_KEYWORDS = [
    "electrical",
    "electric",
    "battery-electric",
    "power",
    "cable",
    "conduit",
    "switchgear",
    "transformer",
    "substation",
    "generator",
    "fire alarm",
    "transmission",
    "distribution",
    "voltage",
    "lighting infrastructure",
]


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for pattern in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[:10], pattern).date()
        except ValueError:
            continue
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


def _cell_text(cell: HtmlNode) -> str:
    return re.sub(r"\s+", " ", cell.text_content()).strip()


class ChicagoSolicitationsAdapter(IngestionAdapter):
    name = "chicago_solicitations"
    description = "No-key City of Chicago/CTA public solicitation table adapter."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        limit = int(params.get("limit") or 25)
        keywords = _keyword_terms(params)
        due_after = _parse_date(params.get("due_after")) or date.today()
        url = params.get("url") or CHICAGO_SOLICITATIONS_URL
        headers = {"User-Agent": params.get("user_agent") or "ElecBidSpecAI/0.1 public-bid-ingestion"}

        with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            root = parse_html(response.text)

        opportunities: list[dict[str, Any]] = []
        for row in root.select("table#resultstable tr"):
            cells = row.select("td")
            if len(cells) < 8:
                continue

            agency_code = _cell_text(cells[0])
            procurement_type = _cell_text(cells[1])
            specification_number = _cell_text(cells[2])
            title = _cell_text(cells[3])
            status = _cell_text(cells[4])
            category = _cell_text(cells[5])
            due_date = _parse_date(_cell_text(cells[6]))
            detail_href = cells[7].select("a")[0].attr("href") if cells[7].select("a") else None

            if not title or status.lower() not in {"active", "open"}:
                continue
            if due_date and due_date < due_after:
                continue
            searchable = " ".join([title, category, procurement_type, specification_number])
            if keywords and not _matches_keywords(searchable, keywords):
                continue

            agency = "Chicago Transit Authority" if agency_code.upper() == "CTA" else "City of Chicago"
            description = "\n".join(
                part
                for part in [
                    f"Agency: {agency}",
                    f"Procurement type: {procurement_type}" if procurement_type else "",
                    f"Specification number: {specification_number}" if specification_number else "",
                    f"Category: {category}" if category else "",
                    f"Status: {status}" if status else "",
                ]
                if part
            )
            specs = extract_specs(f"{title}. {description}")
            classification = classify_bid(title, description, specs)
            opportunities.append(
                {
                    "title": title,
                    "agency": agency,
                    "location": "Chicago, IL",
                    "state": "IL",
                    "due_date": due_date,
                    "naics_code": None,
                    "description": description,
                    "source": self.name,
                    "source_type": "state_local",
                    "source_url": urljoin(url, detail_href) if detail_href else url,
                    "bid_status": normalize_bid_status(status, due_date),
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
