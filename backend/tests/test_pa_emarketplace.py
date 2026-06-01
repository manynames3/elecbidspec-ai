import httpx

from app.services.ingestion.pa_emarketplace import PennsylvaniaEMarketplaceAdapter


def test_pa_emarketplace_adapter_extracts_electrical_rows(monkeypatch):
    html = """
    <html><body>
      <table>
        <tr class="GridItem">
          <td headers="ColumnHeader_Solicitation #,RowHeader_6100066200">
            <a href="../Solicitations.aspx?SID=6100066200">6100066200</a>
          </td>
          <td headers="ColumnHeader_Types,RowHeader_6100066200">IFB</td>
          <td headers="ColumnHeader_Solicitation Title,RowHeader_6100066200">Medium Voltage Cable Replacement</td>
          <td headers="ColumnHeader_Description,RowHeader_6100066200">
            Furnish underground conduit, medium voltage cable, transformer terminations, and performance bond.
          </td>
          <td headers="ColumnHeader_Agency,RowHeader_6100066200">Department of General Services</td>
          <td headers="ColumnHeader_County,RowHeader_6100066200">Dauphin</td>
          <td headers="ColumnHeader_Solicitation Due Date,RowHeader_6100066200">7/15/2026 2:00:00 PM</td>
          <td headers="ColumnHeader_Status,RowHeader_6100066200">Open</td>
          <td headers="ColumnHeader_Contact Person,RowHeader_6100066200">Alex Buyer</td>
        </tr>
        <tr class="GridAltItem">
          <td headers="ColumnHeader_Solicitation #,RowHeader_6100066201"><a href="../Solicitations.aspx?SID=6100066201">6100066201</a></td>
          <td headers="ColumnHeader_Solicitation Title,RowHeader_6100066201">Office supplies</td>
          <td headers="ColumnHeader_Description,RowHeader_6100066201">Paper and toner.</td>
          <td headers="ColumnHeader_Status,RowHeader_6100066201">Open</td>
        </tr>
      </table>
    </body></html>
    """

    def handler(request):
        return httpx.Response(200, text=html)

    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handler)))

    records = PennsylvaniaEMarketplaceAdapter().fetch({"limit": 10})

    assert len(records) == 1
    assert records[0]["source"] == "pa_emarketplace"
    assert records[0]["state"] == "PA"
    assert records[0]["agency"] == "Department of General Services"
    assert records[0]["source_url"].endswith("Solicitations.aspx?SID=6100066200")
    assert records[0]["bid_status"] == "open"
