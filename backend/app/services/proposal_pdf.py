from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from textwrap import wrap
from typing import Any, Mapping


PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN_X = 54
TOP_Y = 738
BOTTOM_Y = 54
LINE_HEIGHT = 14


def _plain_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"${float(value):,.0f}"
    return str(value)


def _pdf_string(value: str) -> str:
    safe = value.encode("latin-1", errors="replace").decode("latin-1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _add_wrapped(lines: list[tuple[str, int]], text: Any, size: int = 10, prefix: str = "") -> None:
    raw = _plain_text(text).strip()
    if not raw:
        lines.append(("", size))
        return
    width = 78 if size <= 10 else 58
    for paragraph in raw.splitlines():
        paragraph = paragraph.strip()
        if not paragraph:
            lines.append(("", size))
            continue
        wrapped = wrap(paragraph, width=width, break_long_words=False, replace_whitespace=False) or [paragraph]
        for index, part in enumerate(wrapped):
            lines.append((f"{prefix if index == 0 else '  '}{part}", size))


def _add_section(lines: list[tuple[str, int]], title: str, body: Any) -> None:
    lines.append(("", 10))
    lines.append((title, 14))
    if isinstance(body, list):
        if not body:
            _add_wrapped(lines, "None listed.", 10)
        for item in body:
            _add_wrapped(lines, item, 10, prefix="- ")
    else:
        _add_wrapped(lines, body, 10)


def _document_lines(opportunity: Mapping, proposal: Mapping, company_profile: Mapping | None) -> list[tuple[str, int]]:
    company = (company_profile or {}).get("name") or "Taihan Cable & Solution"
    title = opportunity.get("title") or "Opportunity"
    agency = opportunity.get("agency") or "Issuing agency"
    due = opportunity.get("due_date") or "Due date not posted"
    value = opportunity.get("estimated_value") or "Value not posted"
    lines: list[tuple[str, int]] = [
        (f"{company} Proposal Prep Package", 18),
        (str(title), 14),
        (f"Agency: {agency}", 10),
        (f"Due date: {due}", 10),
        (f"Estimated value: {value}", 10),
    ]
    _add_section(lines, "Bid Summary", proposal.get("bid_summary", ""))
    _add_section(lines, "Draft Executive Summary", proposal.get("draft_executive_summary", ""))
    _add_section(lines, "Scope Checklist", proposal.get("scope_checklist", []))
    _add_section(lines, "Missing Information Checklist", proposal.get("missing_information_checklist", []))
    _add_section(lines, "Required Documents Checklist", proposal.get("required_documents_checklist", []))
    _add_section(lines, "Risk Flags", proposal.get("risk_flags", []) or ["No major automated risk flags."])
    lines.append(("", 10))
    lines.append(("Compliance Matrix", 14))
    matrix = proposal.get("compliance_matrix", [])
    if matrix:
        for row in matrix:
            if isinstance(row, Mapping):
                _add_wrapped(
                    lines,
                    f"{row.get('requirement', '')} | {row.get('status', '')} | {row.get('evidence', '')} | Owner: {row.get('owner', '')}",
                    9,
                    prefix="- ",
                )
    else:
        _add_wrapped(lines, "No compliance matrix rows generated.", 10)
    _add_section(lines, "Bid / No-Bid Memo", proposal.get("bid_no_bid_memo", ""))
    _add_section(lines, "Partner Outreach Email", proposal.get("partner_email_template", ""))
    return lines


def _paginate(lines: list[tuple[str, int]]) -> list[list[tuple[str, int]]]:
    pages: list[list[tuple[str, int]]] = [[]]
    y = TOP_Y
    for text, size in lines:
        height = max(LINE_HEIGHT, size + 4)
        if y - height < BOTTOM_Y and pages[-1]:
            pages.append([])
            y = TOP_Y
        pages[-1].append((text, size))
        y -= height
    return pages


def _content_stream(lines: list[tuple[str, int]], page_number: int, page_count: int) -> bytes:
    y = TOP_Y
    commands: list[str] = []
    for text, size in lines:
        height = max(LINE_HEIGHT, size + 4)
        if text:
            commands.append(f"BT /F1 {size} Tf {MARGIN_X} {y} Td ({_pdf_string(text)}) Tj ET")
        y -= height
    commands.append(f"BT /F1 9 Tf {MARGIN_X} 32 Td (Page {page_number} of {page_count}) Tj ET")
    return "\n".join(commands).encode("latin-1", errors="replace")


def _pdf_object(object_id: int, body: bytes | str) -> bytes:
    if isinstance(body, str):
        body = body.encode("latin-1", errors="replace")
    return b"%d 0 obj\n" % object_id + body + b"\nendobj\n"


def generate_proposal_pdf(opportunity: Mapping, proposal: Mapping, company_profile: Mapping | None) -> bytes:
    pages = _paginate(_document_lines(opportunity, proposal, company_profile))
    font_object_id = 3 + len(pages) * 2
    objects: list[bytes] = []
    page_object_ids = [3 + index * 2 for index in range(len(pages))]
    content_object_ids = [4 + index * 2 for index in range(len(pages))]
    objects.append(_pdf_object(1, "<< /Type /Catalog /Pages 2 0 R >>"))
    kids = " ".join(f"{page_id} 0 R" for page_id in page_object_ids)
    objects.append(_pdf_object(2, f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>"))

    for index, page_lines in enumerate(pages):
        page_id = page_object_ids[index]
        content_id = content_object_ids[index]
        page = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Resources << /Font << /F1 {font_object_id} 0 R >> >> /Contents {content_id} 0 R >>"
        )
        objects.append(_pdf_object(page_id, page))
        stream = _content_stream(page_lines, index + 1, len(pages))
        objects.append(
            _pdf_object(
                content_id,
                b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            )
        )

    objects.append(_pdf_object(font_object_id, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(output))
        output.extend(obj)
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(output)
