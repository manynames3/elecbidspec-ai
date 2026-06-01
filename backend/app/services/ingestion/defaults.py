from __future__ import annotations

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

DEFAULT_PUBLIC_BID_JOBS = [
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
