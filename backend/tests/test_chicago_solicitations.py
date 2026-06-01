import httpx

from app.services.ingestion.chicago_solicitations import ChicagoSolicitationsAdapter


def test_chicago_solicitations_adapter_extracts_matching_open_rows(monkeypatch):
    html = """
    <table id="resultstable">
      <tbody>
        <tr>
          <td>CTA</td>
          <td>IFB</td>
          <td>C25</td>
          <td>High voltage electric repair and maintenance services</td>
          <td>OPEN</td>
          <td>Construction</td>
          <td data-order="20260721">07/21/2026</td>
          <td><a href="./cta/solicitationdetails/C25">Details</a></td>
        </tr>
        <tr>
          <td>CITY</td>
          <td>RFP</td>
          <td>1300</td>
          <td>Strategic planning services</td>
          <td>ACTIVE</td>
          <td>Professional Services</td>
          <td data-order="20260731">07/31/2026</td>
          <td><a href="./city/solicitationdetails/1300">Details</a></td>
        </tr>
      </tbody>
    </table>
    """

    def handler(request):
        return httpx.Response(200, text=html)

    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handler)))

    records = ChicagoSolicitationsAdapter().fetch({"limit": 5, "due_after": "2026-06-01"})

    assert len(records) == 1
    assert records[0]["title"] == "High voltage electric repair and maintenance services"
    assert records[0]["agency"] == "Chicago Transit Authority"
    assert records[0]["source"] == "chicago_solicitations"
    assert records[0]["source_url"] == "https://webapps1.chicago.gov/vcsearch/prtf/cta/solicitationdetails/C25"
