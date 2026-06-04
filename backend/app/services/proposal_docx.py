from __future__ import annotations

import html
import io
import zipfile
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"${float(value):,.0f}"
    return html.escape(str(value), quote=False)


def _paragraph(text: Any = "", style: str | None = None) -> str:
    style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{style_xml}<w:r><w:t>{_safe_text(text)}</w:t></w:r></w:p>"


def _bullet(text: Any) -> str:
    return (
        '<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>'
        f"<w:r><w:t>{_safe_text(text)}</w:t></w:r></w:p>"
    )


def _table(rows: list[list[Any]]) -> str:
    cells = []
    for row in rows:
        row_xml = "".join(
            "<w:tc><w:tcPr><w:tcW w:w=\"2400\" w:type=\"dxa\"/></w:tcPr>"
            f"{_paragraph(cell)}</w:tc>"
            for cell in row
        )
        cells.append(f"<w:tr>{row_xml}</w:tr>")
    return f"<w:tbl><w:tblPr><w:tblW w:w=\"0\" w:type=\"auto\"/><w:tblBorders><w:top w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"B8C2CC\"/><w:left w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"B8C2CC\"/><w:bottom w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"B8C2CC\"/><w:right w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"B8C2CC\"/><w:insideH w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"B8C2CC\"/><w:insideV w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"B8C2CC\"/></w:tblBorders></w:tblPr>{''.join(cells)}</w:tbl>"


def _section(title: str, body: Any) -> list[str]:
    parts = [_paragraph(title, "Heading1")]
    if isinstance(body, list):
        for item in body:
            parts.append(_bullet(item))
    else:
        parts.append(_paragraph(body))
    return parts


def _document_xml(opportunity: Mapping, proposal: Mapping, company_profile: Mapping | None) -> str:
    company = (company_profile or {}).get("name") or "Taihan Cable & Solution"
    title = opportunity.get("title") or "Opportunity"
    agency = opportunity.get("agency") or "Issuing agency"
    due = opportunity.get("due_date") or "Due date not posted"
    value = opportunity.get("estimated_value") or "Value not posted"
    stage = str(opportunity.get("project_stage") or "active_bid").replace("_", " ")
    source_type = str(opportunity.get("source_type") or "source not classified").replace("_", " ")
    fit_score = opportunity.get("fit_score")
    fit_text = f"{fit_score}/100" if fit_score is not None else "Not scored"
    value_confidence = str(opportunity.get("value_confidence") or "unknown").replace("_", " ")
    summary_rows = [
        ["Field", "Value"],
        ["Agency", agency],
        ["Stage", stage],
        ["Source type", source_type],
        ["Fit score", fit_text],
        ["Due date", due],
        ["Estimated value", f"{value} ({value_confidence})"],
    ]
    rows = [
        ["Requirement", "Status", "Evidence", "Owner"],
        *[
            [
                row.get("requirement", ""),
                row.get("status", ""),
                row.get("evidence", ""),
                row.get("owner", ""),
            ]
            for row in proposal.get("compliance_matrix", [])
            if isinstance(row, Mapping)
        ],
    ]
    body_parts = [
        _paragraph(f"{company} Proposal Prep Package", "Title"),
        _paragraph("Pursuit Decision Brief", "Heading1"),
        _paragraph(title, "Heading1"),
        _table(summary_rows),
        *_section("Executive Summary", proposal.get("draft_executive_summary", "")),
        *_section("Bid / No-Bid Recommendation", proposal.get("bid_no_bid_memo", "")),
        *_section("Bid Summary", proposal.get("bid_summary", "")),
        *_section("Scope Checklist", proposal.get("scope_checklist", [])),
        *_section("Missing Information Checklist", proposal.get("missing_information_checklist", [])),
        *_section("Required Documents Checklist", proposal.get("required_documents_checklist", [])),
        *_section("Risk Flags", proposal.get("risk_flags", []) or ["No major automated risk flags."]),
        _paragraph("Compliance Matrix", "Heading1"),
        _table(rows),
        *_section("Partner Outreach Email", proposal.get("partner_email_template", "")),
    ]
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(body_parts)}<w:sectPr><w:pgSz w:w=\"12240\" w:h=\"15840\"/><w:pgMar w:top=\"720\" w:right=\"720\" w:bottom=\"720\" w:left=\"720\"/></w:sectPr></w:body>"
        "</w:document>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:rPr><w:b/><w:color w:val="2F7D53"/><w:sz w:val="40"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:rPr><w:b/><w:color w:val="20231F"/><w:sz w:val="28"/></w:rPr></w:style>'
        "</w:styles>"
    )


def _numbering_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="-"/><w:lvlJc w:val="left"/></w:lvl></w:abstractNum>'
        '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>'
        "</w:numbering>"
    )


def generate_proposal_docx(opportunity: Mapping, proposal: Mapping, company_profile: Mapping | None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as docx:
        docx.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
            "</Types>",
        )
        docx.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            "</Relationships>",
        )
        docx.writestr(
            "word/_rels/document.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>'
            "</Relationships>",
        )
        docx.writestr("word/document.xml", _document_xml(opportunity, proposal, company_profile))
        docx.writestr("word/styles.xml", _styles_xml())
        docx.writestr("word/numbering.xml", _numbering_xml())
    return buffer.getvalue()
