from datetime import datetime, timedelta, timezone

import httpx

from app.services.ingestion.nypa import NypaAdapter


def test_nypa_adapter_normalizes_public_utility_bids(monkeypatch):
    future_due_date = (datetime.now(timezone.utc) + timedelta(days=10)).replace(microsecond=0)
    payload = [
        {
            "rfqid": 6504,
            "rfqName": "BROWN PORCELAIN INSULATORS",
            "postDate": "2026-05-05T00:00:00",
            "bidDueDate": future_due_date.isoformat(),
            "rfqNumber": "B26-10384135AP",
            "facilityName": "Blenheim-Gilboa",
            "categoryName": "Utilities & Green Energies",
            "statusText": "Open",
            "buyer": "Annastacia Peterson",
            "aribaBid": True,
            "nercCipBid": False,
        }
    ]

    def handler(request):
        assert request.headers["Ocp-Apim-Subscription-Key"] == "test-key"
        return httpx.Response(200, json=payload)

    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handler)))

    records = NypaAdapter().fetch({"api_subscription_key": "test-key"})

    assert len(records) == 1
    assert records[0]["source"] == "nypa"
    assert records[0]["source_type"] == "utility"
    assert records[0]["agency"] == "New York Power Authority"
    assert records[0]["bid_status"] == "open"
