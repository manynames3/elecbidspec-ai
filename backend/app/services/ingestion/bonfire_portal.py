from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urljoin

import httpx

from app.services.classification import classify_bid
from app.services.extraction import extract_specs, normalize_text
from app.services.ingestion.base import IngestionAdapter
from app.services.value_assessment import normalize_bid_status

DEFAULT_ENDPOINT = "/PublicPortal/getOpenPublicOpportunitiesSectionData"


def _parse_bonfire_date(value: str | None):
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:19], fmt).date()
        except ValueError:
            continue
    return None


def _parse_value(record: dict[str, Any]) -> Decimal | None:
    for key in ("Budget", "EstimatedBudget", "EstimatedValue", "Value"):
        raw = record.get(key)
        if raw in (None, ""):
            continue
        try:
            return Decimal(str(raw).replace("$", "").replace(",", ""))
        except Exception:
            continue
    return None


class BonfirePortalAdapter(IngestionAdapter):
    name = "bonfire_portal"
    description = "Public Bonfire portal adapter using the open-opportunities JSON endpoint."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        portal_url = str(params.get("portal_url") or params.get("url") or "").strip()
        if not portal_url:
            raise ValueError("bonfire_portal requires params.portal_url or params.url")

        source = params.get("source") or params.get("job_label") or "bonfire_portal"
        source_type = params.get("source_type") or "state_local"
        agency = params.get("agency") or params.get("label") or source
        state = params.get("state")
        location = params.get("location")
        limit = int(params.get("limit") or 25)
        source_limit = int(params.get("source_limit") or 250)
        keywords = [str(keyword).lower() for keyword in (params.get("keywords") or []) if str(keyword).strip()]

        endpoint = str(params.get("endpoint") or DEFAULT_ENDPOINT)
        if endpoint.startswith("http"):
            endpoint_url = endpoint
        else:
            endpoint_url = urljoin(portal_url, endpoint)

        headers = {
            "User-Agent": params.get("user_agent") or "Mozilla/5.0 ElecBidSpecAI/0.1 bonfire",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": portal_url,
        }
        with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
            client.get(portal_url)
            response = client.get(endpoint_url)
            response.raise_for_status()
            payload = response.json()

        projects = payload.get("payload", {}).get("projects", {})
        if isinstance(projects, dict):
            rows = list(projects.values())
        elif isinstance(projects, list):
            rows = projects
        else:
            rows = []

        opportunities: list[dict[str, Any]] = []
        for record in rows[:source_limit]:
            title = normalize_text(str(record.get("ProjectName") or record.get("Name") or ""))
            if not title:
                continue
            reference = normalize_text(str(record.get("ReferenceID") or record.get("ProjectID") or ""))
            combined = f"{title} {reference}".lower()
            if keywords and not any(keyword in combined for keyword in keywords):
                continue

            project_id = str(record.get("ProjectID") or "").strip()
            source_url = params.get("source_url")
            if not source_url:
                source_url = f"{portal_url.split('?')[0].rstrip('/')}/?tab=openOpportunities"
                if project_id:
                    source_url = f"{source_url}&projectId={project_id}"

            due_date = _parse_bonfire_date(record.get("DateClose"))
            description = normalize_text(
                "\n".join(
                    item
                    for item in [
                        f"Reference: {reference}" if reference else "",
                        f"Bonfire project ID: {project_id}" if project_id else "",
                        f"Department ID: {record.get('DepartmentID')}" if record.get("DepartmentID") else "",
                        f"Public portal: {portal_url}",
                    ]
                    if item
                )
            )
            specs = extract_specs(f"{title}. {description}")
            classification = classify_bid(title, description, specs)
            opportunities.append(
                {
                    "title": title[:280],
                    "agency": agency,
                    "location": location,
                    "state": str(state)[:2].upper() if state else None,
                    "due_date": due_date,
                    "naics_code": None,
                    "description": description,
                    "source": source,
                    "source_type": source_type,
                    "source_url": str(source_url),
                    "bid_status": normalize_bid_status("open", due_date),
                    "estimated_value": _parse_value(record),
                    "attachments": [{"name": reference or title, "url": str(source_url), "source": "bonfire_portal"}],
                    "extracted_specs": specs,
                    "project_type": classification["project_type"],
                    "confidence_score": classification["confidence_score"],
                    "classification_explanation": classification["explanation"],
                }
            )
            if len(opportunities) >= limit:
                break
        return opportunities
