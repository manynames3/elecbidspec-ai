from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any

from app.core.config import get_settings


def _line_items(items: list[dict[str, Any]], limit: int = 8) -> list[str]:
    lines = []
    for item in items[:limit]:
        title = item.get("title") or "Untitled opportunity"
        fit = item.get("fit_score")
        due = item.get("due_date") or "no due date"
        source = item.get("source") or "source unknown"
        lines.append(f"- {title} | fit {fit if fit is not None else '--'} | due {due} | {source}")
    return lines


def render_alert_digest_text(digest: dict[str, Any]) -> str:
    counts = digest.get("counts") or {}
    sections = [
        "ElecBidSpec AI daily opportunity digest",
        "",
        f"High-fit matches: {counts.get('high_fit', 0)}",
        f"Due soon: {counts.get('due_soon', 0)}",
        f"Watched: {counts.get('watched', 0)}",
        f"Saved-search matches: {counts.get('saved_search_matches', 0)}",
        f"Source issues: {counts.get('source_failures', 0)}",
        "",
        "High-fit opportunities:",
        *_line_items(digest.get("high_fit") or []),
        "",
        "Due soon:",
        *_line_items(digest.get("due_soon") or []),
    ]
    saved_searches = digest.get("saved_searches") or []
    if saved_searches:
        sections.extend(["", "Saved searches:"])
        for saved_search in saved_searches[:6]:
            sections.append(f"- {saved_search.get('name')}: {len(saved_search.get('matches') or [])} matches")
            for match in (saved_search.get("matches") or [])[:3]:
                opportunity = match.get("opportunity") or {}
                title = opportunity.get("title") or "Untitled opportunity"
                explanation = match.get("search_explanation") or ""
                sections.append(f"  * {title} {f'- {explanation}' if explanation else ''}".strip())
    return "\n".join(sections).strip() + "\n"


def send_alert_digest_email(recipient: str | None, digest: dict[str, Any]) -> dict[str, str | None]:
    settings = get_settings()
    if not recipient:
        return {"status": "complete", "error": None}
    if not settings.smtp_host or not settings.alert_email_from:
        return {"status": "email_unconfigured", "error": "SMTP_HOST and ALERT_EMAIL_FROM are required to send email alerts."}

    message = EmailMessage()
    message["Subject"] = "ElecBidSpec AI daily bid digest"
    message["From"] = settings.alert_email_from
    message["To"] = recipient
    message.set_content(render_alert_digest_text(digest))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username and settings.smtp_password:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    except Exception as exc:  # noqa: BLE001 - persist delivery failure for admin inspection
        return {"status": "email_failed", "error": str(exc)}
    return {"status": "sent", "error": None}
