import httpx

from app.services.ingestion.public_html_scrape import PublicHtmlScrapeAdapter


def test_public_html_scrape_adapter_extracts_listing_and_detail(monkeypatch):
    listing_html = """
    <html>
      <body>
        <article class="bid-card">
          <a class="notice-link" href="/bids/1">Substation relay and transformer upgrade</a>
          <span class="agency">Example City Public Works</span>
          <span class="due">2026-07-20</span>
        </article>
      </body>
    </html>
    """
    detail_html = """
    <html>
      <body>
        <main>
          <p class="scope">Open public bid for substation transformer replacement, medium voltage cable, and performance bond.</p>
          <span class="value">$8.5M</span>
          <span class="state">TX</span>
        </main>
      </body>
    </html>
    """

    def handler(request):
        if str(request.url).endswith("/bids/1"):
            return httpx.Response(200, text=detail_html)
        return httpx.Response(200, text=listing_html)

    real_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **{key: value for key, value in kwargs.items() if key != "headers"}),
    )

    records = PublicHtmlScrapeAdapter().fetch(
        {
            "url": "https://example.gov/procurement",
            "record_selector": "article.bid-card",
            "field_selectors": {
                "title": "a.notice-link",
                "source_url": "a.notice-link@href",
                "agency": ".agency",
                "due_date": ".due",
            },
            "detail_field_selectors": {
                "description": ".scope",
                "estimated_value": ".value",
                "state": ".state",
            },
        }
    )

    assert len(records) == 1
    assert records[0]["title"] == "Substation relay and transformer upgrade"
    assert records[0]["source"] == "public_html_scrape"
    assert records[0]["source_url"] == "https://example.gov/bids/1"
    assert records[0]["estimated_value"] == 8_500_000
    assert records[0]["state"] == "TX"
    assert records[0]["bid_status"] == "open"
