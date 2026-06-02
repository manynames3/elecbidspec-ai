import httpx

from app.core.config import get_settings
from app.services.ingestion.sam_gov import SamGovAdapter


def test_sam_gov_adapter_filters_unrelated_notices(monkeypatch):
    monkeypatch.setenv("SAM_GOV_API_KEY", "test-key")
    get_settings.cache_clear()

    payload = {
        "opportunitiesData": [
            {
                "title": "Medium voltage cable and substation repair",
                "description": "Replace transformer feeders and conduit at utility yard.",
                "responseDeadLine": "2026-07-10",
                "uiLink": "https://sam.gov/opp/1",
                "active": "Yes",
            },
            {
                "title": "Snow removal services",
                "description": "Winter grounds maintenance.",
                "responseDeadLine": "2026-07-11",
                "uiLink": "https://sam.gov/opp/2",
                "active": "Yes",
            },
        ]
    }

    def handler(request):
        return httpx.Response(200, json=payload)

    real_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )

    records = SamGovAdapter().fetch(
        {
            "limit": 10,
            "source_limit": 10,
            "keywords": ["medium voltage", "substation", "conduit"],
            "require_keywords": True,
        }
    )

    assert len(records) == 1
    assert records[0]["title"] == "Medium voltage cable and substation repair"
    assert records[0]["source_url"] == "https://sam.gov/opp/1"

    get_settings.cache_clear()
