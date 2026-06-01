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
