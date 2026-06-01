from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

import httpx

from app.services.classification import classify_bid
from app.services.extraction import extract_specs
from app.services.ingestion.base import IngestionAdapter
from app.services.value_assessment import infer_source_type, normalize_bid_status


@dataclass
class HtmlNode:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list["HtmlNode"] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)

    def text_content(self) -> str:
        parts = [*self.text_parts]
        for child in self.children:
            parts.append(child.text_content())
        return " ".join(part.strip() for part in parts if part.strip())

    def attr(self, name: str) -> str | None:
        return self.attrs.get(name)

    def descendants(self) -> list["HtmlNode"]:
        nodes: list[HtmlNode] = []
        for child in self.children:
            nodes.append(child)
            nodes.extend(child.descendants())
        return nodes

    def select(self, selector: str) -> list["HtmlNode"]:
        current = [self]
        for part in selector.split():
            matched: list[HtmlNode] = []
            for node in current:
                matched.extend(descendant for descendant in node.descendants() if _matches(descendant, part))
            current = matched
        return current


class TreeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = HtmlNode("document")
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = HtmlNode(tag.lower(), {key.lower(): value or "" for key, value in attrs})
        self.stack[-1].children.append(node)
        if tag.lower() not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == normalized:
                self.stack = self.stack[:index]
                return

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.stack[-1].text_parts.append(data)


def parse_html(html: str) -> HtmlNode:
    parser = TreeParser()
    parser.feed(html)
    return parser.root


def _matches(node: HtmlNode, selector: str) -> bool:
    tag = selector
    expected_id = None
    expected_classes: list[str] = []
    if "#" in tag:
        tag, expected_id = tag.split("#", 1)
    if "." in tag:
        pieces = tag.split(".")
        tag = pieces[0]
        expected_classes = [piece for piece in pieces[1:] if piece]
    if tag and node.tag != tag.lower():
        return False
    if expected_id and node.attrs.get("id") != expected_id:
        return False
    classes = set((node.attrs.get("class") or "").split())
    return all(class_name in classes for class_name in expected_classes)


def _selected_value(root: HtmlNode, selector: str | None) -> str | None:
    if not selector:
        return None
    attr_name = None
    if "@" in selector:
        selector, attr_name = selector.rsplit("@", 1)
    matches = root.select(selector.strip())
    if not matches:
        return None
    if attr_name:
        return matches[0].attr(attr_name.strip())
    return matches[0].text_content() or None


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    cleaned = str(value).lower().replace("$", "").replace(",", "").replace("estimated", "").replace("value", "").strip()
    multiplier = Decimal("1")
    if cleaned.endswith(("m", "mil", "million")):
        multiplier = Decimal("1000000")
        cleaned = cleaned.replace("million", "").replace("mil", "").removesuffix("m").strip()
    try:
        return Decimal(cleaned) * multiplier
    except Exception:
        return None


def _first_text(root: HtmlNode, selectors: list[str]) -> str | None:
    for selector in selectors:
        value = _selected_value(root, selector)
        if value:
            return value
    return None


class PublicHtmlScrapeAdapter(IngestionAdapter):
    name = "public_html_scrape"
    description = "Selector-based public HTML scraping adapter for bid listing and detail pages."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        url = params.get("url")
        record_selector = params.get("record_selector")
        if not url or not record_selector:
            raise ValueError("public_html_scrape requires params.url and params.record_selector")

        field_selectors = params.get("field_selectors") or {}
        detail_field_selectors = params.get("detail_field_selectors") or {}
        source = params.get("source") or "public_html_scrape"
        source_type = params.get("source_type") or "state_local"
        headers = {
            "User-Agent": params.get("user_agent") or "ElecBidSpecAI/0.1 public-bid-ingestion",
            **(params.get("headers") or {}),
        }
        limit = int(params.get("limit") or 25)
        detail_delay = float(params.get("detail_delay_seconds") or 0)

        with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
            listing_html = client.get(url).text
            listing_root = parse_html(listing_html)
            records = listing_root.select(record_selector)[:limit]
            opportunities = []
            for record in records:
                detail_url = _selected_value(record, field_selectors.get("source_url") or field_selectors.get("detail_url") or "a@href")
                absolute_detail_url = urljoin(url, detail_url) if detail_url else None
                detail_root = None
                if absolute_detail_url and detail_field_selectors:
                    if detail_delay > 0:
                        time.sleep(detail_delay)
                    detail_response = client.get(absolute_detail_url)
                    detail_response.raise_for_status()
                    detail_root = parse_html(detail_response.text)

                data = self._extract_record(record, detail_root, field_selectors, detail_field_selectors)
                title = data.get("title") or _first_text(record, ["h1", "h2", "h3", "a"])
                if not title:
                    continue
                description = data.get("description") or record.text_content()
                due_date = _parse_date(data.get("due_date"))
                agency = data.get("agency") or params.get("agency")
                specs = extract_specs(f"{title}. {description}")
                classification = classify_bid(title, description, specs)
                state = data.get("state") or params.get("state")
                opportunities.append(
                    {
                        "title": title,
                        "agency": agency,
                        "location": data.get("location") or params.get("location"),
                        "state": str(state)[:2].upper() if state else None,
                        "due_date": due_date,
                        "naics_code": data.get("naics_code"),
                        "description": description,
                        "source": source,
                        "source_type": data.get("source_type") or source_type or infer_source_type(source, agency),
                        "source_url": absolute_detail_url or url,
                        "bid_status": normalize_bid_status(data.get("bid_status"), due_date),
                        "estimated_value": _parse_decimal(data.get("estimated_value")),
                        "attachments": [],
                        "extracted_specs": specs,
                        "project_type": classification["project_type"],
                        "confidence_score": classification["confidence_score"],
                        "classification_explanation": classification["explanation"],
                    }
                )
        return opportunities

    def _extract_record(
        self,
        record: HtmlNode,
        detail_root: HtmlNode | None,
        field_selectors: dict[str, str],
        detail_field_selectors: dict[str, str],
    ) -> dict[str, str]:
        data = {}
        for field_name, selector in field_selectors.items():
            if field_name in {"source_url", "detail_url"}:
                continue
            value = _selected_value(record, selector)
            if value:
                data[field_name] = value
        if detail_root:
            for field_name, selector in detail_field_selectors.items():
                value = _selected_value(detail_root, selector)
                if value:
                    data[field_name] = value
        return data
