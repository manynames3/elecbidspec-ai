from __future__ import annotations

DEFAULT_PUBLIC_BID_JOBS = [
    {
        "adapter": "nyc_city_record",
        "params": {
            "limit": 25,
            "source_limit": 300,
            "keywords": [
                "electrical systems",
                "electrical installations",
                "electric work",
                "low voltage",
                "medium voltage",
                "high voltage",
                "shore power",
                "power hub",
                "cable",
                "conduit",
                "transformer",
                "substation",
                "switchgear",
                "fire alarm",
                "energization",
            ],
            "update_existing": True,
        },
    }
]
