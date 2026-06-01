from __future__ import annotations

from datetime import date, datetime
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.classification import classify_bid
from app.services.extraction import extract_specs
from app.services.ingestion.base import IngestionAdapter
from app.services.value_assessment import normalize_bid_status

NYPA_BIDS_API_URL = "https://api.nypa.gov/rfq/v1/api/public/rfq/Bids"
NYPA_PUBLIC_RFP_URL = "https://rfp.nypa.gov/"


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


class NypaAdapter(IngestionAdapter):
    name = "nypa"
    description = "New York Power Authority public RFQ/RFP adapter."

    def fetch(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        settings = get_settings()
        api_key = params.get("api_subscription_key") or settings.nypa_api_subscription_key
        if not api_key:
            raise ValueError("NYPA_API_SUBSCRIPTION_KEY is required for NYPA utility ingestion.")

        limit = int(params.get("limit") or 25)
        request_params = {
            "statusText": params.get("status_text") or "Open",
            "userAdminSite": params.get("user_admin_site") or "",
            "postDateMinimum": params.get("post_date_minimum") or "",
        }
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(
                params.get("url") or NYPA_BIDS_API_URL,
                params=request_params,
                headers={"Ocp-Apim-Subscription-Key": api_key},
            )
            response.raise_for_status()
            records = response.json()

        opportunities: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            title = record.get("rfqName")
            if not title:
                continue
            due_date = _parse_date(record.get("bidDueDate"))
            facility = str(record.get("facilityName") or record.get("adminFacilityName") or "").strip()
            description = "\n".join(
                part
                for part in [
                    f"RFQ number: {record.get('rfqNumber')}" if record.get("rfqNumber") else "",
                    f"Category: {record.get('categoryName')}" if record.get("categoryName") else "",
                    f"Facility: {facility}" if facility else "",
                    f"Buyer: {record.get('buyer')}" if record.get("buyer") else "",
                    f"NERC CIP bid: {record.get('nercCipBid')}" if record.get("nercCipBid") is not None else "",
                    f"Ariba bid: {record.get('aribaBid')}" if record.get("aribaBid") is not None else "",
                ]
                if part
            )
            specs = extract_specs(f"{title}. {description}")
            classification = classify_bid(str(title), description, specs)
            opportunities.append(
                {
                    "title": str(title),
                    "agency": "New York Power Authority",
                    "location": facility or "New York",
                    "state": "NY",
                    "due_date": due_date,
                    "naics_code": None,
                    "description": description,
                    "source": self.name,
                    "source_type": "utility",
                    "source_url": NYPA_PUBLIC_RFP_URL,
                    "bid_status": normalize_bid_status(record.get("statusText") or "open", due_date),
                    "estimated_value": None,
                    "attachments": [],
                    "extracted_specs": specs,
                    "project_type": classification["project_type"],
                    "confidence_score": classification["confidence_score"],
                    "classification_explanation": classification["explanation"],
                }
            )
            if len(opportunities) >= limit:
                break
        return opportunities
