from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.services.classification import classify_bid
from app.services.extraction import extract_specs, normalize_text
from app.services.ingestion.base import IngestionAdapter
from app.services.ingestion.public_html_scrape import HtmlNode, parse_html
from app.services.value_assessment import infer_source_type, normalize_bid_status

DEFAULT_PROCUREMENT_TERMS = [
    "bid",
    "bids",
    "ifb",
    "rfb",
    "rfp",
    "rfq",
    "solicitation",
    "advertisement",
    "letting",
    "proposal",
    "contract",
    "procurement",
]

DEFAULT_SKIP_PATTERNS = [
    "copyright",
    "privacy",
    "terms of use",
    "sign in",
    "login",
    "register now",
    "navigation",
    "facebook",
    "instagram",
    "youtube",
]


def _parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    text = normalize_text(str(value)).replace("Sept.", "Sep.").replace("Sept ", "Sep ")
    patterns = [
        ("%Y-%m-%d", r"\b\d{4}-\d{2}-\d{2}\b"),
        ("%m/%d/%Y", r"\b\d{1,2}/\d{1,2}/\d{4}\b"),
        ("%m/%d/%y", r"\b\d{1,2}/\d{1,2}/\d{2}\b"),
        ("%d-%b-%Y", r"\b\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)-\d{4}\b"),
        ("%B %d, %Y", r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b"),
        ("%b %d, %Y", r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},\s+\d{4}\b"),
    ]
    for fmt, pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        raw = match.group(0).replace(".", "")
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    match = re.search(r"\$\s?\d[\d,]*(?:\.\d+)?\s?(?:b|bn|billion|m|mil|million)?", str(value), flags=re.IGNORECASE)
    if not match:
        return None
    cleaned = match.group(0).lower().replace("$", "").replace(",", "").strip()
    multiplier = Decimal("1")
    if cleaned.endswith(("b", "bn", "billion")):
        multiplier = Decimal("1000000000")
        cleaned = cleaned.replace("billion", "").replace("bn", "").removesuffix("b").strip()
    elif cleaned.endswith(("m", "mil", "million")):
        multiplier = Decimal("1000000")
        cleaned = cleaned.replace("million", "").replace("mil", "").removesuffix("m").strip()
    try:
        return Decimal(cleaned) * multiplier
    except Exception:
        return None


def _direct_children(node: HtmlNode, tags: set[str]) -> list[HtmlNode]:
    return [child for child in node.children if child.tag in tags]


def _links(node: HtmlNode, base_url: str) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    seen: set[str] = set()
    for candidate in [node, *node.descendants()]:
        if candidate.tag != "a":
            continue
        href = candidate.attr("href")
        if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        absolute = urljoin(base_url, href)
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append({"name": normalize_text(candidate.text_content()) or absolute, "url": absolute})
    return links


def _format_template(template: str | None, values: dict[str, str]) -> str | None:
    if not template:
        return None

    def replace(match: re.Match) -> str:
        return values.get(match.group(1), "")

    formatted = re.sub(r"{([^{}]+)}", replace, template)
    return normalize_text(formatted) or None


def _text_matches_terms(text: str, terms: list[str]) -> bool:
    if not terms:
        return True
    for term in terms:
        parts = [re.escape(part) for part in term.lower().split()]
        pattern = r"\b" + r"\s+".join(parts) + r"\b"
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False


def _is_fetchable_detail(url: str, page_url: str) -> bool:
    parsed = urlparse(url)
    page = urlparse(page_url)
    if parsed.netloc and parsed.netloc != page.netloc:
        return False
    return not parsed.path.lower().endswith((".pdf", ".zip", ".doc", ".docx", ".xls", ".xlsx"))


def _collect_embedded_html(value: Any, field_names: set[str] | None = None, current_key: str | None = None) -> list[str]:
    fragments: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            fragments.extend(_collect_embedded_html(child, field_names, str(key)))
    elif isinstance(value, list):
        for child in value:
            fragments.extend(_collect_embedded_html(child, field_names, current_key))
    elif isinstance(value, str):
        should_consider = not field_names or (current_key or "").lower() in field_names
        if should_consider and re.search(r"<(?:table|tr|li|article|a)\b", value, flags=re.IGNORECASE):
            fragments.append(value)
    return fragments


def _roots_from_response(text: str, parse_json_html: bool, json_html_fields: list[str]) -> list[HtmlNode]:
    if not parse_json_html and not json_html_fields:
        return [parse_html(text)]

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return [parse_html(text)]

    field_names = {field.lower() for field in json_html_fields if field}
    fragments = _collect_embedded_html(payload, field_names or None)
    if not fragments:
        return [parse_html(text)]
    return [parse_html("\n".join(fragments))]


class PublicBidPageAdapter(IngestionAdapter):
    name = "public_bid_page"
    description = "Source-configured public bid page adapter for official tables and list pages."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        pages = params.get("pages") or [params.get("url")]
        pages = [str(page) for page in pages if page]
        if not pages:
            raise ValueError("public_bid_page requires params.url or params.pages")

        source = params.get("source") or "public_bid_page"
        source_type = params.get("source_type") or "state_local"
        agency = params.get("agency") or params.get("label")
        state = params.get("state")
        location = params.get("location")
        limit = int(params.get("limit") or 25)
        source_limit = int(params.get("source_limit") or 500)
        selectors = params.get("candidate_selectors") or ["tr", "li", "article"]
        keywords = [str(keyword).lower() for keyword in (params.get("keywords") or []) if str(keyword).strip()]
        procurement_terms = [str(term).lower() for term in (params.get("procurement_terms") or DEFAULT_PROCUREMENT_TERMS)]
        skip_patterns = [str(pattern).lower() for pattern in (params.get("skip_patterns") or DEFAULT_SKIP_PATTERNS)]
        require_keywords = _parse_bool(params.get("require_keywords"), True)
        require_procurement_terms = _parse_bool(params.get("require_procurement_terms"), False)
        fetch_detail = _parse_bool(params.get("fetch_detail"), False)
        detail_template = params.get("detail_url_template")
        due_after = _parse_date(params.get("due_after")) or date.today()
        title_column = params.get("title_column")
        due_date_column = params.get("due_date_column")
        source_url_column = params.get("source_url_column")
        status_column = params.get("status_column")
        estimated_value_column = params.get("estimated_value_column")
        source_url_pattern = params.get("source_url_pattern")
        parse_json_html = _parse_bool(params.get("parse_json_html"), False)
        json_html_fields = [str(field) for field in (params.get("json_html_fields") or [])]
        min_text_length = int(params.get("min_text_length") or 16)
        headers = {
            "User-Agent": params.get("user_agent") or "Mozilla/5.0 ElecBidSpecAI/0.1 public-bid-page",
            **(params.get("headers") or {}),
        }

        opportunities: list[dict[str, Any]] = []
        seen: set[str] = set()
        verify_tls = _parse_bool(params.get("verify_tls"), True)
        with httpx.Client(timeout=30, follow_redirects=True, headers=headers, verify=verify_tls) as client:
            for page_url in pages:
                response = client.get(page_url)
                response.raise_for_status()
                candidates: list[HtmlNode] = []
                for root in _roots_from_response(response.text, parse_json_html, json_html_fields):
                    for selector in selectors:
                        candidates.extend(root.select(str(selector)))

                for node in candidates[:source_limit]:
                    if node.tag == "tr" and not _direct_children(node, {"td"}):
                        continue
                    row = self._candidate_from_node(node, page_url, title_column, due_date_column, source_url_column, status_column, estimated_value_column)
                    raw_text = row["raw_text"]
                    if len(raw_text) < min_text_length:
                        continue
                    lower = raw_text.lower()
                    if any(pattern in lower for pattern in skip_patterns):
                        continue
                    if source_url_pattern and not re.search(str(source_url_pattern), row.get("source_url") or "", flags=re.IGNORECASE):
                        continue

                    detail_url = _format_template(str(detail_template), row) if detail_template else row.get("source_url")
                    detail_text = ""
                    detail_links: list[dict[str, str]] = []
                    if fetch_detail and detail_url and _is_fetchable_detail(detail_url, page_url):
                        detail_response = client.get(detail_url)
                        detail_response.raise_for_status()
                        detail_root = parse_html(detail_response.text)
                        detail_text = normalize_text(detail_root.text_content())
                        detail_links = _links(detail_root, detail_url)

                    search_text = f"{raw_text} {detail_text} {detail_url or ''}"
                    if require_keywords and not _text_matches_terms(search_text.lower(), keywords):
                        continue
                    if require_procurement_terms and not _text_matches_terms(search_text.lower(), procurement_terms):
                        continue

                    title = _format_template(params.get("title_template"), row) or row.get("title") or raw_text[:180]
                    title = normalize_text(title)[:260]
                    if not title or len(title) < 5:
                        continue
                    source_url = detail_url or row.get("source_url") or page_url
                    key = f"{source}:{source_url}:{title}"
                    if key in seen:
                        continue
                    seen.add(key)

                    due_date = _parse_date(row.get("due_date") or raw_text)
                    if due_date and due_date < due_after:
                        continue
                    description = normalize_text(
                        params.get("description_prefix") or f"Official public bid listing from {agency or source}:"
                    )
                    description = f"{description} {raw_text}"
                    if detail_text:
                        description = f"{description}\n\nDetail page text: {detail_text[:3000]}"
                    attachments = [*row["links"], *detail_links]
                    specs = extract_specs(f"{title}. {description}")
                    classification = classify_bid(title, description, specs)
                    opportunities.append(
                        {
                            "title": title,
                            "agency": agency,
                            "location": location,
                            "state": str(state).upper()[:2] if state else None,
                            "due_date": due_date,
                            "naics_code": row.get("naics_code"),
                            "description": description,
                            "source": source,
                            "source_type": source_type or infer_source_type(source, agency),
                            "source_url": source_url,
                            "bid_status": normalize_bid_status(row.get("bid_status") or params.get("bid_status") or "open", due_date),
                            "estimated_value": _parse_decimal(row.get("estimated_value") or raw_text),
                            "attachments": attachments[:12],
                            "extracted_specs": specs,
                            "project_type": classification["project_type"],
                            "confidence_score": classification["confidence_score"],
                            "classification_explanation": classification["explanation"],
                        }
                    )
                    if len(opportunities) >= limit:
                        return opportunities
        return opportunities

    def _candidate_from_node(
        self,
        node: HtmlNode,
        page_url: str,
        title_column: Any,
        due_date_column: Any,
        source_url_column: Any,
        status_column: Any,
        estimated_value_column: Any,
    ) -> dict[str, Any]:
        cells = _direct_children(node, {"td", "th"})
        values: dict[str, str] = {}
        for index, cell in enumerate(cells):
            values[f"col{index}"] = normalize_text(cell.text_content())
        links = _links(node, page_url)

        def column_value(column: Any) -> str | None:
            if column is None or column == "":
                return None
            try:
                index = int(column)
            except (TypeError, ValueError):
                return values.get(str(column))
            if index < 0 or index >= len(cells):
                return None
            return values.get(f"col{index}")

        source_url = None
        if source_url_column is not None:
            try:
                index = int(source_url_column)
            except (TypeError, ValueError):
                index = -1
            if 0 <= index < len(cells):
                cell_links = _links(cells[index], page_url)
                source_url = cell_links[0]["url"] if cell_links else None
        if not source_url and links:
            source_url = links[0]["url"]

        first_link_text = links[0]["name"] if links else None
        raw_text = normalize_text(node.text_content())
        title = column_value(title_column) or first_link_text
        if title and len(title) < 4:
            title = None

        values.update(
            {
                "title": title or raw_text[:180],
                "raw_text": raw_text,
                "source_url": source_url or "",
                "due_date": column_value(due_date_column) or "",
                "bid_status": column_value(status_column) or "",
                "estimated_value": column_value(estimated_value_column) or "",
            }
        )
        return {
            **values,
            "links": links,
            "source_url": source_url,
        }
