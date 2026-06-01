from __future__ import annotations

from datetime import date, datetime
from typing import Any
from urllib.parse import urljoin

import httpx

from app.services.classification import classify_bid
from app.services.extraction import extract_specs
from app.services.ingestion.base import IngestionAdapter
from app.services.ingestion.defaults import DEFAULT_ELECTRICAL_SOURCE_KEYWORDS
from app.services.ingestion.public_html_scrape import HtmlNode, parse_html
from app.services.value_assessment import normalize_bid_status

PA_EMARKETPLACE_URL = "https://www.emarketplace.state.pa.us/Search.aspx/Home.aspx"


def _text(node: HtmlNode | None) -> str | None:
    if not node:
        return None
    value = node.text_content().strip()
    return " ".join(value.split()) if value else None


def _cell(row: HtmlNode, column_header: str) -> HtmlNode | None:
    expected = f"ColumnHeader_{column_header}".lower()
    for node in row.descendants():
        if node.tag != "td":
            continue
        headers = (node.attrs.get("headers") or "").lower()
        if expected in headers:
            return node
    return None


def _cell_text(row: HtmlNode, column_header: str) -> str | None:
    return _text(_cell(row, column_header))


def _detail_url(row: HtmlNode) -> str | None:
    cell = _cell(row, "Solicitation #")
    if not cell:
        return None
    for node in cell.descendants():
        if node.tag == "a" and node.attr("href"):
            return urljoin(PA_EMARKETPLACE_URL, node.attr("href") or "")
    return None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    for pattern in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %I:%M %p", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def _keyword_terms(params: dict[str, Any]) -> list[str]:
    keywords = params.get("keywords") or DEFAULT_ELECTRICAL_SOURCE_KEYWORDS
    if isinstance(keywords, str):
        keywords = [part.strip() for part in keywords.split(",")]
    return [str(keyword).lower() for keyword in keywords if str(keyword).strip()]


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    normalized = text.lower()
    return any(keyword in normalized for keyword in keywords)


class PennsylvaniaEMarketplaceAdapter(IngestionAdapter):
    name = "pa_emarketplace"
    description = "Pennsylvania eMarketplace open solicitation adapter."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        limit = int(params.get("limit") or 25)
        keywords = _keyword_terms(params)
        url = params.get("url") or PA_EMARKETPLACE_URL
        headers = {"User-Agent": params.get("user_agent") or "ElecBidSpecAI/0.1 public-bid-ingestion"}

        with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            root = parse_html(response.text)

        rows = [*root.select("tr.GridItem"), *root.select("tr.GridAltItem")]
        opportunities: list[dict[str, Any]] = []
        for row in rows:
            title = _cell_text(row, "Solicitation Title")
            if not title:
                continue
            solicitation_id = _cell_text(row, "Solicitation #")
            description = _cell_text(row, "Description") or ""
            agency = _cell_text(row, "Agency") or "Commonwealth of Pennsylvania"
            county = _cell_text(row, "County")
            status = _cell_text(row, "Status")
            due_date = _parse_date(_cell_text(row, "Solicitation Due Date"))
            searchable = " ".join([title, description, agency])
            if keywords and not _matches_keywords(searchable, keywords):
                continue

            specs = extract_specs(f"{title}. {description}")
            classification = classify_bid(title, description, specs)
            opportunities.append(
                {
                    "title": title,
                    "agency": agency,
                    "location": ", ".join(part for part in [county, "PA"] if part),
                    "state": "PA",
                    "due_date": due_date,
                    "naics_code": None,
                    "description": "\n".join(
                        part
                        for part in [
                            f"Solicitation ID: {solicitation_id}" if solicitation_id else "",
                            f"Type: {_cell_text(row, 'Types')}" if _cell_text(row, "Types") else "",
                            description,
                            f"Contact: {_cell_text(row, 'Contact Person')}" if _cell_text(row, "Contact Person") else "",
                        ]
                        if part
                    ),
                    "source": self.name,
                    "source_type": "state_local",
                    "source_url": _detail_url(row) or url,
                    "bid_status": normalize_bid_status(status or "open", due_date),
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
