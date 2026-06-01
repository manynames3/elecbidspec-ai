from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy.orm import Session

from app.models import Opportunity, OpportunityAttachmentExtraction
from app.services.extraction import extract_specs, normalize_text, parse_attachment
from app.services.storage import store_upload

DOCUMENT_LINK_TERMS = [
    "rfp",
    "ifb",
    "bid package",
    "solicitation",
    "spec",
    "specification",
    "addendum",
    "plans",
    "drawings",
    "scope",
    "attachment",
    "download",
]

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".text", ".csv"}
MAX_ATTACHMENT_BYTES = 12 * 1024 * 1024


@dataclass(frozen=True)
class CandidateDocument:
    url: str
    label: str | None = None


class _DocumentLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[dict[str, str]] = []
        self._active_href: str | None = None
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = {key.lower(): value or "" for key, value in attrs}
        href = attrs_dict.get("href")
        if href:
            self._active_href = href
            self._text_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._active_href:
            self.links.append({"href": self._active_href, "text": normalize_text(" ".join(self._text_parts))})
            self._active_href = None
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._active_href:
            self._text_parts.append(data)


def _is_public_http_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return False
    hostname = parsed.hostname.lower()
    if hostname in {"localhost", "127.0.0.1", "::1"} or hostname.endswith(".local"):
        return False
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        return True
    return not (address.is_private or address.is_loopback or address.is_link_local or address.is_reserved)


def _filename_from_url(url: str, content_type: str | None = None) -> str:
    parsed_name = Path(urlparse(url).path).name
    if parsed_name and "." in parsed_name:
        return parsed_name[:240]
    if content_type and "pdf" in content_type.lower():
        return "attachment.pdf"
    return parsed_name[:240] or "attachment.txt"


def _looks_like_document(url: str, label: str | None = None) -> bool:
    path = urlparse(url).path.lower()
    suffix = Path(path).suffix
    if suffix in SUPPORTED_EXTENSIONS:
        return True
    combined = f"{path} {label or ''}".lower()
    return any(term in combined for term in DOCUMENT_LINK_TERMS)


def _candidate_urls_from_html(html: str, base_url: str, max_links: int) -> list[CandidateDocument]:
    parser = _DocumentLinkParser()
    parser.feed(html)
    candidates: list[CandidateDocument] = []
    seen: set[str] = set()
    for link in parser.links:
        href = link.get("href") or ""
        if href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        if absolute in seen or not _is_public_http_url(absolute):
            continue
        label = link.get("text") or None
        if not _looks_like_document(absolute, label):
            continue
        seen.add(absolute)
        candidates.append(CandidateDocument(absolute, label))
        if len(candidates) >= max_links:
            break
    return candidates


def _candidate_documents(opportunity: Opportunity, client: httpx.Client, max_links: int) -> list[CandidateDocument]:
    candidates: list[CandidateDocument] = []
    seen: set[str] = set()
    for attachment in opportunity.attachments or []:
        if not isinstance(attachment, dict):
            continue
        url = str(attachment.get("url") or attachment.get("href") or attachment.get("source_url") or "")
        if url and url not in seen and _is_public_http_url(url):
            seen.add(url)
            candidates.append(CandidateDocument(url, str(attachment.get("name") or "") or None))

    source_url = opportunity.source_url
    if source_url and _is_public_http_url(source_url) and source_url not in seen:
        if _looks_like_document(source_url):
            candidates.append(CandidateDocument(source_url, opportunity.title))
            seen.add(source_url)
        else:
            response = client.get(source_url)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type.lower() or "<html" in response.text[:500].lower():
                for candidate in _candidate_urls_from_html(response.text, source_url, max_links=max_links):
                    if candidate.url not in seen:
                        candidates.append(candidate)
                        seen.add(candidate.url)
            elif _looks_like_document(source_url, content_type):
                candidates.append(CandidateDocument(source_url, opportunity.title))
    return candidates[:max_links]


def merge_specs(existing: dict | None, incoming: dict | None) -> dict:
    merged = dict(existing or {})
    incoming = incoming or {}
    for key, value in incoming.items():
        if isinstance(value, list):
            current = [str(item) for item in merged.get(key, []) if str(item).strip()] if isinstance(merged.get(key), list) else []
            for item in value:
                text = str(item).strip()
                if text and text not in current:
                    current.append(text)
            merged[key] = current[:24]
        elif key == "source_text_preview" and value:
            current_preview = str(merged.get(key) or "")
            extra = str(value)
            merged[key] = normalize_text(f"{current_preview} {extra}")[:1600]
        elif key not in merged or not merged.get(key):
            merged[key] = value
    return merged


def ingest_opportunity_attachments(db: Session, opportunity: Opportunity, max_links: int = 8) -> list[OpportunityAttachmentExtraction]:
    headers = {"User-Agent": "ElecBidSpecAI/0.1 public-document-ingestion"}
    results: list[OpportunityAttachmentExtraction] = []
    attachments = list(opportunity.attachments or [])
    existing_urls = {
        str(item.get("url") or item.get("source_url") or item.get("stored_path") or "")
        for item in attachments
        if isinstance(item, dict)
    }

    with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
        candidates = _candidate_documents(opportunity, client, max_links=max_links)
        for candidate in candidates:
            existing = (
                db.query(OpportunityAttachmentExtraction)
                .filter(
                    OpportunityAttachmentExtraction.opportunity_id == opportunity.id,
                    OpportunityAttachmentExtraction.source_url == candidate.url,
                )
                .first()
            )
            if existing and existing.status == "complete":
                results.append(existing)
                continue
            extraction = existing or OpportunityAttachmentExtraction(
                opportunity_id=opportunity.id,
                source_url=candidate.url,
                filename=candidate.label,
                status="running",
            )
            if not existing:
                db.add(extraction)
                db.flush()
            try:
                response = client.get(candidate.url)
                response.raise_for_status()
                content = response.content[:MAX_ATTACHMENT_BYTES]
                content_type = response.headers.get("content-type")
                filename = _filename_from_url(candidate.url, content_type)
                attachment = store_upload(content, filename, content_type)
                attachment["url"] = candidate.url
                attachment["label"] = candidate.label
                text = parse_attachment(content, filename)
                specs = extract_specs(text)

                extraction.filename = filename
                extraction.status = "complete"
                extraction.attachment = attachment
                extraction.extracted_specs = specs
                extraction.error = None
                if candidate.url not in existing_urls:
                    attachments.append(attachment)
                    existing_urls.add(candidate.url)
                opportunity.extracted_specs = merge_specs(opportunity.extracted_specs, specs)
                opportunity.attachments = attachments
            except Exception as exc:  # noqa: BLE001 - keep per-document failures inspectable
                extraction.status = "failed"
                extraction.error = str(exc)
            results.append(extraction)
    db.commit()
    for result in results:
        db.refresh(result)
    db.refresh(opportunity)
    return results
