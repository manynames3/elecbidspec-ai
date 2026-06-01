from __future__ import annotations

from typing import Any

DEFAULT_ELECTRICAL_SOURCE_KEYWORDS = [
    "electrical",
    "electric",
    "electrical systems",
    "electrical installations",
    "electric work",
    "battery electric",
    "battery-electric",
    "low voltage",
    "medium voltage",
    "high voltage",
    "shore power",
    "power hub",
    "power station",
    "cable",
    "conduit",
    "underground",
    "utility",
    "transformer",
    "substation",
    "switchgear",
    "fire alarm",
    "generator",
    "energization",
    "data center",
    "transmission",
    "distribution",
    "lighting infrastructure",
]

DEFAULT_SOURCE_CATALOG = [
    {
        "source": "sam_gov",
        "label": "SAM.gov",
        "category": "federal",
        "coverage": "Nationwide federal opportunities",
        "adapter": "sam_gov",
        "requires_setting": "sam_gov_api_key",
    },
    {
        "source": "txdot_bid_items",
        "label": "TxDOT",
        "category": "state_dot",
        "coverage": "Texas statewide DOT lettings",
        "adapter": "txdot_bid_items",
    },
    {
        "source": "nypa",
        "label": "NY Power Authority",
        "category": "utility",
        "coverage": "New York utility RFQ/RFPs",
        "adapter": "nypa",
        "requires_setting": "nypa_api_subscription_key",
    },
    {
        "source": "nyc_city_record",
        "label": "NYC City Record",
        "category": "state_local",
        "coverage": "New York City public solicitations",
        "adapter": "nyc_city_record",
    },
    {
        "source": "nyc_school_construction_authority",
        "label": "NYC School Construction",
        "category": "education",
        "coverage": "NYC School Construction Authority solicitations",
        "adapter": "nyc_city_record",
    },
    {
        "source": "la_ramp",
        "label": "Los Angeles RAMP",
        "category": "state_local",
        "coverage": "Los Angeles city/county and LADWP-linked postings",
        "adapter": "public_json_feed",
    },
    {
        "source": "chicago_solicitations",
        "label": "Chicago/CTA",
        "category": "state_local",
        "coverage": "City of Chicago and CTA solicitations",
        "adapter": "chicago_solicitations",
    },
    {
        "source": "sf_open_bids",
        "label": "San Francisco",
        "category": "state_local",
        "coverage": "San Francisco open bid opportunities",
        "adapter": "sf_open_bids",
    },
    {
        "source": "montgomery_md_solicitations",
        "label": "Montgomery County",
        "category": "state_local",
        "coverage": "Montgomery County, MD active solicitations",
        "adapter": "public_json_feed",
    },
]

DEFAULT_PUBLIC_BID_JOBS = [
    {
        "adapter": "sam_gov",
        "requires_setting": "sam_gov_api_key",
        "params": {
            "job_label": "sam_gov",
            "limit": 50,
            "posted_window_days": 90,
            "ptype": "o",
            "status": "active",
            "keyword": "electrical cable OR high voltage OR medium voltage OR substation OR conduit OR transformer",
            "update_existing": True,
        },
    },
    {
        "adapter": "txdot_bid_items",
        "params": {
            "job_label": "txdot_bid_items",
            "limit": 50,
            "source_limit": 5000,
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "update_existing": True,
        },
    },
    {
        "adapter": "nypa",
        "requires_setting": "nypa_api_subscription_key",
        "params": {
            "job_label": "nypa",
            "limit": 50,
            "update_existing": True,
        },
    },
    {
        "adapter": "nyc_city_record",
        "params": {
            "job_label": "nyc_city_record",
            "limit": 25,
            "source_limit": 300,
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "update_existing": True,
        },
    },
    {
        "adapter": "nyc_city_record",
        "params": {
            "job_label": "nyc_school_construction_authority",
            "source": "nyc_school_construction_authority",
            "source_type": "education",
            "limit": 25,
            "source_limit": 300,
            "agency_keywords": ["School Construction Authority"],
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "update_existing": True,
        },
    },
    {
        "adapter": "sf_open_bids",
        "params": {
            "job_label": "sf_open_bids",
            "limit": 25,
            "source_limit": 300,
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "update_existing": True,
        },
    },
    {
        "adapter": "public_json_feed",
        "params": {
            "job_label": "la_ramp",
            "source": "la_ramp",
            "source_type": "state_local",
            "url": "https://data.lacity.org/resource/hf3r-utnq.json",
            "location": "Los Angeles, CA",
            "state": "CA",
            "agency_prefix": "Los Angeles RAMP",
            "limit": 50,
            "source_limit": 500,
            "order": "closedate ASC",
            "query_params": {
                "$where": "stagename in('Open', 'Amended')",
            },
            "mapping": {
                "title": "title",
                "agency": "department",
                "due_date": "closedate",
                "bid_status": "stagename",
                "source_url": "url.url",
            },
            "description_template": (
                "RAMP ID: {rampid}\n"
                "Department: {department}\n"
                "Category: {category}\n"
                "Type: {type}\n"
                "Status: {stagename}\n"
                "Open date: {bidpost}"
            ),
            "keyword_fields": ["title", "category", "type"],
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "status_allow": ["open", "amended"],
            "update_existing": True,
        },
    },
    {
        "adapter": "public_json_feed",
        "params": {
            "job_label": "montgomery_md_solicitations",
            "source": "montgomery_md_solicitations",
            "source_type": "state_local",
            "url": "https://data.montgomerycountymd.gov/resource/eeq6-nnwe.json",
            "location": "Montgomery County, MD",
            "state": "MD",
            "agency_prefix": "Montgomery County, MD",
            "limit": 25,
            "source_limit": 300,
            "order": "closingdate ASC",
            "query_params": {
                "$where": "status = 'Active'",
            },
            "mapping": {
                "title": "description",
                "agency": "department",
                "due_date": "closingdate",
                "bid_status": "status",
            },
            "source_url_template": "https://data.montgomerycountymd.gov/Government/Solicitations/eeq6-nnwe?number={number}",
            "description_template": (
                "Solicitation number: {number}\n"
                "Type: {type}\n"
                "Department: {department}\n"
                "Buyer: {buyer}\n"
                "Department contact: {deptcontact}\n"
                "Construction solicitation: {construction}\n"
                "LSBRP: {lsbrpindicator}"
            ),
            "keyword_fields": ["description", "department", "type"],
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "status_allow": ["active"],
            "update_existing": True,
        },
    },
    {
        "adapter": "chicago_solicitations",
        "params": {
            "job_label": "chicago_solicitations",
            "limit": 25,
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "update_existing": True,
        },
    },
]


def missing_required_setting(settings: Any, job_spec: dict[str, Any]) -> str | None:
    required = job_spec.get("requires_setting")
    if required and not getattr(settings, str(required), None):
        return str(required)
    return None


def available_default_public_bid_jobs(settings: Any) -> list[dict[str, Any]]:
    return [job for job in DEFAULT_PUBLIC_BID_JOBS if missing_required_setting(settings, job) is None]


def skipped_default_public_bid_jobs(settings: Any) -> list[dict[str, Any]]:
    return [job for job in DEFAULT_PUBLIC_BID_JOBS if missing_required_setting(settings, job) is not None]
