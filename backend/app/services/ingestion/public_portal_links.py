from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.services.classification import classify_bid
from app.services.extraction import extract_specs, normalize_text
from app.services.ingestion.base import IngestionAdapter
from app.services.value_assessment import infer_source_type, normalize_bid_status

PROCUREMENT_TERMS = [
    "bid",
    "bids",
    "ifb",
    "rfb",
    "rfp",
    "solicitation",
    "opportunity",
    "advertisement",
    "letting",
    "procurement",
    "contract",
]


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        href = attrs_dict.get("href")
        if href:
            self._href = href
            self._text = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append({"href": self._href, "text": normalize_text(" ".join(self._text))})
            self._href = None
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)


def _parse_date(text: str) -> date | None:
    patterns = [
        ("%Y-%m-%d", r"\b\d{4}-\d{2}-\d{2}\b"),
        ("%m/%d/%Y", r"\b\d{1,2}/\d{1,2}/\d{4}\b"),
        ("%m/%d/%y", r"\b\d{1,2}/\d{1,2}/\d{2}\b"),
        ("%B %d, %Y", r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b"),
        ("%b %d, %Y", r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+\d{1,2},\s+\d{4}\b"),
    ]
    for fmt, pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        value = match.group(0).replace("Sept", "Sep").replace(".", "")
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(text: str) -> Decimal | None:
    match = re.search(r"\$\s?\d[\d,]*(?:\.\d+)?\s?(?:m|mil|million)?", text, flags=re.IGNORECASE)
    if not match:
        return None
    cleaned = match.group(0).lower().replace("$", "").replace(",", "").strip()
    multiplier = Decimal("1")
    if cleaned.endswith(("m", "mil", "million")):
        multiplier = Decimal("1000000")
        cleaned = cleaned.replace("million", "").replace("mil", "").removesuffix("m").strip()
    try:
        return Decimal(cleaned) * multiplier
    except Exception:
        return None


def _is_usable_href(href: str) -> bool:
    if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return False
    suffix = Path(urlparse(href).path.lower()).suffix
    return suffix not in {".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js", ".ico", ".zip"}


class PublicPortalLinksAdapter(IngestionAdapter):
    name = "public_portal_links"
    description = "Generic public portal link monitor for electrical bid/spec links exposed in static HTML."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        url = params.get("url")
        if not url:
            raise ValueError("public_portal_links requires params.url")

        keywords = [str(keyword).lower() for keyword in (params.get("keywords") or []) if str(keyword).strip()]
        if not keywords:
            keywords = [
                "electrical",
                "electric",
                "cable",
                "conduit",
                "substation",
                "transformer",
                "medium voltage",
                "high voltage",
                "fiber",
                "data center",
                "utility",
                "transmission",
                "distribution",
            ]
        procurement_terms = [str(term).lower() for term in (params.get("procurement_terms") or PROCUREMENT_TERMS)]
        source = params.get("source") or params.get("job_label") or "public_portal_links"
        source_type = params.get("source_type") or "state_local"
        agency = params.get("agency")
        state = params.get("state")
        location = params.get("location")
        limit = int(params.get("limit") or 25)
        source_limit = int(params.get("source_limit") or 400)

        headers = {"User-Agent": params.get("user_agent") or "ElecBidSpecAI/0.1 public-portal-links"}
        with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
            response = client.get(url)
            response.raise_for_status()
            parser = _AnchorParser()
            parser.feed(response.text)

        opportunities: list[dict[str, Any]] = []
        seen: set[str] = set()
        for link in parser.links[:source_limit]:
            href = link.get("href") or ""
            if not _is_usable_href(href):
                continue
            absolute_url = urljoin(url, href)
            if absolute_url in seen:
                continue
            text = link.get("text") or Path(urlparse(absolute_url).path).stem.replace("-", " ").replace("_", " ")
            combined = f"{text} {absolute_url}".lower()
            if not any(keyword in combined for keyword in keywords):
                continue
            if not any(term in combined for term in procurement_terms):
                continue
            title = normalize_text(text)[:260]
            if len(title) < 8:
                continue
            seen.add(absolute_url)
            due_date = _parse_date(text)
            description = (
                f"Candidate public bid/spec link identified on {params.get('label') or source}: {title}. "
                f"Source portal: {url}. Link text: {text}"
            )
            specs = extract_specs(f"{title}. {description}")
            classification = classify_bid(title, description, specs)
            opportunities.append(
                {
                    "title": title,
                    "agency": agency or params.get("label") or source,
                    "location": location,
                    "state": str(state)[:2].upper() if state else None,
                    "due_date": due_date,
                    "naics_code": None,
                    "description": description,
                    "source": source,
                    "source_type": source_type or infer_source_type(source, agency),
                    "source_url": absolute_url,
                    "bid_status": normalize_bid_status(params.get("bid_status") or "open", due_date),
                    "estimated_value": _parse_decimal(text),
                    "attachments": [{"name": title, "url": absolute_url, "source": "portal_link"}],
                    "extracted_specs": specs,
                    "project_type": classification["project_type"],
                    "confidence_score": classification["confidence_score"],
                    "classification_explanation": classification["explanation"],
                }
            )
            if len(opportunities) >= limit:
                break
        return opportunities
