import httpx
import pytest

from app.core.config import get_settings
from app.services.ingestion.sam_gov import SamGovAdapter
from app.worker import sanitize_job_error


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


def test_worker_error_sanitizer_redacts_query_secrets():
    message = sanitize_job_error(
        "Client error for https://example.test/path?api_key=SAM-test-secret-value&token=abc123 with Bearer secret-token"
    )

    assert "SAM-test-secret-value" not in message
    assert "abc123" not in message
    assert "secret-token" not in message
    assert "api_key=[REDACTED]" in message


def test_sam_gov_adapter_redacts_api_key_on_rate_limit(monkeypatch):
    monkeypatch.setenv("SAM_GOV_API_KEY", "SAM-test-secret-value")
    get_settings.cache_clear()

    def handler(request):
        assert "SAM-test-secret-value" in str(request.url)
        return httpx.Response(429, request=request, json={"error": "too many requests"})

    real_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )

    with pytest.raises(RuntimeError) as excinfo:
        SamGovAdapter().fetch({"limit": 10, "source_limit": 10, "keyword_queries": ["substation"]})

    message = str(excinfo.value)
    assert "rate limit" in message.lower()
    assert "SAM-test-secret-value" not in message

    get_settings.cache_clear()
