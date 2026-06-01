from __future__ import annotations

from datetime import date, datetime
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.classification import classify_bid
from app.services.extraction import extract_specs
from app.services.ingestion.base import IngestionAdapter


def parse_sam_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _get_nested(data: dict, path: list[str]) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def normalize_sam_notice(notice: dict[str, Any]) -> dict[str, Any]:
    place = notice.get("placeOfPerformance") or {}
    state = _get_nested(place, ["state", "code"]) or _get_nested(place, ["state", "name"])
    city = _get_nested(place, ["city", "name"]) or _get_nested(place, ["city", "code"])
    location = ", ".join(part for part in [city, state] if part)
    description = notice.get("description") or notice.get("typeOfSetAsideDescription") or ""
    title = notice.get("title") or "Untitled SAM.gov opportunity"
    specs = extract_specs(f"{title}. {description}")
    classification = classify_bid(title, description, specs)

    attachments = []
    for link in notice.get("resourceLinks") or []:
        attachments.append({"name": "SAM.gov attachment", "url": link})

    return {
        "title": title,
        "agency": notice.get("fullParentPathName") or notice.get("department/indAgency"),
        "location": location or None,
        "state": str(state).upper()[:2] if state else None,
        "due_date": parse_sam_date(notice.get("responseDeadLine")),
        "naics_code": str(notice.get("naicsCode")) if notice.get("naicsCode") else None,
        "description": description,
        "source": "sam_gov",
        "source_type": "federal",
        "source_url": notice.get("uiLink") or notice.get("link"),
        "bid_status": "open",
        "estimated_value": None,
        "attachments": attachments,
        "extracted_specs": specs,
        "project_type": classification["project_type"],
        "confidence_score": classification["confidence_score"],
        "classification_explanation": classification["explanation"],
    }


class SamGovAdapter(IngestionAdapter):
    name = "sam_gov"
    description = "SAM.gov federal Contract Opportunities API adapter."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        settings = get_settings()
        api_key = params.get("api_key") or settings.sam_gov_api_key
        if not api_key:
            raise ValueError("SAM_GOV_API_KEY is required for live SAM.gov ingestion.")

        request_params = {
            "api_key": api_key,
            "limit": params.get("limit", 25),
            "postedFrom": params.get("posted_from"),
            "postedTo": params.get("posted_to"),
            "ptype": params.get("ptype", "o"),
            "ncode": params.get("naics_code"),
            "keyword": params.get("keyword", "electrical cable OR substation OR conduit"),
        }
        request_params = {key: value for key, value in request_params.items() if value}
        with httpx.Client(timeout=30) as client:
            response = client.get(settings.sam_gov_api_base_url, params=request_params)
            response.raise_for_status()
            payload = response.json()

        notices = payload.get("opportunitiesData") or payload.get("data") or []
        return [normalize_sam_notice(notice) for notice in notices]
