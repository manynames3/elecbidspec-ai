import httpx

from app.services.ingestion.jea_procurement import JeaProcurementAdapter


def test_jea_procurement_groups_documents_by_solicitation(monkeypatch):
    html = """
    <html><body>
      <a href="/About/Procurement/Formal_Procurement_Opportunities/1412175446_Solicitation/">1412175446 Solicitation</a>
      <a href="/About/Procurement/Formal_Procurement_Opportunities/1412175446_Appendix_A_-_Technical_Specifications/">1412175446 Appendix A - Technical Specifications</a>
      <a href="/About/Procurement/Formal_Procurement_Opportunities/1412175446_Attachment_C_-_All_Approved_Transformer_Manufacturers_2026/">1412175446 Attachment C - All Approved Transformer Manufacturers_2026</a>
      <a href="/About/Procurement/Formal_Procurement_Opportunities/1412170000_Solicitation/">1412170000 Solicitation</a>
    </body></html>
    """

    def handler(request):
        return httpx.Response(200, text=html)

    real_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **{key: value for key, value in kwargs.items() if key != "headers"}),
    )

    records = JeaProcurementAdapter().fetch(
        {
            "url": "https://www.jea.com/about/procurement/formal_procurement_opportunities/?ns=y",
            "source": "jea",
            "keywords": ["transformer"],
        }
    )

    assert len(records) == 1
    assert records[0]["title"] == "JEA 1412175446 Solicitation"
    assert records[0]["source"] == "jea"
    assert len(records[0]["attachments"]) == 3
    assert "transformer" in records[0]["extracted_specs"]["keywords"]
