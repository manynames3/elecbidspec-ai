from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any

import boto3
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


def _sam_date(value: Any, fallback: date) -> str:
    if isinstance(value, date):
        return value.strftime("%m/%d/%Y")
    if isinstance(value, str) and value.strip():
        parsed = parse_sam_date(value)
        if parsed:
            return parsed.strftime("%m/%d/%Y")
        return value
    return fallback.strftime("%m/%d/%Y")


def _get_nested(data: dict, path: list[str]) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


@lru_cache(maxsize=4)
def _api_key_from_secret(secret_arn: str) -> str | None:
    if not secret_arn:
        return None
    response = boto3.client("secretsmanager").get_secret_value(SecretId=secret_arn)
    secret_string = response.get("SecretString")
    if not secret_string:
        return None
    try:
        payload = json.loads(secret_string)
    except json.JSONDecodeError:
        return secret_string
    if isinstance(payload, dict):
        for key in ("SAM_GOV_API_KEY", "SAM_API_KEY", "api_key", "key"):
            value = payload.get(key)
            if value:
                return str(value)
    return None


def resolve_sam_api_key(params: dict[str, Any] | None = None) -> str | None:
    params = params or {}
    settings = get_settings()
    direct_key = params.get("api_key") or settings.sam_gov_api_key
    if direct_key:
        return str(direct_key)
    secret_arn = params.get("api_key_secret_arn") or settings.sam_gov_api_key_secret_arn
    if secret_arn:
        return _api_key_from_secret(str(secret_arn))
    return None


def sanitize_sam_error(message: str) -> str:
    message = re.sub(r"([?&]api_key=)[^&\s'\"]+", r"\1[REDACTED]", message)
    message = re.sub(r"(SAM-[A-Za-z0-9-]+)", "[REDACTED]", message)
    return message


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
        "bid_status": "open" if str(notice.get("active") or "").lower() in {"yes", "true", "active", ""} else "closed",
        "estimated_value": None,
        "attachments": attachments,
        "extracted_specs": specs,
        "project_type": classification["project_type"],
        "confidence_score": classification["confidence_score"],
        "classification_explanation": classification["explanation"],
    }


def _matches_keywords(record: dict[str, Any], keywords: list[str]) -> bool:
    if not keywords:
        return True
    search_text = " ".join(
        str(value or "")
        for value in [
            record.get("title"),
            record.get("agency"),
            record.get("description"),
            record.get("naics_code"),
            record.get("project_type"),
        ]
    ).lower()
    return any(keyword.lower() in search_text for keyword in keywords)


class SamGovAdapter(IngestionAdapter):
    name = "sam_gov"
    description = "SAM.gov federal Contract Opportunities API adapter."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        settings = get_settings()
        api_key = resolve_sam_api_key(params)
        if not api_key:
            raise ValueError("SAM_GOV_API_KEY or SAM_GOV_API_KEY_SECRET_ARN is required for live SAM.gov ingestion.")

        limit = int(params.get("limit") or 25)
        source_limit = int(params.get("source_limit") or limit)
        keywords = [str(keyword).strip() for keyword in (params.get("keywords") or []) if str(keyword).strip()]
        require_keywords = bool(params.get("require_keywords", bool(keywords)))
        query_pause_seconds = float(params.get("query_pause_seconds") or 0)
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        keyword_queries = [str(keyword).strip() for keyword in (params.get("keyword_queries") or []) if str(keyword).strip()]
        if not keyword_queries:
            keyword_queries = [str(params.get("keyword") or "electrical cable OR substation OR conduit")]
        base_request_params = {
            "api_key": api_key,
            "limit": source_limit,
            "postedFrom": _sam_date(params.get("posted_from"), date.today() - timedelta(days=int(params.get("posted_window_days") or 60))),
            "postedTo": _sam_date(params.get("posted_to"), date.today()),
            "ptype": params.get("ptype", "o"),
            "ncode": params.get("naics_code"),
            "status": params.get("status", "active"),
        }
        base_request_params = {key: value for key, value in base_request_params.items() if value}
        with httpx.Client(timeout=30) as client:
            for index, keyword_query in enumerate(keyword_queries):
                if query_pause_seconds and index > 0:
                    time.sleep(query_pause_seconds)
                request_params = {**base_request_params, "keyword": keyword_query}
                response = client.get(settings.sam_gov_api_base_url, params=request_params)
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code == 429:
                        if records:
                            return records
                        raise RuntimeError("SAM.gov rate limit reached; retry this source later.") from exc
                    raise RuntimeError(sanitize_sam_error(str(exc))) from exc
                payload = response.json()
                notices = payload.get("opportunitiesData") or payload.get("data") or []
                for notice in notices:
                    record = normalize_sam_notice(notice)
                    key = record.get("source_url") or record.get("title")
                    if not key or key in seen:
                        continue
                    if require_keywords and not _matches_keywords(record, keywords):
                        continue
                    seen.add(str(key))
                    records.append(record)
                    if len(records) >= limit:
                        return records
        return records
