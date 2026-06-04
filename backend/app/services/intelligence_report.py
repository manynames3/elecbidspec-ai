from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal
from textwrap import wrap
from typing import Any


PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN_X = 54
TOP_Y = 738
BOTTOM_Y = 54
LINE_HEIGHT = 14


def _plain(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return f"${float(value):,.0f}"
    return str(value)


def _clean(value: Any, limit: int | None = None) -> str:
    text = " ".join(_plain(value).split())
    if limit and len(text) > limit:
        return f"{text[: limit - 3].rstrip()}..."
    return text


def _money(value: Any) -> str:
    if value is None or value == "":
        return "Value not posted"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"${amount:,.0f}"


def _date_text(value: Any) -> str:
    if not value:
        return "Not posted"
    if isinstance(value, (date, datetime)):
        return value.isoformat()[:10]
    return str(value)[:10]


def _intel(opportunity: Mapping[str, Any]) -> Mapping[str, Any]:
    return ((opportunity.get("extracted_specs") or {}).get("taihan_intelligence") or {})


def _pursuit(opportunity: Mapping[str, Any]) -> Mapping[str, Any]:
    return ((opportunity.get("extracted_specs") or {}).get("pursuit_intelligence") or {})


def _score(opportunity: Mapping[str, Any]) -> int:
    try:
        return int(_intel(opportunity).get("score") or 0)
    except (TypeError, ValueError):
        return 0


def _sort_key(opportunity: Mapping[str, Any]) -> tuple[int, int, int]:
    stage_boost = 20 if opportunity.get("project_stage") in {"early_signal", "pre_rfp"} else 0
    value_boost = 10 if opportunity.get("minimum_value_match") else 0
    fit = int(opportunity.get("fit_score") or 0)
    return (_score(opportunity) + stage_boost + value_boost, fit, 1 if _pursuit(opportunity).get("evidence_grade") == "strong" else 0)


def _brief_row(opportunity: Mapping[str, Any]) -> dict[str, Any]:
    pursuit = _pursuit(opportunity)
    intel = _intel(opportunity)
    evidence = pursuit.get("source_evidence") or []
    return {
        "id": opportunity.get("id"),
        "title": opportunity.get("title"),
        "agency": opportunity.get("agency"),
        "state": opportunity.get("state"),
        "location": opportunity.get("location"),
        "source": opportunity.get("source"),
        "source_type": opportunity.get("source_type"),
        "source_url": opportunity.get("source_url"),
        "project_stage": opportunity.get("project_stage"),
        "signal_type": opportunity.get("signal_type"),
        "owner_type": opportunity.get("owner_type"),
        "forecast_rfp_date": _date_text(opportunity.get("forecast_rfp_date")),
        "due_date": _date_text(opportunity.get("due_date")),
        "estimated_value": _money(opportunity.get("estimated_value")),
        "fit_score": opportunity.get("fit_score"),
        "taihan_score": intel.get("score"),
        "taihan_tier": intel.get("tier"),
        "cable_relevance": intel.get("cable_relevance"),
        "procurement_path": intel.get("procurement_path"),
        "entry_window": intel.get("entry_window"),
        "evidence_grade": pursuit.get("evidence_grade"),
        "why_now": pursuit.get("why_now"),
        "next_actions": pursuit.get("next_actions") or [],
        "relationship_targets": pursuit.get("relationship_targets") or [],
        "partner_targets": pursuit.get("partner_targets") or [],
        "signal_change": pursuit.get("signal_change") or {},
        "analyst_review": pursuit.get("analyst_review") or {},
        "source_evidence": evidence,
        "evidence_excerpt": next((item.get("excerpt") for item in evidence if item.get("excerpt")), ""),
    }


def build_opportunity_brief(opportunity: Mapping[str, Any], company_profile: Mapping[str, Any] | None = None) -> dict[str, Any]:
    row = _brief_row(opportunity)
    company_name = (company_profile or {}).get("name") or "Taihan Cable & Solution"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "company": company_name,
        "opportunity": row,
        "executive_read": (
            f"{row['title']} is a {row['project_stage']} signal with Taihan score {row['taihan_score']} "
            f"and {row['evidence_grade']} evidence. {row['why_now']}"
        ),
        "recommended_posture": _intel(opportunity).get("recommended_action"),
        "pursuit_decision": "escalate" if row.get("taihan_tier") == "high" else "watch" if row.get("taihan_tier") == "medium" else "monitor",
    }


