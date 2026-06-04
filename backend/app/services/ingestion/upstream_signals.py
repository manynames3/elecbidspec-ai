from __future__ import annotations

import csv
import html
import io
import re
import zipfile
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

import httpx

from app.services.classification import classify_bid
from app.services.extraction import extract_specs
from app.services.ingestion.base import IngestionAdapter


USER_AGENT = "ElecBidSpecAI/1.0 (+https://elecbidspec-ai.pages.dev)"

PJM_PAGE_URL = "https://www.pjm.com/planning/m/project-construction"
PJM_XML_URL = "https://www.pjm.com/pjmfiles/media/planning/projectConstruction-data/projectCostUpgrades.xml"
CAISO_PAGE_URL = "https://www.caiso.com/library/interconnection-queue-reports"
CAISO_CLUSTER_15_URL = "https://www.caiso.com/documents/cluster-15-interconnection-requests.xlsx"
ERCOT_RESOURCE_PAGE_URL = "https://www.ercot.com/gridinfo/resource"
ISO_NE_PAGE_URL = "https://www.iso-ne.com/system-planning/interconnection-service/interconnection-request-queue"
ISO_NE_PUBLIC_QUEUE_URL = "https://irtt.iso-ne.com/reports/external"
MISO_PAGE_URL = "https://www.misoenergy.org/planning/resource-utilization/generator-interconnection/"
MISO_ERAS_WORKBOOK_URL = "https://cdn.misoenergy.org/ERAS%20Interconnection%20Requests718482.xlsx?v=20250925100619"
NYISO_PAGE_URL = "https://www.nyiso.com/interconnections"
NYISO_QUEUE_WORKBOOK_URL = (
    "https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue-04302026.xlsx/"
    "ff0e2005-e8d3-e75d-3e81-fa7027a52685?t=1778697331320"
)
TEXAS_PUC_DOCKETS_URL = (
    "https://interchange.puc.texas.gov/search/dockets/"
    "?UtilityType=E&ItemMatch=Equal&DocumentType=ALL&SortBy=ControlNumber&SortOrder=Descending"
)
SPP_GI_PAGE_URL = "https://spp.org/engineering/generator-interconnection/"
SPP_GI_ACTIVE_URL = "https://opsportal.spp.org/Studies/GIActive"
SPP_GI_ACTIVE_CSV_URL = "https://opsportal.spp.org/Studies/GenerateActiveCSV"
VIRGINIA_SCC_TRANSMISSION_PAGE_URL = "https://www.scc.virginia.gov/consumers/public-utility/electricity-faqs/transmission-line-projects/"
GEORGIA_PSC_HOME_URL = "https://psc.ga.gov/?lang=us"
GEORGIA_PSC_DATA_CENTER_FACT_SHEET_URL = "https://psc.ga.gov/site/downloads/datacenterfactsheet.pdf"
LOUDOUN_LAND_APPLICATIONS_PAGE_URL = "https://www.loudoun.gov/3362/Land-Application-Information-Comments"
LOUDOUN_LAND_APPLICATIONS_LAYER_URL = "https://logis.loudoun.gov/gis/rest/services/Projects/LOLA_DATA/MapServer/0"
TLS_FALLBACK_HOSTS = {"interchange.puc.texas.gov"}

DEFAULT_UPSTREAM_KEYWORDS = [
    "ai infrastructure",
    "artificial intelligence",
    "battery",
    "ccn",
    "certificate of convenience",
    "conduit",
    "data center",
    "datacenter",
    "electric delivery",
    "generation interconnection",
    "grid",
    "high voltage",
    "hyperscale",
    "interconnection",
    "large load",
    "medium voltage",
    "power",
    "substation",
    "switchyard",
    "transmission",
    "utility",
]

IOU_TERMS = [
    "aep",
    "american electric power",
    "bge",
    "centerpoint",
    "dominion",
    "duke",
    "duquesne",
    "edison",
    "oncor",
    "peco",
    "penelec",
    "pge",
    "pg&e",
    "pseg",
    "sdge",
    "sce",
    "southwestern electric power",
    "alliant",
    "ameren",
    "central hudson",
    "commonwealth edison",
    "con edison",
    "consolidated edison",
    "consumers energy",
    "dte",
    "entergy",
    "eversource",
    "evergy",
    "firstenergy",
    "georgia power",
    "itc",
    "midamerican",
    "minnesota power",
    "national grid",
    "nyseg",
    "orange and rockland",
    "otter tail",
    "rge",
    "xcel",
]

VIRGINIA_SCC_UTILITY_NAMES = [
    "Dominion Energy Virginia",
    "Appalachian Power Company",
    "Delmarva Power & Light",
    "Old Dominion Electric Cooperative",
    "Central Virginia Electric Cooperative",
    "Kentucky Utilities Company",
    "NextEra Energy Transmission Virginia",
]


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def _keyword_terms(params: dict[str, Any]) -> list[str]:
    keywords = params.get("keywords") or DEFAULT_UPSTREAM_KEYWORDS
    if isinstance(keywords, str):
        keywords = [part.strip() for part in keywords.split(",")]
    return [str(keyword).lower() for keyword in keywords if str(keyword).strip()]


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    lower = text.lower()
    return any(keyword in lower for keyword in keywords)


def _keyword_score(text: str) -> int:
    lower = text.lower()
    score = 0
    for term in ["data center", "datacenter", "hyperscale", "ai infrastructure"]:
        if term in lower:
            score += 8
    for term in ["substation", "transmission", "large load", "interconnection", "765 kv", "500 kv", "345 kv", "230 kv", "138 kv", "115 kv"]:
        if term in lower:
            score += 5
    for term in ["industrial park", "power generation", "battery", "storage", "solar", "wind", "offshore wind", "combined cycle", "load"]:
        if term in lower:
            score += 2
    return score


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).replace("$", "").replace(",", "").strip())
    except Exception:
        return None


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
        if number > 10_000_000_000:
            return datetime.fromtimestamp(number / 1000, tz=timezone.utc).date()
        if 20_000 <= number <= 80_000:
            return (datetime(1899, 12, 30) + timedelta(days=number)).date()
    except ValueError:
        pass
    for pattern in ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%b %d, %Y", "%B %d, %Y"]:
        try:
            return datetime.strptime(text[:24], pattern).date()
        except ValueError:
            continue
    return None


def _owner_type(text: str, default: str = "public_power_or_utility") -> str:
    lower = text.lower()
    if any(term in lower for term in IOU_TERMS):
        return "investor_owned_utility"
    return default


def _evidence(name: str, url: str, source: str, excerpt: str | None = None) -> dict[str, str]:
    evidence = {"name": name, "url": url, "source": source, "type": "evidence"}
    if excerpt:
        evidence["excerpt"] = excerpt[:500]
    return evidence


