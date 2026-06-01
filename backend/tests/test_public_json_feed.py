import httpx

from app.services.ingestion.public_json_feed import PublicJsonFeedAdapter


def test_public_json_feed_adapter_normalizes_records(monkeypatch):
    payload = {
        "items": [
            {
                "title": "County substation transformer replacement",
                "owner": {"name": "Example County Public Works"},
                "state": "TX",
                "dates": {"close": "2026-07-01"},
                "description": "Open bid for substation transformer replacement, high voltage testing, and performance bond.",
                "estimated_value": "$8,000,000",
                "url": "https://example.gov/bid/1",
            }
        ]
    }

    def handler(request):
        return httpx.Response(200, json=payload)

    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda timeout: real_client(transport=httpx.MockTransport(handler)))

    records = PublicJsonFeedAdapter().fetch(
        {
            "url": "https://example.gov/feed",
            "source_type": "state_local",
            "mapping": {"agency": "owner.name", "due_date": "dates.close"},
        }
    )

    assert len(records) == 1
    assert records[0]["agency"] == "Example County Public Works"
    assert records[0]["source_type"] == "state_local"
    assert records[0]["bid_status"] == "open"
    assert records[0]["estimated_value"] == 8_000_000


def test_public_json_feed_adapter_supports_official_portal_configs(monkeypatch):
    payload = [
        {
            "rampid": "230001",
            "title": "Underground conduit and substructure construction",
            "stagename": "Open",
            "category": "Construction",
            "type": "IFB - Invitation for Bid",
            "bidpost": "2026-05-20T00:00:00.000",
            "closedate": "2026-06-20T21:00:00.000",
            "department": "Water & Power",
            "url": {"url": "https://www.rampla.org/s/opportunity-details?id=006-test"},
        },
        {
            "rampid": "230002",
            "title": "Office supplies",
            "stagename": "Open",
            "category": "Commodity",
            "type": "RFQ",
            "closedate": "2026-06-20T21:00:00.000",
            "department": "General Services",
            "url": {"url": "https://www.rampla.org/s/opportunity-details?id=007-test"},
        },
    ]

    def handler(request):
        assert "%24limit=100" in str(request.url)
        return httpx.Response(200, json=payload)

    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda timeout: real_client(transport=httpx.MockTransport(handler)))

    records = PublicJsonFeedAdapter().fetch(
        {
            "url": "https://data.lacity.org/resource/hf3r-utnq.json",
            "source": "la_ramp",
            "source_type": "state_local",
            "location": "Los Angeles, CA",
            "state": "CA",
            "agency_prefix": "Los Angeles RAMP",
            "source_limit": 100,
            "mapping": {
                "title": "title",
                "agency": "department",
                "due_date": "closedate",
                "bid_status": "stagename",
                "source_url": "url.url",
            },
            "keyword_fields": ["title", "category", "type"],
            "keywords": ["underground conduit"],
            "status_allow": ["open"],
        }
    )

    assert len(records) == 1
    assert records[0]["source"] == "la_ramp"
    assert records[0]["agency"] == "Los Angeles RAMP - Water & Power"
    assert records[0]["state"] == "CA"
    assert records[0]["source_url"] == "https://www.rampla.org/s/opportunity-details?id=006-test"