def build_weekly_intelligence_report(
    opportunities: list[Mapping[str, Any]],
    source_health: list[Mapping[str, Any]] | None = None,
    company_profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    company_name = (company_profile or {}).get("name") or "Taihan Cable & Solution"
    upstream = [item for item in opportunities if item.get("project_stage") in {"early_signal", "pre_rfp"}]
    active = [item for item in opportunities if item.get("project_stage") == "active_bid" or item.get("bid_status") == "open"]
    high = [item for item in upstream if _intel(item).get("tier") == "high"]
    data_center = [
        item
        for item in upstream
        if (_intel(item).get("evidence_strength") or {}).get("data_center_or_load")
        or "data center" in _clean(item.get("title")).lower()
        or "data center" in _clean(item.get("description")).lower()
    ]
    changed = [
        item
        for item in upstream
        if (_pursuit(item).get("signal_change") or {}).get("status") in {"new", "updated", "escalated", "active_bid_handoff"}
    ]
    sorted_upstream = sorted(upstream, key=_sort_key, reverse=True)
    sorted_active = sorted(active, key=_sort_key, reverse=True)
    source_health = list(source_health or [])
    healthy_sources = len([item for item in source_health if item.get("status") == "healthy"])
    evidence_strong = len([item for item in upstream if _pursuit(item).get("evidence_grade") == "strong"])

    top_signals = [_brief_row(item) for item in sorted_upstream[:10]]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "company": company_name,
        "title": f"{company_name} U.S. Pre-RFP Power Infrastructure Intelligence",
        "summary": {
            "upstream_signals": len(upstream),
            "high_priority": len(high),
            "data_center_or_large_load": len(data_center),
            "active_bid_handoffs": len(active),
            "strong_evidence": evidence_strong,
            "live_importing_sources": healthy_sources,
            "tracked_sources": len(source_health),
        },
        "executive_takeaway": (
            f"{company_name} has {len(high)} high-priority upstream signals and {len(data_center)} data-center or large-load signals in the current pipeline. "
            "The highest-leverage action is to verify source evidence, assign BD ownership, and start utility/EPC positioning before formal RFP release."
        ),
        "top_signals": top_signals,
        "watchlist_changes": [_brief_row(item) for item in sorted(changed, key=_sort_key, reverse=True)[:8]],
        "active_bid_handoffs": [_brief_row(item) for item in sorted_active[:6]],
        "recommended_actions": [
            "Review the top 10 source-backed signals and mark each verified, needs evidence, monitor, or no-bid.",
            "For high-priority IOU/regulatory records, map utility planning, procurement, and transmission engineering contacts.",
            "For data-center or large-load records, identify developer, load-serving utility, substation owner, and likely EPC/design partner.",
            "Generate one-page briefs for every high-priority signal before partner outreach.",
            "Confirm AVL/vendor-registration gaps and prepare Taihan HV/MV/EHV cable capability language for each target owner.",
        ],
        "source_health": source_health,
    }
    return report