def _xml_tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _xml_items(content: bytes, item_tag: str) -> list[ET.Element]:
    text = content.decode("utf-8-sig", errors="replace")
    try:
        root = ET.fromstring(text)
        direct_items = [item for item in list(root) if _xml_tag_name(item.tag) == item_tag]
        nested_items = [item for item in root.findall(f".//{item_tag}") if _xml_tag_name(item.tag) == item_tag]
        return direct_items or nested_items
    except ET.ParseError:
        items: list[ET.Element] = []
        pattern = re.compile(rf"<{re.escape(item_tag)}\b[\s\S]*?</{re.escape(item_tag)}>", flags=re.IGNORECASE)
        for match in pattern.finditer(text):
            try:
                items.append(ET.fromstring(match.group(0)))
            except ET.ParseError:
                continue
        if items:
            return items
        raise


def _get_with_official_tls_fallback(url: str, *, timeout: int = 45) -> httpx.Response:
    headers = {"User-Agent": USER_AGENT}
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
            return client.get(url)
    except httpx.TransportError as exc:
        host = urlparse(url).hostname or ""
        if host not in TLS_FALLBACK_HOSTS or "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers, verify=False) as client:
            return client.get(url)


def _record(
    *,
    title: str,
    agency: str,
    description: str,
    source: str,
    source_type: str,
    source_url: str,
    signal_type: str,
    location: str | None = None,
    state: str | None = None,
    due_date: date | None = None,
    forecast_rfp_date: date | None = None,
    estimated_value: Decimal | None = None,
    owner_type: str = "public_agency",
    bid_status: str = "planning",
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence_links = []
    explicit_evidence_excerpts = []
    for item in attachments or []:
        normalized = dict(item)
        if normalized.get("excerpt"):
            explicit_evidence_excerpts.append(_clean(normalized.get("excerpt")))
        if not normalized.get("excerpt"):
            normalized["excerpt"] = description[:500]
        normalized["quality"] = "excerpted" if normalized.get("excerpt") else "link_only"
        evidence_links.append(normalized)
    specs = extract_specs(f"{title}. {description}")
    specs["evidence_links"] = evidence_links
    evidence_excerpts = [_clean(item.get("excerpt")) for item in evidence_links if isinstance(item, dict) and item.get("excerpt")]
    if evidence_excerpts:
        specs["evidence_excerpts"] = list(dict.fromkeys([*explicit_evidence_excerpts, *evidence_excerpts]))[:3]
    specs["evidence_quality"] = "strong" if len(evidence_excerpts) >= 1 and len(evidence_links) >= 2 else "moderate" if evidence_links else "thin"
    classification = classify_bid(title, description, specs)
    return {
        "title": title[:280],
        "agency": agency,
        "location": location,
        "state": state[:2].upper() if state else None,
        "due_date": due_date,
        "naics_code": None,
        "description": description,
        "source": source,
        "source_type": source_type,
        "source_url": source_url,
        "bid_status": bid_status,
        "project_stage": "early_signal",
        "signal_type": signal_type,
        "owner_type": owner_type,
        "forecast_rfp_date": forecast_rfp_date,
        "estimated_value": estimated_value,
        "attachments": evidence_links,
        "extracted_specs": specs,
        "project_type": classification["project_type"],
        "confidence_score": classification["confidence_score"],
        "classification_explanation": classification["explanation"],
    }


def _cell_index(ref: str) -> int:
    match = re.match(r"[A-Z]+", ref or "A1")
    letters = match.group(0) if match else "A"
    index = 0
    for letter in letters:
        index = index * 26 + ord(letter) - 64
    return index - 1


def _xlsx_rows(content: bytes) -> list[list[str]]:
    rows: list[list[str]] = []
    ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(content)) as workbook:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
            for item in root.findall("a:si", ns):
                shared_strings.append("".join(text.text or "" for text in item.findall(".//a:t", ns)))

        sheet_names = sorted(name for name in workbook.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", name))
        for sheet_name in sheet_names:
            root = ET.fromstring(workbook.read(sheet_name))
            for row in root.findall(".//a:sheetData/a:row", ns):
                values: dict[int, str] = {}
                for cell in row.findall("a:c", ns):
                    ref = cell.attrib.get("r", "A1")
                    value_node = cell.find("a:v", ns)
                    value = value_node.text if value_node is not None else ""
                    if cell.attrib.get("t") == "s" and value:
                        value = shared_strings[int(value)]
                    elif cell.attrib.get("t") == "inlineStr":
                        value = "".join(text.text or "" for text in cell.findall(".//a:t", ns))
                    values[_cell_index(ref)] = _clean(value)
                if values and any(value for value in values.values()):
                    rows.append([values.get(index, "") for index in range(max(values) + 1)])
    return rows


def _row_dicts(rows: list[list[str]], header_markers: list[tuple[str, ...]] | None = None) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    headers: list[str] = []
    markers = header_markers or [("project name",), ("inr", "queue number")]
    for row in rows:
        lowered = [_clean(cell).lower() for cell in row]
        if all(any(marker in lowered for marker in marker_group) for marker_group in markers):
            headers = [_clean(cell) for cell in row]
            continue
        if not headers or lowered[0] == "month/year":
            continue
        record = {headers[index]: row[index] for index in range(min(len(headers), len(row))) if headers[index]}
        if any(record.values()):
            records.append(record)
    return records


def _table_dicts(rows: list[tuple[list[str], list[str]]], header_markers: list[tuple[str, ...]]) -> list[tuple[dict[str, str], list[str]]]:
    records: list[tuple[dict[str, str], list[str]]] = []
    headers: list[str] = []
    for cells, links in rows:
        lowered = [_clean(cell).lower() for cell in cells]
        if all(any(marker in lowered for marker in marker_group) for marker_group in header_markers):
            headers = [_clean(cell) for cell in cells]
            continue
        if not headers or len(cells) < 2:
            continue
        record: dict[str, str] = {}
        for index, header in enumerate(headers[: len(cells)]):
            key = header or f"Column {index + 1}"
            if key in record:
                key = f"{key} {index + 1}"
            record[key] = cells[index]
        if any(record.values()):
            records.append((record, links))
    return records


def _first_value(data: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = _clean(data.get(key))
        if value:
            return value
    return ""


def _decode_document_text(content: bytes) -> str:
    if content.startswith(b"%PDF"):
        try:
            from app.services.extraction import parse_pdf

            return _clean(parse_pdf(content))
        except Exception:
            return ""
    return _clean(content.decode("utf-8", errors="ignore"))


def _latest_known_agency(html_text: str, match_start: int, candidates: list[str]) -> str:
    window = html_text[max(0, match_start - 12000) : match_start]
    best_name = ""
    best_index = -1
    lower_window = window.lower()
    for candidate in candidates:
        index = lower_window.rfind(candidate.lower())
        if index > best_index:
            best_index = index
            best_name = candidate
    return best_name


def _forecast_before(value: Any, days: int = 365) -> date | None:
    parsed = _parse_date(value)
    if not parsed:
        return None
    if days == 365:
        try:
            return parsed.replace(year=parsed.year - 1)
        except ValueError:
            return parsed.replace(year=parsed.year - 1, day=28)
    return parsed - timedelta(days=days)


class _TableRowParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.rows: list[tuple[list[str], list[str]]] = []
        self._in_row = False
        self._in_cell = False
        self._cell_text = ""
        self._cells: list[str] = []
        self._links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "tr":
            self._in_row = True
            self._cells = []
            self._links = []
        elif self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._cell_text = ""
        elif self._in_row and tag == "a" and attrs_dict.get("href"):
            self._links.append(urljoin(self.base_url, str(attrs_dict["href"])))

    def handle_endtag(self, tag: str) -> None:
        if self._in_row and tag in {"td", "th"}:
            self._cells.append(_clean(self._cell_text))
            self._in_cell = False
        elif self._in_row and tag == "tr":
            if self._cells:
                self.rows.append((self._cells, self._links))
            self._in_row = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_text += f" {data}"


class PjmProjectConstructionAdapter(IngestionAdapter):
    name = "pjm_project_construction"
    description = "Official PJM project construction XML export for transmission upgrades and cost allocation signals."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        xml_url = params.get("url") or PJM_XML_URL
        page_url = params.get("page_url") or PJM_PAGE_URL
        limit = int(params.get("limit") or 25)
        source_limit = int(params.get("source_limit") or 5000)
        min_cost_millions = Decimal(str(params.get("min_cost_millions") or 5))
        active_statuses = {str(item).lower() for item in (params.get("statuses") or ["active", "ep", "uc", "pl", "on hold"])}
        keywords = _keyword_terms(params)

        with httpx.Client(timeout=45, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(xml_url)
            response.raise_for_status()
            upgrades = _xml_items(response.content, "Upgrade")

        candidates: list[tuple[date, dict[str, Any]]] = []
        for upgrade in upgrades[:source_limit]:
            data = {_xml_tag_name(child.tag): _clean(child.text) for child in upgrade}
            upgrade_id = data.get("UpgradeId")
            description = data.get("Description") or ""
            if not upgrade_id or not description:
                continue
            status = data.get("Status", "")
            if status.lower() not in active_statuses:
                continue
            cost_millions = _parse_decimal(data.get("CostEstimate"))
            if cost_millions is not None and cost_millions < min_cost_millions:
                continue

            text = " ".join(str(value) for value in data.values())
            if not _matches_keywords(text, keywords):
                continue

            estimated_value = cost_millions * Decimal("1000000") if cost_millions is not None else None
            state = data.get("State") or None
            location = ", ".join(part for part in [data.get("Location"), state, "PJM"] if part)
            voltage = data.get("Voltage")
            transmission_owner = data.get("TransmissionOwner") or "PJM transmission owner"
            title = f"PJM transmission upgrade {upgrade_id}: {description}"
            body = [
                f"Official PJM project construction signal for {description}.",
                f"Project type: {data.get('ProjectType') or 'Not stated'}.",
                f"Transmission owner: {transmission_owner}.",
                f"Voltage: {voltage or 'Not stated'} kV.",
                f"Equipment: {data.get('Equipment') or 'Not stated'}.",
                f"Driver: {data.get('Driver') or 'Not stated'}.",
                f"Status: {status}.",
                f"Estimated upgrade cost: ${estimated_value:,.0f}." if estimated_value is not None else "Estimated upgrade cost: Not stated.",
                f"Projected in-service date: {data.get('ProjectedInServiceDate') or data.get('RevisedInServiceDate') or 'Not stated'}.",
                f"Last updated: {data.get('LastUpdated') or 'Not stated'}.",
            ]
            record = _record(
                title=title,
                agency=transmission_owner,
                location=location,
                state=state,
                description="\n".join(body),
                source="pjm_project_construction",
                source_type="rto_iso",
                source_url=f"{page_url}#upgrade-{upgrade_id}",
                signal_type="rto_transmission_plan",
                owner_type=_owner_type(transmission_owner),
                estimated_value=estimated_value,
                attachments=[
                    _evidence("PJM Project Construction page", page_url, "pjm_project_construction"),
                    _evidence("PJM Project Construction XML export", xml_url, "pjm_project_construction", " ".join(body[:6])),
                ],
            )
            candidates.append((_parse_date(data.get("LastUpdated")) or date.min, record))

        candidates.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in candidates[:limit]]


class CaisoInterconnectionQueueAdapter(IngestionAdapter):
    name = "caiso_interconnection_queue"
    description = "Official CAISO interconnection queue workbook for large generation, storage, and transmission interconnection signals."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        workbook_url = params.get("url") or CAISO_CLUSTER_15_URL
        page_url = params.get("page_url") or CAISO_PAGE_URL
        limit = int(params.get("limit") or 25)
        min_mw = Decimal(str(params.get("min_mw") or 100))
        min_voltage = Decimal(str(params.get("min_voltage_kv") or 70))
        keywords = _keyword_terms(params)

        with httpx.Client(timeout=45, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(workbook_url)
            response.raise_for_status()
            rows = _xlsx_rows(response.content)

        opportunities: list[dict[str, Any]] = []
        for data in _row_dicts(rows):
            queue_number = data.get("Queue Number")
            project_name = data.get("Project Name")
            if not queue_number or not project_name:
                continue
            net_mw = _parse_decimal(data.get("NET MW POI") or data.get("NET MW 1")) or Decimal("0")
            voltage = _parse_decimal(data.get("Voltage kV")) or Decimal("0")
            if net_mw < min_mw or voltage < min_voltage:
                continue
            text = " ".join(str(value) for value in data.values())
            if not _matches_keywords(text, keywords):
                continue

            state = data.get("Project State") or None
            county = data.get("PROJECT COUNTY") or None
            pto = data.get("PTO") or "CAISO participating transmission owner"
            fuels = ", ".join(
                item
                for item in [data.get("Generation/Fuel 1"), data.get("Generation/Fuel 2"), data.get("Generation/Fuel 3")]
                if item and item.upper() != "N/A"
            )
            description = "\n".join(
                [
                    f"Official CAISO interconnection queue signal for {project_name}.",
                    f"Point of interconnection: {data.get('POI') or 'Not stated'}.",
                    f"Participating transmission owner: {pto}.",
                    f"Study area: {data.get('Study Area') or 'Not stated'}.",
                    f"Resource mix: {fuels or 'Not stated'}.",
                    f"Requested capacity at POI: {net_mw} MW.",
                    f"Voltage: {voltage} kV.",
                    f"Requested commercial operation date: {_parse_date(data.get('Requested COD')) or 'Not stated'}.",
                    f"Service type: {data.get('Service Type') or 'Not stated'}.",
                ]
            )
            opportunities.append(
                _record(
                    title=f"CAISO interconnection request {queue_number}: {project_name} ({net_mw} MW at {voltage} kV)",
                    agency=pto,
                    location=", ".join(part for part in [county, state] if part) or "CAISO",
                    state=state,
                    description=description,
                    source="caiso_interconnection_queue",
                    source_type="rto_iso",
                    source_url=f"{page_url}#queue-{queue_number}",
                    signal_type="interconnection_queue",
                    owner_type=_owner_type(pto, default="private_developer"),
                    attachments=[
                        _evidence("CAISO Interconnection Queue Reports page", page_url, "caiso_interconnection_queue"),
                        _evidence("CAISO Cluster 15 interconnection requests workbook", workbook_url, "caiso_interconnection_queue"),
                    ],
                )
            )
            if len(opportunities) >= limit:
                break
        return opportunities


class ErcotCapacityChangesAdapter(IngestionAdapter):
    name = "ercot_capacity_changes"
    description = "Official ERCOT planned capacity workbook for interconnection and data-center-adjacent grid signals."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        page_url = params.get("page_url") or ERCOT_RESOURCE_PAGE_URL
        workbook_url = params.get("url") or self._latest_workbook_url(page_url)
        limit = int(params.get("limit") or 25)
        min_mw = Decimal(str(params.get("min_mw") or 100))
        keywords = _keyword_terms(params)

        with httpx.Client(timeout=45, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(workbook_url)
            response.raise_for_status()
            rows = _xlsx_rows(response.content)

        candidates: list[tuple[int, date, dict[str, Any]]] = []
        for data in _row_dicts(rows):
            inr = data.get("INR")
            project_name = data.get("Project Name")
            if not inr or not project_name:
                continue
            capacity = _parse_decimal(data.get("Capacity (MW)")) or Decimal("0")
            if capacity < min_mw:
                continue
            text = " ".join(str(value) for value in data.values())
            if not _matches_keywords(text, keywords):
                continue
            projected_cod = _parse_date(data.get("Projected COD"))
            ia_signed = _parse_date(data.get("IA Signed"))
            county = data.get("County") or None
            fuel = data.get("Fuel") or "resource"
            technology = data.get("Technology") or "not stated"
            data_center_priority = 1 if "data center" in project_name.lower() or "datacenter" in project_name.lower() else 0
            description = "\n".join(
                [
                    f"Official ERCOT planned capacity/interconnection signal for {project_name}.",
                    f"INR: {inr}.",
                    f"County: {county or 'Not stated'}, Texas.",
                    f"Fuel / technology: {fuel} / {technology}.",
                    f"Planned capacity: {capacity} MW.",
                    f"Projected commercial operation date: {projected_cod or 'Not stated'}.",
                    f"Interconnection agreement signed: {ia_signed or 'Not stated'}.",
                    "Starting in 2026 ERCOT's public resource adequacy page also references transmission interconnection cost reporting.",
                ]
            )
            candidates.append(
                (
                    data_center_priority,
                    projected_cod or date.min,
                    _record(
                        title=f"ERCOT planned interconnection {inr}: {project_name} ({capacity} MW {fuel})",
                        agency="ERCOT",
                        location=", ".join(part for part in [county, "TX"] if part),
                        state="TX",
                        description=description,
                        source="ercot_capacity_changes",
                        source_type="rto_iso",
                        source_url=f"{page_url}#inr-{inr}",
                        signal_type="interconnection_queue",
                        owner_type="private_developer",
                        attachments=[
                            _evidence("ERCOT Resource Adequacy page", page_url, "ercot_capacity_changes"),
                            _evidence("ERCOT planned capacity workbook", workbook_url, "ercot_capacity_changes"),
                        ],
                    ),
                )
            )

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [record for _, _, record in candidates[:limit]]

    def _latest_workbook_url(self, page_url: str) -> str:
        with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(page_url)
            response.raise_for_status()
        links = re.findall(r'href=["\']([^"\']+PlannedMonthly\.xlsx)["\']', response.text, flags=re.IGNORECASE)
        if not links:
            raise ValueError("ERCOT resource page did not expose a planned monthly capacity workbook")
        return urljoin(str(response.url), links[0])


class IsoNeInterconnectionQueueAdapter(IngestionAdapter):
    name = "iso_ne_interconnection_queue"
    description = "Official ISO New England public interconnection queue HTML for generation, storage, and ETU signals."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        page_url = params.get("page_url") or ISO_NE_PAGE_URL
        queue_url = params.get("url") or ISO_NE_PUBLIC_QUEUE_URL
        limit = int(params.get("limit") or 25)
        min_mw = Decimal(str(params.get("min_mw") or 75))
        keywords = _keyword_terms(params)

        with httpx.Client(timeout=45, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(queue_url)
            response.raise_for_status()

        parser = _TableRowParser(str(response.url))
        parser.feed(response.text)

        candidates: list[tuple[int, date, dict[str, Any]]] = []
        for data, _links in _table_dicts(parser.rows, [("qp",), ("alternative name",), ("net mw",)]):
            queue_position = _first_value(data, "QP")
            project_name = _first_value(data, "Alternative Name")
            status = _first_value(data, "Status")
            if not queue_position or not project_name or status.upper() == "W":
                continue

            net_mw = _parse_decimal(_first_value(data, "Net MW")) or Decimal("0")
            summer_mw = _parse_decimal(_first_value(data, "Summer MW")) or Decimal("0")
            winter_mw = _parse_decimal(_first_value(data, "Winter MW")) or Decimal("0")
            max_mw = max(net_mw, summer_mw, winter_mw)
            if max_mw < min_mw:
                continue

            text = " ".join(str(value) for value in data.values())
            if not _matches_keywords(text, keywords):
                continue

            state = _first_value(data, "ST") or None
            county = _first_value(data, "County") or None
            fuel_type = _first_value(data, "Fuel Type") or _first_value(data, "Unit") or "not stated"
            poi = _first_value(data, "POI")
            transmission_owner = _first_value(data, "TO Report") or "ISO-NE transmission owner"
            operation_date = _parse_date(_first_value(data, "Op Date"))
            sync_date = _parse_date(_first_value(data, "Sync Date"))
            updated = _parse_date(_first_value(data, "Updated"))
            project_status = _first_value(data, "Project Status")
            excerpt = (
                f"ISO-NE public queue row QP {queue_position}: {project_name}; {max_mw} MW {fuel_type}; "
                f"POI {poi or 'not stated'}; status {status or project_status or 'not stated'}."
            )
            description = "\n".join(
                [
                    f"Official ISO New England public interconnection queue signal for {project_name}.",
                    f"Queue position: {queue_position}.",
                    f"Type / fuel: {_first_value(data, 'Type') or 'Not stated'} / {fuel_type}.",
                    f"Net / summer / winter MW: {net_mw} / {summer_mw} / {winter_mw}.",
                    f"County / state: {county or 'Not stated'}, {state or 'Not stated'}.",
                    f"Point of interconnection: {poi or 'Not stated'}.",
                    f"Transmission owner report: {transmission_owner}.",
                    f"Service: {_first_value(data, 'Serv') or 'Not stated'}.",
                    f"Project status: {project_status or 'Not stated'}; queue status: {status or 'Not stated'}.",
                    f"Expected operation date: {operation_date or 'Not stated'}.",
                    f"Expected sync date: {sync_date or 'Not stated'}.",
                    f"Last updated: {updated or 'Not stated'}.",
                ]
            )
            candidates.append(
                (
                    _keyword_score(text),
                    updated or operation_date or sync_date or date.min,
                    _record(
                        title=f"ISO-NE interconnection QP {queue_position}: {project_name} ({max_mw} MW {fuel_type})",
                        agency=transmission_owner,
                        location=", ".join(part for part in [county, state, "ISO-NE"] if part),
                        state=state,
                        description=description,
                        source="iso_ne_interconnection_queue",
                        source_type="rto_iso",
                        source_url=f"{queue_url}#qp-{queue_position}",
                        signal_type="interconnection_queue",
                        owner_type=_owner_type(transmission_owner, default="private_developer"),
                        forecast_rfp_date=_forecast_before(operation_date or sync_date),
                        attachments=[
                            _evidence("ISO-NE Interconnection Request Queue page", page_url, "iso_ne_interconnection_queue"),
                            _evidence("ISO-NE public queue IRTT table", queue_url, "iso_ne_interconnection_queue", excerpt),
                        ],
                    ),
                )
            )

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [record for _, _, record in candidates[:limit]]


class SppGiActiveRequestsAdapter(IngestionAdapter):
    name = "spp_gi_active_requests"
    description = "Official SPP GI Active Requests CSV for generation interconnection queue signals."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        page_url = params.get("page_url") or SPP_GI_PAGE_URL
        active_url = params.get("active_url") or SPP_GI_ACTIVE_URL
        csv_url = params.get("url") or SPP_GI_ACTIVE_CSV_URL
        limit = int(params.get("limit") or 25)
        min_mw = Decimal(str(params.get("min_mw") or 75))
        keywords = _keyword_terms(params)

        with httpx.Client(timeout=45, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(csv_url)
            response.raise_for_status()

        rows = list(csv.reader(io.StringIO(response.text)))
        if len(rows) < 3:
            return []
        last_updated = _parse_date(rows[0][1]) if len(rows[0]) > 1 else None
        headers = [_clean(header) for header in rows[1]]

        candidates: list[tuple[int, date, dict[str, Any]]] = []
        for row in rows[2:]:
            data = {headers[index]: _clean(row[index]) for index in range(min(len(headers), len(row))) if headers[index]}
            gi_number = _first_value(data, "Generation Interconnection Number")
            if not gi_number or _first_value(data, "Date Withdrawn"):
                continue
            capacity = _parse_decimal(_first_value(data, "Capacity", "MAX Summer MW", "Nameplate Capacity")) or Decimal("0")
            summer_mw = _parse_decimal(_first_value(data, "MAX Summer MW")) or Decimal("0")
            winter_mw = _parse_decimal(_first_value(data, "MAX Winter MW")) or Decimal("0")
            max_mw = max(capacity, summer_mw, winter_mw)
            if max_mw < min_mw:
                continue

            text = " ".join(str(value) for value in data.values())
            if not _matches_keywords(text, keywords):
                continue

            state = _first_value(data, "State") or None
            county = _first_value(data, "Nearest Town or County") or None
            owner = _first_value(data, "TO at POI") or "SPP transmission owner"
            facility = _first_value(data, "Substation or Line")
            fuel_type = _first_value(data, "Fuel Type", "Generation Type") or "not stated"
            in_service = _parse_date(_first_value(data, "In-Service Date"))
            cod = _parse_date(_first_value(data, "Commercial Operation Date"))
            status = _first_value(data, "Status")
            excerpt = (
                f"SPP active GI row {gi_number}: {max_mw} MW {fuel_type}; {facility or 'POI not stated'}; "
                f"{county or 'county not stated'}, {state or 'state not stated'}; status {status or 'not stated'}."
            )
            description = "\n".join(
                [
                    f"Official SPP GI Active Requests signal for {gi_number}.",
                    f"Current cluster: {_first_value(data, 'Current Cluster') or 'Not stated'}.",
                    f"Transmission owner at POI: {owner}.",
                    f"Substation or line: {facility or 'Not stated'}.",
                    f"County / state: {county or 'Not stated'}, {state or 'Not stated'}.",
                    f"Generation / fuel type: {_first_value(data, 'Generation Type') or 'Not stated'} / {fuel_type}.",
                    f"Capacity / summer / winter MW: {capacity} / {summer_mw} / {winter_mw}.",
                    f"Service type: {_first_value(data, 'Service Type') or 'Not stated'}.",
                    f"Requested maximum injection capability: {_first_value(data, 'Requested Maximum Injection Capability (MW)') or 'Not stated'} MW.",
                    f"In-service date: {in_service or 'Not stated'}.",
                    f"Commercial operation date: {cod or 'Not stated'}.",
                    f"Request received: {_parse_date(_first_value(data, 'Request Received')) or 'Not stated'}.",
                    f"Status: {status or 'Not stated'}.",
                    f"Queue last updated: {last_updated or 'Not stated'}.",
                ]
            )
            candidates.append(
                (
                    _keyword_score(text),
                    in_service or cod or last_updated or date.min,
                    _record(
                        title=f"SPP active GI request {gi_number}: {facility or fuel_type} ({max_mw} MW)",
                        agency=owner,
                        location=", ".join(part for part in [county, state, "SPP"] if part),
                        state=state,
                        description=description,
                        source="spp_gi_active_requests",
                        source_type="rto_iso",
                        source_url=f"{active_url}#gi-{gi_number}",
                        signal_type="interconnection_queue",
                        owner_type=_owner_type(owner, default="private_developer"),
                        forecast_rfp_date=_forecast_before(in_service or cod),
                        attachments=[
                            _evidence("SPP Generator Interconnection page", page_url, "spp_gi_active_requests"),
                            _evidence("SPP GI Active Requests CSV", csv_url, "spp_gi_active_requests", excerpt),
                        ],
                    ),
                )
            )

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [record for _, _, record in candidates[:limit]]


class MisoErasInterconnectionAdapter(IngestionAdapter):
    name = "miso_eras_interconnection"
    description = "Official MISO ERAS interconnection workbook for early generation, storage, and transmission-owner signals."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        page_url = params.get("page_url") or MISO_PAGE_URL
        workbook_url = params.get("url") or self._latest_workbook_url(page_url)
        limit = int(params.get("limit") or 25)
        min_mw = Decimal(str(params.get("min_mw") or 75))
        excluded_statuses = [str(item).lower() for item in (params.get("exclude_statuses") or ["withdrawn", "terminated", "cancelled", "canceled"])]
        keywords = _keyword_terms(params)

        with httpx.Client(timeout=45, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(workbook_url)
            response.raise_for_status()
            rows = _xlsx_rows(response.content)

        candidates: list[tuple[int, date, dict[str, Any]]] = []
        for data in _row_dicts(rows, [("project number",), ("interconnection customer",), ("request status",)]):
            project_number = _first_value(data, "Project Number", "Project Number ")
            customer = _first_value(data, "Interconnection Customer")
            status = _first_value(data, "Request Status")
            if not project_number or not customer:
                continue
            if any(status.lower().startswith(excluded) for excluded in excluded_statuses):
                continue
            if _first_value(data, "Date Withdrawn"):
                continue

            summer_mw = _parse_decimal(_first_value(data, "Max Summer MW")) or Decimal("0")
            winter_mw = _parse_decimal(_first_value(data, "Max Winter MW")) or Decimal("0")
            max_mw = max(summer_mw, winter_mw)
            if max_mw < min_mw:
                continue

            text = " ".join(str(value) for value in data.values())
            if not _matches_keywords(text, keywords):
                continue

            state = _first_value(data, "State") or None
            county = _first_value(data, "County") or None
            transmission_owner = _first_value(data, "Transmission Owner") or "MISO transmission owner"
            facility = _first_value(data, "Generating Facility") or customer
            fuel_type = _first_value(data, "Fuel Type") or "not stated"
            poi = _first_value(data, "POI Name")
            in_service = _parse_date(_first_value(data, "Application In Service Date", "Negotiated In Service Date"))
            score_text = f"{facility} {customer} {transmission_owner} {fuel_type} {poi} {state} {county}"
            description = "\n".join(
                [
                    f"Official MISO ERAS interconnection signal for {facility}.",
                    f"Project number: {project_number}.",
                    f"Interconnection customer: {customer}.",
                    f"Transmission owner: {transmission_owner}.",
                    f"Point of interconnection: {poi or 'Not stated'}.",
                    f"County / state: {county or 'Not stated'}, {state or 'Not stated'}.",
                    f"Fuel / facility type: {fuel_type}.",
                    f"Service type: {_first_value(data, 'Service Type') or 'Not stated'}.",
                    f"Requested max summer capacity: {summer_mw} MW.",
                    f"Requested max winter capacity: {winter_mw} MW.",
                    f"Study cycle: {_first_value(data, 'Study Cycle') or 'Not stated'}.",
                    f"Request status: {status or 'Not stated'}.",
                    f"Order submitted: {_parse_date(_first_value(data, 'Order Submitted')) or 'Not stated'}.",
                    f"Forecast in-service date: {in_service or 'Not stated'}.",
                ]
            )
            candidates.append(
                (
                    _keyword_score(score_text),
                    in_service or date.min,
                    _record(
                        title=f"MISO ERAS interconnection {project_number}: {facility} ({max_mw} MW {fuel_type})",
                        agency=transmission_owner,
                        location=", ".join(part for part in [county, state, "MISO"] if part),
                        state=state,
                        description=description,
                        source="miso_eras_interconnection",
                        source_type="rto_iso",
                        source_url=f"{page_url}#project-{project_number}",
                        signal_type="interconnection_queue",
                        owner_type=_owner_type(f"{transmission_owner} {customer}", default="private_developer"),
                        forecast_rfp_date=_forecast_before(in_service),
                        attachments=[
                            _evidence("MISO Generator Interconnection page", page_url, "miso_eras_interconnection"),
                            _evidence("MISO ERAS interconnection requests workbook", workbook_url, "miso_eras_interconnection"),
                        ],
                    ),
                )
            )

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [record for _, _, record in candidates[:limit]]

    def _latest_workbook_url(self, page_url: str) -> str:
        with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(page_url)
            response.raise_for_status()
        links = re.findall(r'href=["\']([^"\']+\.xlsx[^"\']*)["\']', response.text, flags=re.IGNORECASE)
        for link in links:
            decoded = html.unescape(link)
            if "ERAS%20Interconnection%20Requests" in decoded or "ERAS Interconnection Requests" in decoded:
                return urljoin(str(response.url), decoded)
        return MISO_ERAS_WORKBOOK_URL


class NyisoInterconnectionQueueAdapter(IngestionAdapter):
    name = "nyiso_interconnection_queue"
    description = "Official NYISO interconnection queue workbook for load, storage, generation, and transmission-owner signals."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        page_url = params.get("page_url") or NYISO_PAGE_URL
        workbook_url = params.get("url") or self._latest_workbook_url(page_url)
        limit = int(params.get("limit") or 25)
        min_mw = Decimal(str(params.get("min_mw") or 75))
        keywords = _keyword_terms(params)

        with httpx.Client(timeout=45, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(workbook_url)
            response.raise_for_status()
            rows = _xlsx_rows(response.content)

        candidates: list[tuple[int, date, dict[str, Any]]] = []
        seen: set[str] = set()
        for data in _row_dicts(rows, [("queue pos.", "queue pos"), ("project name",), ("county",)]):
            queue_position = _first_value(data, "Queue Pos.", "Queue Pos")
            project_name = _first_value(data, "Project Name")
            if not queue_position or not project_name or queue_position in seen:
                continue
            seen.add(queue_position)

            summer_mw = _parse_decimal(_first_value(data, "SP (MW)", "Summer MW", "MW")) or Decimal("0")
            winter_mw = _parse_decimal(_first_value(data, "WP (MW)", "Winter MW")) or Decimal("0")
            max_mw = max(summer_mw, winter_mw)
            if max_mw < min_mw:
                continue

            text = " ".join(str(value) for value in data.values())
            if not _matches_keywords(text, keywords):
                continue

            customer = _first_value(data, "Developer/Interconnection Customer", "Interconnection Customer Name", "Owner/Developer") or "NYISO interconnection customer"
            state = _first_value(data, "State") or "NY"
            county = _first_value(data, "County") or None
            resource_type = _first_value(data, "Type/ Fuel", "Type / Fuel") or "not stated"
            poi = _first_value(data, "Points of Interconnection", "Interconnection Point")
            utility = _first_value(data, "Utility", "Utility ")
            affected_owner = _first_value(data, "Affected Transmission Owner (ATO)")
            owner = affected_owner or utility or "NYISO transmission owner"
            last_updated = _parse_date(_first_value(data, "Last Updated Date"))
            proposed_backfeed = _parse_date(_first_value(data, "Proposed In-Service/Initial Backfeed Date"))
            proposed_cod = _parse_date(_first_value(data, "Proposed COD"))
            forecast_anchor = proposed_backfeed or proposed_cod
            score_text = f"{project_name} {customer} {resource_type} {poi} {owner} {county} {state}"
            description = "\n".join(
                [
                    f"Official NYISO interconnection queue signal for {project_name}.",
                    f"Queue position: {queue_position}.",
                    f"Developer / interconnection customer: {customer}.",
                    f"Utility / affected transmission owner: {utility or 'Not stated'} / {affected_owner or 'Not stated'}.",
                    f"Point of interconnection: {poi or 'Not stated'}.",
                    f"County / state: {county or 'Not stated'}, {state or 'Not stated'}.",
                    f"Type / fuel: {resource_type}.",
                    f"Summer peak / winter peak: {summer_mw} MW / {winter_mw} MW.",
                    f"Energy storage capability: {_first_value(data, 'Energy Storage Capability') or 'Not stated'}.",
                    f"Availability of studies: {_first_value(data, 'Availability of Studies') or 'Not stated'}.",
                    f"IA tender date: {_parse_date(_first_value(data, 'IA Tender Date')) or 'Not stated'}.",
                    f"Proposed in-service/backfeed date: {proposed_backfeed or 'Not stated'}.",
                    f"Proposed COD: {proposed_cod or 'Not stated'}.",
                    f"Last updated: {last_updated or 'Not stated'}.",
                ]
            )
            candidates.append(
                (
                    _keyword_score(score_text),
                    last_updated or forecast_anchor or date.min,
                    _record(
                        title=f"NYISO interconnection {queue_position}: {project_name} ({max_mw} MW {resource_type})",
                        agency=owner,
                        location=", ".join(part for part in [county, state, "NYISO"] if part),
                        state=state,
                        description=description,
                        source="nyiso_interconnection_queue",
                        source_type="rto_iso",
                        source_url=f"{page_url}#queue-{queue_position}",
                        signal_type="interconnection_queue",
                        owner_type=_owner_type(f"{owner} {utility} {customer}", default="private_developer"),
                        forecast_rfp_date=_forecast_before(forecast_anchor),
                        attachments=[
                            _evidence("NYISO Interconnections page", page_url, "nyiso_interconnection_queue"),
                            _evidence("NYISO interconnection queue workbook", workbook_url, "nyiso_interconnection_queue"),
                        ],
                    ),
                )
            )

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [record for _, _, record in candidates[:limit]]

    def _latest_workbook_url(self, page_url: str) -> str:
        with httpx.Client(timeout=30, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(page_url)
            response.raise_for_status()
        links = re.findall(r'href=["\']([^"\']+\.xlsx[^"\']*)["\']', response.text, flags=re.IGNORECASE)
        for link in links:
            decoded = html.unescape(link)
            if "NYISO-Interconnection-Queue" in decoded:
                return urljoin(str(response.url), decoded)
        return NYISO_QUEUE_WORKBOOK_URL


class VirginiaSccTransmissionCasesAdapter(IngestionAdapter):
    name = "virginia_scc_transmission_cases"
    description = "Official Virginia SCC transmission-line case listing for CPCN and high-voltage grid expansion signals."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        url = params.get("url") or VIRGINIA_SCC_TRANSMISSION_PAGE_URL
        limit = int(params.get("limit") or 25)
        source_limit = int(params.get("source_limit") or 250)
        keywords = _keyword_terms(params)

        response = _get_with_official_tls_fallback(url)
        response.raise_for_status()

        pattern = re.compile(
            r"<li>\s*<a\s+href=[\"']([^\"']+)[\"'][^>]*>\s*((?:PUR|PUE)-\d{4}-\d{5})\s*</a>\s*(.*?)(?:<ul>|</li>)",
            flags=re.IGNORECASE | re.DOTALL,
        )
        candidates: list[tuple[int, str, dict[str, Any]]] = []
        for match in list(pattern.finditer(response.text))[:source_limit]:
            href, case_number, raw_description = match.groups()
            description_line = _clean(re.sub(r"<[^>]+>", " ", raw_description))
            if not description_line:
                continue
            text = f"{case_number} {description_line}"
            if not _matches_keywords(text, keywords):
                continue

            agency = _latest_known_agency(response.text, match.start(), VIRGINIA_SCC_UTILITY_NAMES) or "Virginia State Corporation Commission"
            location = description_line.split(" - ", 1)[0].split(" – ", 1)[0].strip(" -–") or "Virginia"
            source_url = urljoin(str(response.url), href)
            excerpt = f"Virginia SCC recent transmission case {case_number}: {description_line}"
            body = "\n".join(
                [
                    f"Official Virginia SCC transmission-line case signal for {case_number}.",
                    f"Listed utility / applicant context: {agency}.",
                    f"Case description: {description_line}.",
                    "Virginia SCC states that construction and operation of transmission lines and/or facilities above 115 kV usually require a CPCN.",
                    "Review the SCC DocketSearch case and project map before outreach, partnering, or bid/no-bid decisions.",
                ]
            )
            candidates.append(
                (
                    _keyword_score(text),
                    case_number,
                    _record(
                        title=f"Virginia SCC transmission case {case_number}: {description_line}",
                        agency=agency,
                        location=location,
                        state="VA",
                        description=body,
                        source="virginia_scc_transmission_cases",
                        source_type="regulatory",
                        source_url=source_url,
                        signal_type="puc_docket",
                        owner_type=_owner_type(agency, default="public_power_or_utility"),
                        attachments=[
                            _evidence("Virginia SCC Transmission Line Projects page", url, "virginia_scc_transmission_cases", excerpt),
                            _evidence(f"Virginia SCC DocketSearch case {case_number}", source_url, "virginia_scc_transmission_cases"),
                        ],
                    ),
                )
            )

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [record for _, _, record in candidates[:limit]]


class GeorgiaPscDataCenterAdapter(IngestionAdapter):
    name = "georgia_psc_data_center"
    description = "Official Georgia PSC data-center regulatory signal for large-load generation, data-center contracts, and Georgia Power filings."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        page_url = params.get("page_url") or GEORGIA_PSC_HOME_URL
        fact_sheet_url = params.get("url") or GEORGIA_PSC_DATA_CENTER_FACT_SHEET_URL
        keywords = _keyword_terms(params)

        with httpx.Client(timeout=45, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            page_response = client.get(page_url)
            page_response.raise_for_status()
            match = re.search(r'href=["\']([^"\']*datacenterfactsheet\.pdf)["\']', page_response.text, flags=re.IGNORECASE)
            if match and not params.get("url"):
                fact_sheet_url = urljoin(str(page_response.url), html.unescape(match.group(1)))
            fact_response = client.get(fact_sheet_url)
            fact_response.raise_for_status()

        page_text = _clean(re.sub(r"<[^>]+>", " ", page_response.text))
        fact_text = _decode_document_text(fact_response.content)
        combined_text = f"{page_text} {fact_text}"
        if keywords and not _matches_keywords(combined_text, keywords):
            return []

        docket_match = re.search(r"Docket\s+#?(\d+)", combined_text, flags=re.IGNORECASE)
        docket_number = docket_match.group(1) if docket_match else "44280"
        certified_match = re.search(r"certif(?:y|ies|ied|ying)[^.]{0,120}?(\d{1,2},\d{3})\s*MW", combined_text, flags=re.IGNORECASE)
        if certified_match:
            mw_text = certified_match.group(1)
        else:
            mw_values = [int(match.replace(",", "")) for match in re.findall(r"(\d{1,2},\d{3})\s*MW", combined_text, flags=re.IGNORECASE)]
            mw_text = f"{max(mw_values):,}" if mw_values else "9,985"
        excerpt = (
            "Georgia PSC data-center fact sheet states Georgia Power must file quarterly data-center reports, "
            f"and that the Commission certified {mw_text} MW of new energy generation with a large data-center load component."
        )
        body = "\n".join(
            [
                "Official Georgia PSC data center power regulatory signal for Georgia Power large-load, generation, transmission, substation, utility interconnection, and critical power planning.",
                f"Referenced docket: {docket_number}.",
                "The PSC homepage points residents to Docket #44280 and official data-center documents.",
                excerpt,
                "This is not an active construction bid; it is an early regulatory and utility-planning signal for data center power, generation, substation, transmission, and large-load commercial follow-up.",
            ]
        )
        return [
            _record(
                title=f"Georgia PSC data center large-load signal: Docket {docket_number} and {mw_text} MW generation planning",
                agency="Georgia Public Service Commission / Georgia Power",
                location="Georgia",
                state="GA",
                description=body,
                source="georgia_psc_data_center",
                source_type="regulatory",
                source_url=page_url,
                signal_type="puc_docket",
                owner_type="investor_owned_utility",
                attachments=[
                    _evidence("Georgia PSC homepage data-center notice", page_url, "georgia_psc_data_center"),
                    _evidence("Georgia PSC Data Center Fact Sheet", fact_sheet_url, "georgia_psc_data_center", excerpt),
                ],
            )
        ]


class TexasPucDocketsAdapter(IngestionAdapter):
    name = "texas_puc_dockets"
    description = "Public Utility Commission of Texas Interchange docket signals for electric transmission, CCN, and large-load proceedings."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        url = params.get("url") or TEXAS_PUC_DOCKETS_URL
        limit = int(params.get("limit") or 25)
        source_limit = int(params.get("source_limit") or 500)
        keywords = _keyword_terms(params)

        response = _get_with_official_tls_fallback(url)
        response.raise_for_status()

        parser = _TableRowParser(str(response.url))
        parser.feed(response.text)
        opportunities: list[dict[str, Any]] = []
        for cells, links in parser.rows[:source_limit]:
            if len(cells) < 4 or cells[0].lower() == "control":
                continue
            control, filing_count, utility, description = cells[:4]
            text = f"{control} {filing_count} {utility} {description}"
            if not _matches_keywords(text, keywords):
                continue
            source_url = links[0] if links else f"{url}#control-{control}"
            body = "\n".join(
                [
                    f"Official Texas PUCT electric docket signal for control number {control}.",
                    f"Utility / filing party: {utility or 'Not stated'}.",
                    f"Filing count: {filing_count or 'Not stated'}.",
                    f"Case style: {description}.",
                    "Review the Interchange docket for CCN, transmission cost recovery, interconnection, or large-load context before bid/no-bid decisions.",
                ]
            )
            opportunities.append(
                _record(
                    title=f"Texas PUCT docket {control}: {description}",
                    agency=utility or "Public Utility Commission of Texas",
                    location="Texas",
                    state="TX",
                    description=body,
                    source="texas_puc_dockets",
                    source_type="regulatory",
                    source_url=source_url,
                    signal_type="puc_docket",
                    owner_type=_owner_type(utility, default="public_power_or_utility"),
                    attachments=[
                        _evidence("Texas PUCT Interchange electric dockets", url, "texas_puc_dockets"),
                        _evidence(f"Texas PUCT docket {control}", source_url, "texas_puc_dockets"),
                    ],
                )
            )
            if len(opportunities) >= limit:
                break
        return opportunities


class LoudounLandApplicationsAdapter(IngestionAdapter):
    name = "loudoun_land_applications"
    description = "Official Loudoun County ArcGIS land application layer for data-center and industrial permitting signals."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        layer_url = params.get("layer_url") or LOUDOUN_LAND_APPLICATIONS_LAYER_URL
        page_url = params.get("page_url") or LOUDOUN_LAND_APPLICATIONS_PAGE_URL
        limit = int(params.get("limit") or 25)
        source_limit = int(params.get("source_limit") or 250)
        statuses = params.get("statuses") or ["In Review"]
        status_sql = ",".join(f"'{_clean(status)}'" for status in statuses)
        where = params.get("where") or f"PlanStatus IN ({status_sql})"
        keywords = _keyword_terms(params)

        with httpx.Client(timeout=45, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
            response = client.get(
                f"{layer_url}/query",
                params={
                    "f": "json",
                    "where": where,
                    "outFields": "*",
                    "returnGeometry": "false",
                    "resultRecordCount": source_limit,
                    "orderByFields": "PlanApplicationDate DESC",
                },
            )
            response.raise_for_status()
            payload = response.json()
        if payload.get("error"):
            raise ValueError(f"Loudoun ArcGIS query failed: {payload['error']}")

        candidates: list[tuple[int, date, dict[str, Any]]] = []
        for feature in payload.get("features", []):
            attrs = feature.get("attributes") or {}
            plan_number = _clean(attrs.get("PlanNumber"))
            plan_name = _clean(attrs.get("PlanName"))
            plan_description = _clean(attrs.get("PlanDescription"))
            if not plan_number or not plan_name:
                continue
            text = " ".join([plan_number, plan_name, plan_description, _clean(attrs.get("PlanType")), _clean(attrs.get("PlanStatus"))])
            if not _matches_keywords(text, keywords):
                continue
            score = _keyword_score(text)
            application_date = _parse_date(attrs.get("PlanApplicationDate"))
            source_url = f"{page_url}#{plan_number}"
            body = "\n".join(
                [
                    f"Official Loudoun County land application signal for {plan_name}.",
                    f"Plan number: {plan_number}.",
                    f"Plan type: {_clean(attrs.get('PlanType')) or 'Not stated'}.",
                    f"Plan status: {_clean(attrs.get('PlanStatus')) or 'Not stated'}.",
                    f"Application date: {application_date or 'Not stated'}.",
                    f"Assigned planner: {_clean(attrs.get('AssignedTo')) or 'Not stated'}.",
                    f"Description: {plan_description or 'Not stated'}.",
                ]
            )
            candidates.append(
                (
                    score,
                    application_date or date.min,
                    _record(
                        title=f"Loudoun land application {plan_number}: {plan_name}",
                        agency="Loudoun County Planning and Zoning",
                        location="Loudoun County, VA",
                        state="VA",
                        description=body,
                        source="loudoun_land_applications",
                        source_type="land_use",
                        source_url=source_url,
                        signal_type="zoning_or_permit",
                        owner_type="private_developer",
                        attachments=[
                            _evidence("Loudoun Land Applications page", page_url, "loudoun_land_applications"),
                            _evidence("Loudoun LOLA_DATA ArcGIS layer", layer_url, "loudoun_land_applications"),
                        ],
                    ),
                )
            )
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [record for _, _, record in candidates[:limit]]
