from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.services.classification import classify_bid
from app.services.extraction import extract_specs, normalize_text
from app.services.ingestion.base import IngestionAdapter
from app.services.value_assessment import normalize_bid_status

DEFAULT_JEA_URLS = [
    "https://www.jea.com/about/procurement/formal_procurement_opportunities/?ns=y",
    "https://www.jea.com/about/procurement/informal_procurement_opportunities/?ns=y",
]

SOLICITATION_PATTERN = re.compile(r"\b\d{6,12}\b")
DOCUMENT_TERMS = [
    "solicitation",
    "ifb",
    "rfp",
    "appendix",
    "attachment",
    "technical specification",
    "technical specifications",
    "addendum",
    "bid forms",
    "response forms",
    "evaluation matrix",
]
ELECTRICAL_TERMS = [
    "electric",
    "electrical",
    "cable",
    "conduit",
    "substation",
    "transformer",
    "switchgear",
    "underground",
    "medium voltage",
    "high voltage",
    "power",
    "generator",
    "transmission",
    "distribution",
]


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        href = attrs_dict.get("href")
        if href:
            self._href = href
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append({"href": self._href, "text": normalize_text(" ".join(self._parts))})
            self._href = None
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._parts.append(data)


def _parse_date(text: str):
    patterns = [
        ("%m/%d/%Y", r"\b\d{1,2}/\d{1,2}/\d{4}\b"),
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
    value = match.group(0).lower().replace("$", "").replace(",", "").strip()
    multiplier = Decimal("1")
    if value.endswith(("m", "mil", "million")):
        multiplier = Decimal("1000000")
        value = value.replace("million", "").replace("mil", "").removesuffix("m").strip()
    try:
        return Decimal(value) * multiplier
    except Exception:
        return None


def _is_document_link(text: str, href: str) -> bool:
    combined = f"{text} {href}".lower()
    if not any(term in combined for term in DOCUMENT_TERMS):
        return False
    suffix = Path(urlparse(href).path.lower()).suffix
    return suffix not in {".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js", ".ico", ".zip"}


class JeaProcurementAdapter(IngestionAdapter):
    name = "jea_procurement"
    description = "JEA formal/informal procurement adapter grouping solicitation document links by solicitation number."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        raw_urls = params.get("urls") or ([params.get("url")] if params.get("url") else DEFAULT_JEA_URLS)
        urls = [str(url) for url in raw_urls if str(url).strip()]
        source = params.get("source") or params.get("job_label") or "jea"
        source_type = params.get("source_type") or "utility"
        agency = params.get("agency") or params.get("label") or "JEA"
        state = params.get("state") or "FL"
        location = params.get("location") or "Jacksonville, FL"
        limit = int(params.get("limit") or 25)
        source_limit = int(params.get("source_limit") or 1200)
        include_all = bool(params.get("include_all"))
        keywords = [str(keyword).lower() for keyword in (params.get("keywords") or ELECTRICAL_TERMS) if str(keyword).strip()]

        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        headers = {"User-Agent": params.get("user_agent") or "Mozilla/5.0 ElecBidSpecAI/0.1 jea"}
        with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
            for url in urls:
                response = client.get(url)
                response.raise_for_status()
                parser = _AnchorParser()
                parser.feed(response.text)
                for link in parser.links[:source_limit]:
                    text = link.get("text") or ""
                    href = link.get("href") or ""
                    if not _is_document_link(text, href):
                        continue
                    match = SOLICITATION_PATTERN.search(f"{text} {href}")
                    if not match:
                        continue
                    grouped[match.group(0)].append({"text": text, "url": urljoin(url, href)})

        opportunities: list[dict[str, Any]] = []
        for solicitation_id, documents in grouped.items():
            seen_docs: set[str] = set()
            unique_docs = []
            for document in documents:
                if document["url"] in seen_docs:
                    continue
                seen_docs.add(document["url"])
                unique_docs.append(document)
            combined = normalize_text(" ".join(document["text"] for document in unique_docs))
            if not include_all and keywords and not any(keyword in combined.lower() for keyword in keywords):
                if "technical specification" not in combined.lower() and "appendix" not in combined.lower():
                    continue

            solicitation_doc = next((doc for doc in unique_docs if "solicitation" in doc["text"].lower()), unique_docs[0])
            title = normalize_text(solicitation_doc["text"])
            if not title.lower().startswith("jea"):
                title = f"JEA {title}"
            description = (
                f"JEA procurement package grouped from public formal/informal solicitation documents. "
                f"Solicitation ID: {solicitation_id}. Documents: {combined[:1400]}"
            )
            specs = extract_specs(f"{title}. {description}")
            classification = classify_bid(title, description, specs)
            attachments = [
                {"name": document["text"] or f"JEA {solicitation_id} document", "url": document["url"], "source": "jea_procurement"}
                for document in unique_docs[:12]
            ]
            due_date = _parse_date(combined)
            opportunities.append(
                {
                    "title": title[:280],
                    "agency": agency,
                    "location": location,
                    "state": str(state)[:2].upper() if state else None,
                    "due_date": due_date,
                    "naics_code": None,
                    "description": description,
                    "source": source,
                    "source_type": source_type,
                    "source_url": solicitation_doc["url"],
                    "bid_status": normalize_bid_status("open", due_date),
                    "estimated_value": _parse_decimal(combined),
                    "attachments": attachments,
                    "extracted_specs": specs,
                    "project_type": classification["project_type"],
                    "confidence_score": classification["confidence_score"],
                    "classification_explanation": classification["explanation"],
                }
            )
            if len(opportunities) >= limit:
                break
        return opportunities
