import httpx

from app.services.ingestion.public_portal_links import PublicPortalLinksAdapter


def test_public_portal_links_adapter_extracts_electrical_bid_links(monkeypatch):
    html = """
    <html>
      <body>
        <a href="/docs/substation-transformer-ifb.pdf">IFB - Substation transformer and medium voltage cable upgrade due 07/20/2026 $9M</a>
        <a href="/about">About procurement</a>
      </body>
    </html>
    """

    def handler(request):
        return httpx.Response(200, text=html)

    real_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **{key: value for key, value in kwargs.items() if key != "headers"}),
    )

    records = PublicPortalLinksAdapter().fetch(
        {
            "url": "https://example.gov/procurement",
            "source": "example_portal",
            "source_type": "utility",
            "agency": "Example Public Power",
            "state": "TX",
            "keywords": ["substation", "medium voltage", "cable"],
        }
    )

    assert len(records) == 1
    assert records[0]["title"].startswith("IFB - Substation transformer")
    assert records[0]["source_url"] == "https://example.gov/docs/substation-transformer-ifb.pdf"
    assert records[0]["estimated_value"] == 9_000_000
    assert records[0]["due_date"].isoformat() == "2026-07-20"
    assert records[0]["state"] == "TX"
