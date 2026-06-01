import httpx

from app.services.ingestion.nyc_city_record import NycCityRecordAdapter


def test_nyc_city_record_adapter_filters_and_normalizes_electrical_notices(monkeypatch):
    payload = [
        {
            "request_id": "20260514007",
            "agency_name": "School Construction Authority",
            "short_title": "Low Voltage Electrical Systems / Flood Elimination / Roofs / Ansul Systems",
            "due_date": "2026-06-04T10:30:00.000",
            "category_description": "Construction/Construction Services",
            "selection_method_description": "Competitive Sealed Bids",
            "additional_description_1": "<p>Bid opening for low voltage electrical systems and flood elimination.</p>",
            "pin": "SCA26-026783-1",
            "email": "jkalin@nycsca.org",
        },
        {
            "request_id": "20260521016",
            "agency_name": "Brooklyn Bridge Park",
            "short_title": "Electronic Bid Submission Advisory Services",
            "due_date": "2026-07-01T16:00:00.000",
            "category_description": "Human Services/Client Services",
            "selection_method_description": "Request for Proposals",
            "additional_description_1": "<p>Portfolio advisory services with electronic proposal submission.</p>",
        },
    ]

    def handler(request):
        assert "due_date" in str(request.url)
        return httpx.Response(200, json=payload)

    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handler)))

    records = NycCityRecordAdapter().fetch({"limit": 5, "due_after": "2026-06-01"})

    assert len(records) == 1
    assert records[0]["title"] == "Low Voltage Electrical Systems / Flood Elimination / Roofs / Ansul Systems"
    assert records[0]["source"] == "nyc_city_record"
    assert records[0]["source_url"] == "https://a856-cityrecord.nyc.gov/RequestDetail/20260514007"
    assert records[0]["state"] == "NY"
    assert records[0]["bid_status"] == "open"
