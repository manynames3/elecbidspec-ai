import json

import httpx

from app.services.ingestion.public_bid_page import PublicBidPageAdapter


def _mock_client(monkeypatch, handler):
    real_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(
            transport=httpx.MockTransport(handler),
            **{key: value for key, value in kwargs.items() if key != "headers"},
        ),
    )


def test_public_bid_page_extracts_column_mapped_table_rows(monkeypatch):
    html = """
    <table>
      <tr><th>TRACS #</th><th>Project</th><th>Bid Opening</th><th>Type of Work</th></tr>
      <tr>
        <td><a href="/projects/T058801C">T058801C</a></td>
        <td>SUR-0-(237)T</td>
        <td>07/10/2026</td>
        <td>Conduit, Pull Boxes &amp; Fiber Optic Cable</td>
      </tr>
    </table>
    """

    def handler(request):
        return httpx.Response(200, text=html)

    _mock_client(monkeypatch, handler)

    records = PublicBidPageAdapter().fetch(
        {
            "url": "https://example.gov/current",
            "source": "az_dot",
            "source_type": "state_dot",
            "agency": "ADOT",
            "state": "AZ",
            "candidate_selectors": ["tr"],
            "title_column": 3,
            "due_date_column": 2,
            "source_url_column": 0,
            "title_template": "ADOT {col0}: {col3}",
            "keywords": ["conduit", "fiber", "cable"],
            "require_keywords": True,
            "require_procurement_terms": False,
        }
    )

    assert len(records) == 1
    assert records[0]["title"] == "ADOT T058801C: Conduit, Pull Boxes & Fiber Optic Cable"
    assert records[0]["source_url"] == "https://example.gov/projects/T058801C"
    assert records[0]["due_date"].isoformat() == "2026-07-10"
    assert records[0]["state"] == "AZ"


def test_public_bid_page_extracts_json_embedded_html_tables(monkeypatch):
    payload = {
        "items": {
            "text": """
            <table>
              <tr><th>Contract</th><th>Due Date</th><th>Description</th></tr>
              <tr>
                <td><a href="/ads/JFK-100.pdf">JFK-100</a></td>
                <td>16-Jun-2026</td>
                <td>Airport electrical substation and medium voltage cable upgrade</td>
              </tr>
            </table>
            """
        }
    }

    def handler(request):
        return httpx.Response(200, text=json.dumps(payload))

    _mock_client(monkeypatch, handler)

    records = PublicBidPageAdapter().fetch(
        {
            "url": "https://example.gov/model.json",
            "source": "port_authority_ny_nj",
            "source_type": "airport_authority",
            "agency": "Port Authority NY/NJ",
            "state": "NY",
            "parse_json_html": True,
            "json_html_fields": ["text"],
            "candidate_selectors": ["tr"],
            "title_column": 2,
            "due_date_column": 1,
            "source_url_column": 0,
            "title_template": "PANYNJ {col0}: {col2}",
            "keywords": ["substation", "medium voltage", "cable"],
            "require_keywords": True,
            "require_procurement_terms": False,
        }
    )

    assert len(records) == 1
    assert records[0]["title"].startswith("PANYNJ JFK-100")
    assert records[0]["source_url"] == "https://example.gov/ads/JFK-100.pdf"
    assert records[0]["due_date"].isoformat() == "2026-06-16"
    assert records[0]["project_type"] == "substation_related"