def _pdf_string(value: str) -> str:
    safe = value.encode("latin-1", errors="replace").decode("latin-1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _add_wrapped(lines: list[tuple[str, int]], text: Any, size: int = 10, prefix: str = "") -> None:
    raw = _clean(text)
    if not raw:
        lines.append(("", size))
        return
    width = 82 if size <= 10 else 58
    for paragraph in raw.splitlines():
        wrapped = wrap(paragraph.strip(), width=width, break_long_words=False, replace_whitespace=False) or [paragraph]
        for index, part in enumerate(wrapped):
            lines.append((f"{prefix if index == 0 else '  '}{part}", size))


def _section(lines: list[tuple[str, int]], title: str) -> None:
    lines.append(("", 10))
    lines.append((title, 14))


def _report_lines(report: Mapping[str, Any]) -> list[tuple[str, int]]:
    summary = report.get("summary") or {}
    lines: list[tuple[str, int]] = [
        (_clean(report.get("title") or "Weekly Intelligence Report"), 18),
        (f"Generated: {_date_text(report.get('generated_at'))}", 10),
        ("Executive Intelligence Report", 14),
    ]
    _add_wrapped(lines, report.get("executive_takeaway"), 10)
    _section(lines, "Pipeline Snapshot")
    for key in [
        "upstream_signals",
        "high_priority",
        "data_center_or_large_load",
        "active_bid_handoffs",
        "strong_evidence",
        "live_importing_sources",
        "tracked_sources",
    ]:
        _add_wrapped(lines, f"{key.replace('_', ' ').title()}: {summary.get(key, 0)}", 10, prefix="- ")
    _section(lines, "Recommended Actions This Week")
    for item in report.get("recommended_actions") or []:
        _add_wrapped(lines, item, 10, prefix="- ")
    _section(lines, "Top Pre-RFP Signals")
    for index, item in enumerate(report.get("top_signals") or [], start=1):
        _add_wrapped(lines, f"{index}. {item.get('title')} | Taihan {item.get('taihan_score')} | {item.get('evidence_grade')} evidence", 10)
        _add_wrapped(lines, item.get("why_now"), 9, prefix="   ")
        actions = item.get("next_actions") or []
        if actions:
            _add_wrapped(lines, f"Next: {actions[0]}", 9, prefix="   ")
    return lines


def _brief_lines(brief: Mapping[str, Any]) -> list[tuple[str, int]]:
    item = brief.get("opportunity") or {}
    lines: list[tuple[str, int]] = [
        (f"{brief.get('company') or 'Taihan'} Opportunity Brief", 18),
        (_clean(item.get("title") or "Opportunity"), 14),
        (f"Generated: {_date_text(brief.get('generated_at'))}", 10),
        (f"Agency: {_clean(item.get('agency') or 'Not posted')}", 10),
        (f"Stage: {_clean(item.get('project_stage'))} | Signal: {_clean(item.get('signal_type'))}", 10),
        (f"Taihan score: {item.get('taihan_score')} | Evidence: {item.get('evidence_grade')} | Value: {item.get('estimated_value')}", 10),
    ]
    _section(lines, "Executive Read")
    _add_wrapped(lines, brief.get("executive_read"), 10)
    _section(lines, "Why Now")
    _add_wrapped(lines, item.get("why_now"), 10)
    _section(lines, "Recommended Posture")
    _add_wrapped(lines, brief.get("recommended_posture"), 10)
    _section(lines, "Next Actions")
    for action in item.get("next_actions") or []:
        _add_wrapped(lines, action, 10, prefix="- ")
    _section(lines, "Relationship Targets")
    for target in item.get("relationship_targets") or []:
        _add_wrapped(lines, f"{target.get('role')}: {target.get('name')} - {target.get('action')}", 9, prefix="- ")
    _section(lines, "Source Evidence")
    for evidence in item.get("source_evidence") or []:
        _add_wrapped(lines, f"{evidence.get('name')} | {evidence.get('url')}", 9, prefix="- ")
        if evidence.get("excerpt"):
            _add_wrapped(lines, evidence.get("excerpt"), 9, prefix="  ")
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
    commands: list[str] = [
        "0.97 0.98 0.99 rg 0 0 612 792 re f",
        "1 1 1 rg 36 42 540 708 re f",
        "0.03 0.13 0.28 rg 36 750 540 6 re f",
        "0.88 0.92 0.97 RG 36 42 540 708 re S",
        "0.93 0.96 1 rg 36 42 540 34 re f",
    ]
    for text, size in lines:
        height = max(LINE_HEIGHT, size + 4)
        if text:
            if size >= 18:
                commands.append(f"0.03 0.13 0.28 rg {MARGIN_X} {y - 12} 240 3 re f")
                color = "0.03 0.10 0.22 rg"
            elif size >= 14:
                commands.append(f"0.93 0.96 1 rg {MARGIN_X - 8} {y - 5} 512 21 re f")
                commands.append(f"0.16 0.37 0.70 rg {MARGIN_X - 8} {y - 5} 4 21 re f")
                color = "0.03 0.13 0.28 rg"
            else:
                color = "0.16 0.19 0.24 rg"
            commands.append(f"{color} BT /F1 {size} Tf {MARGIN_X} {y} Td ({_pdf_string(text)}) Tj ET")
        y -= height
    commands.append(f"0.39 0.45 0.55 rg BT /F1 9 Tf {MARGIN_X} 32 Td (ElecBidSpec AI | Page {page_number} of {page_count}) Tj ET")
    return "\n".join(commands).encode("latin-1", errors="replace")


def _pdf_object(object_id: int, body: bytes | str) -> bytes:
    if isinstance(body, str):
        body = body.encode("latin-1", errors="replace")
    return b"%d 0 obj\n" % object_id + body + b"\nendobj\n"


def _render_pdf(lines: list[tuple[str, int]]) -> bytes:
    pages = _paginate(lines)
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
        objects.append(_pdf_object(content_id, b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"))

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
    output.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii"))
    return bytes(output)


def generate_weekly_intelligence_pdf(report: Mapping[str, Any]) -> bytes:
    return _render_pdf(_report_lines(report))


def generate_opportunity_brief_pdf(brief: Mapping[str, Any]) -> bytes:
    return _render_pdf(_brief_lines(brief))
