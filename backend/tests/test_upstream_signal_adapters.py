import io
import zipfile
from xml.sax.saxutils import escape

import httpx

from app.services.ingestion.upstream_signals import (
    CaisoInterconnectionQueueAdapter,
    ErcotCapacityChangesAdapter,
    GeorgiaPscDataCenterAdapter,
    IsoNeInterconnectionQueueAdapter,
    LoudounLandApplicationsAdapter,
    MisoErasInterconnectionAdapter,
    NyisoInterconnectionQueueAdapter,
    PjmProjectConstructionAdapter,
    SppGiActiveRequestsAdapter,
    TexasPucDocketsAdapter,
    VirginiaSccTransmissionCasesAdapter,
)


def _xlsx_bytes(rows_by_sheet: list[list[list[str]]]) -> bytes:
    def col_name(index: int) -> str:
        name = ""
        index += 1
        while index:
            index, remainder = divmod(index - 1, 26)
            name = chr(65 + remainder) + name
        return name

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as workbook:
        for sheet_index, rows in enumerate(rows_by_sheet, start=1):
            row_xml = []
            for row_index, row in enumerate(rows, start=1):
                cells = []
                for column_index, value in enumerate(row):
                    if value == "":
                        continue
                    ref = f"{col_name(column_index)}{row_index}"
                    cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>')
                row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
            workbook.writestr(
                f"xl/worksheets/sheet{sheet_index}.xml",
                (
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                    f'<sheetData>{"".join(row_xml)}</sheetData>'
                    "</worksheet>"
                ),
            )
    return buffer.getvalue()


def _mock_client(monkeypatch, handler):
    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))


def test_pjm_project_construction_adapter_parses_active_upgrade_with_evidence(monkeypatch):
    payload = """<?xml version="1.0" encoding="UTF-8"?>
    <Upgrades>
      <Upgrade>
        <UpgradeId>b1001</UpgradeId>
        <Description>Install 500 kV transformer and substation breakers for load growth</Description>
        <ProjectType>Baseline</ProjectType>
        <Voltage>500</Voltage>
        <CostEstimate>12.5</CostEstimate>
        <TransmissionOwner>Dominion Energy</TransmissionOwner>
        <State>VA</State>
        <Location>Ashburn</Location>
        <Equipment>Transformer</Equipment>
        <Status>Active</Status>
        <Driver>Data center load growth and reliability</Driver>
        <ProjectedInServiceDate>12/1/2028</ProjectedInServiceDate>
        <LastUpdated>6/1/2026</LastUpdated>
      </Upgrade>
      <Upgrade>
        <UpgradeId>b1002</UpgradeId>
        <Description>Completed low-value breaker work</Description>
        <CostEstimate>1</CostEstimate>
        <Status>IS</Status>
      </Upgrade>
    </Upgrades>
    """

    def handler(request):
        return httpx.Response(200, text=payload)

    _mock_client(monkeypatch, handler)

    records = PjmProjectConstructionAdapter().fetch({"limit": 5})

    assert len(records) == 1
    assert records[0]["source_type"] == "rto_iso"
    assert records[0]["signal_type"] == "rto_transmission_plan"
    assert records[0]["owner_type"] == "investor_owned_utility"
    assert records[0]["estimated_value"] == 12_500_000
    assert records[0]["attachments"][0]["type"] == "evidence"


def test_caiso_interconnection_queue_adapter_parses_workbook(monkeypatch):
    workbook = _xlsx_bytes(
        [
            [
                [
                    "Queue Number",
                    "Project Number",
                    "Project Name",
                    "Generation/Fuel 1",
                    "NET MW 1",
                    "Generation/Fuel 2",
                    "NET MW 2",
                    "Generation/Fuel 3",
                    "NET MW 3",
                    "NET MW POI",
                    "PROJECT COUNTY",
                    "Project State",
                    "Study Area",
                    "PTO",
                    "POI",
                    "Voltage kV",
                    "Requested COD",
                    "Queue Date ",
                    "Application Date",
                    "Service Type",
                ],
                ["2207", "54516", "Alisa Solar Energy Complex 2", "Photovoltaic/Solar", "500", "Storage/Battery", "500", "N/A", "N/A", "500", "Yuma", "AZ", "SAN DIEGO", "SDGE", "NORTH GILA 525 kV", "525", "47635", "45700", "45614", "Energy Only Requested"],
            ]
        ]
    )

    def handler(request):
        return httpx.Response(200, content=workbook)

    _mock_client(monkeypatch, handler)

    records = CaisoInterconnectionQueueAdapter().fetch({"limit": 5, "keywords": ["storage"]})

    assert len(records) == 1
    assert records[0]["state"] == "AZ"
    assert records[0]["source_type"] == "rto_iso"
    assert records[0]["owner_type"] == "investor_owned_utility"
    assert "525" in records[0]["description"]
    assert records[0]["attachments"][1]["type"] == "evidence"


def test_ercot_capacity_changes_adapter_discovers_latest_workbook_and_prioritizes_data_center(monkeypatch):
    workbook = _xlsx_bytes(
        [
            [
                ["INR", "Project Name", "County", "Projected COD", "IA Signed", "Fuel", "Technology", "Capacity (MW)"],
                ["25INR0688", "Giga Texas Data Center", "Travis", "46006", "45777", "Battery", "BA", "133"],
                ["26INR0033", "Fairway Storage", "Ward", "46200", "45800", "Battery", "BA", "120"],
            ]
        ]
    )

    def handler(request):
        if ".xlsx" in str(request.url):
            return httpx.Response(200, content=workbook)
        return httpx.Response(200, text='<a href="/files/docs/latest/Capacity-Changes-by-Fuel-Type-Charts_PlannedMonthly.xlsx">Workbook</a>')

    _mock_client(monkeypatch, handler)

    records = ErcotCapacityChangesAdapter().fetch({"limit": 2, "keywords": ["battery", "data center"]})

    assert len(records) == 2
    assert records[0]["title"].startswith("ERCOT planned interconnection 25INR0688")
    assert records[0]["project_type"] == "data_center_power"
    assert records[0]["attachments"][1]["url"].endswith("PlannedMonthly.xlsx")


def test_iso_ne_interconnection_queue_adapter_parses_public_queue_with_evidence_excerpt(monkeypatch):
    html = """
    <table id="publicqueue">
      <thead><tr>
        <th>Cluster</th><th>QP</th><th>Updated</th><th>Type</th><th>Requested</th>
        <th>Alternative Name</th><th>Unit</th><th>Fuel Type</th><th>Net MW</th>
        <th>Summer MW</th><th>Winter MW</th><th>County</th><th>ST</th><th>Op Date</th>
        <th>Sync Date</th><th>W/D Date</th><th>POI</th><th>Serv</th><th>SIS</th><th>I39</th>
        <th>TO Report</th><th>Dev</th><th>Zone</th><th>FS</th><th>SIS</th><th>OS</th>
        <th>FAC</th><th>IA</th><th>Project Status</th><th>Status</th><th>Jurisdiction</th>
      </tr></thead>
      <tbody>
        <tr>
          <td>TCS</td><td>1148</td><td>4/8/2026</td><td>G</td><td>7/13/2021</td>
          <td>Lite Brite Battery Storage</td><td>OT</td><td>BAT</td><td>300</td>
          <td>305.624</td><td>305.624</td><td>Suffolk</td><td>MA</td><td>5/26/2028</td>
          <td>4/30/2028</td><td></td><td>Electric Avenue 115 kV substation</td><td>CNR</td>
          <td>Y</td><td>Y</td><td>Eversource</td><td></td><td>BOST</td><td></td><td></td>
          <td></td><td></td><td></td><td>ISO-NE</td><td>A</td><td>F</td>
        </tr>
        <tr>
          <td>TCS</td><td>1252</td><td>4/8/2026</td><td>G</td><td>4/21/2022</td>
          <td>Withdrawn Battery</td><td>OT</td><td>BAT</td><td>310</td>
          <td>314.7</td><td>314.7</td><td>Essex</td><td>MA</td><td>8/1/2032</td>
          <td>7/1/2032</td><td>12/22/2025</td><td>Ward Hill 345 kV Substation</td>
          <td>CNR</td><td>Y</td><td>Y</td><td>Eversource</td><td></td><td>BOST</td>
          <td></td><td></td><td></td><td></td><td></td><td>PD</td><td>W</td><td>F</td>
        </tr>
      </tbody>
    </table>
    """

    def handler(request):
        return httpx.Response(200, text=html, request=request)

    _mock_client(monkeypatch, handler)

    records = IsoNeInterconnectionQueueAdapter().fetch({"limit": 5, "keywords": ["battery", "115"]})

    assert len(records) == 1
    assert records[0]["source"] == "iso_ne_interconnection_queue"
    assert records[0]["owner_type"] == "investor_owned_utility"
    assert records[0]["forecast_rfp_date"].year == 2027
    assert "ISO-NE public queue row QP 1148" in records[0]["extracted_specs"]["evidence_excerpts"][0]


def test_spp_gi_active_requests_adapter_parses_csv_with_evidence_excerpt(monkeypatch):
    csv_payload = """"Last Updated On",6/2/2026,
Generation Interconnection Number,IFS Queue Number,Current Cluster,Cluster Group, Nearest Town or County,State,TO at POI,In-Service Date,Commercial Operation Date,Cessation Date,Original Generator Commercial Op Date,Capacity,MAX Summer MW,MAX Winter MW,Service Type,Requested Maximum Injection Capability (MW),Requested Network Resource Deliverability (MW),Nameplate Capacity,Generation Type,Fuel Type,Substation or Line,Request Received,Date Withdrawn,Status,JTIQ Participant,JTIQ Commitment,Cause of Delay
"GI-TC-2024-25","","RTOE Transitional Cluster","","Weld County","CO","TSGT","6/2/2031","12/1/2028",,,"350","350","350","ER","0","0","0","Wind","Wind","Ault - Laramie River Station 345 Line","5/28/2024",,"FACILITY STUDY STAGE","","","GIA delayed due to Affected Systems Study"
"GI-LOW-2024-01","","RTOE Transitional Cluster","","County","CO","TSGT","6/2/2031",,,,"10","10","10","ER","0","0","0","Wind","Wind","Low value 115 Substation","5/28/2024",,"FACILITY STUDY STAGE","","",""
"""

    def handler(request):
        return httpx.Response(200, text=csv_payload, request=request)

    _mock_client(monkeypatch, handler)

    records = SppGiActiveRequestsAdapter().fetch({"limit": 5, "keywords": ["345", "wind"]})

    assert len(records) == 1
    assert records[0]["source"] == "spp_gi_active_requests"
    assert records[0]["signal_type"] == "interconnection_queue"
    assert records[0]["state"] == "CO"
    assert "SPP active GI row GI-TC-2024-25" in records[0]["extracted_specs"]["evidence_excerpts"][0]


def test_miso_eras_interconnection_adapter_discovers_workbook_and_parses_large_queue_signal(monkeypatch):
    workbook = _xlsx_bytes(
        [
            [
                [
                    "Project Number",
                    "Application ID",
                    "Interconnection Customer",
                    "Request Status",
                    "Order Submitted",
                    "Date Withdrawn",
                    "Application In Service Date",
                    "Transmission Owner",
                    "County",
                    "State",
                    "Study Cycle",
                    "Service Type",
                    "POI Name",
                    "Max Summer MW",
                    "Max Winter MW",
                    "Fuel Type",
                    "Generating Facility",
                    "Post GIA Status",
                    "Negotiated In Service Date",
                ],
                [
                    "E0012",
                    "A-100",
                    "Red Oak Ridge Energy Center LLC",
                    "In Progress",
                    "05/01/2026",
                    "",
                    "12/31/2028",
                    "Ameren Missouri",
                    "Edgar",
                    "IL",
                    "ERAS Cycle 1",
                    "NRIS",
                    "Paris-Lakeview 345 kV double circuit",
                    "1211.25",
                    "1200",
                    "Gas",
                    "Red Oak Ridge Energy Center",
                    "",
                    "12/31/2028",
                ],
                [
                    "E0099",
                    "A-200",
                    "Withdrawn Solar LLC",
                    "Withdrawn",
                    "05/01/2026",
                    "06/01/2026",
                    "12/31/2028",
                    "MISO TO",
                    "County",
                    "IL",
                    "ERAS Cycle 1",
                    "ERIS",
                    "Substation",
                    "500",
                    "500",
                    "Solar",
                    "Withdrawn Solar",
                    "",
                    "",
                ],
            ]
        ]
    )

    def handler(request):
        if ".xlsx" in str(request.url):
            return httpx.Response(200, content=workbook)
        return httpx.Response(200, text='<a href="https://cdn.misoenergy.org/ERAS%20Interconnection%20Requests718482.xlsx?v=1">Workbook</a>')

    _mock_client(monkeypatch, handler)

    records = MisoErasInterconnectionAdapter().fetch({"limit": 5, "keywords": ["345", "gas"]})

    assert len(records) == 1
    assert records[0]["source"] == "miso_eras_interconnection"
    assert records[0]["source_type"] == "rto_iso"
    assert records[0]["signal_type"] == "interconnection_queue"
    assert records[0]["owner_type"] == "investor_owned_utility"
    assert records[0]["forecast_rfp_date"].year == 2027
    assert records[0]["attachments"][1]["url"].endswith("v=1")


def test_nyiso_interconnection_queue_adapter_discovers_workbook_and_parses_load_signal(monkeypatch):
    workbook = _xlsx_bytes(
        [
            [
                [
                    "Queue Pos.",
                    "Developer/Interconnection Customer",
                    "Project Name",
                    "Date of IR",
                    "SP (MW)",
                    "WP (MW)",
                    "Type/ Fuel",
                    "Energy Storage Capability",
                    "Minimum_Duration Full Discharge",
                    "County",
                    "State",
                    "Z",
                    "Points of Interconnection",
                    "Utility",
                    "Affected Transmission Owner (ATO)",
                    "S",
                    "Last Updated Date",
                    "Availability of Studies",
                    "IA Tender Date",
                    "CY/FS Complete Date",
                    "Proposed In-Service/Initial Backfeed Date",
                    "Proposed Sync Date",
                    "Proposed COD",
                ],
                [
                    "0580",
                    "WNY STAMP",
                    "WNY STAMP Large Load",
                    "04/01/2026",
                    "300",
                    "300",
                    "Load",
                    "",
                    "",
                    "Genesee",
                    "NY",
                    "A",
                    "Kintigh/Niagara - New Rochester 345 kV",
                    "National Grid",
                    "NYPA",
                    "Active",
                    "04/30/2026",
                    "Available",
                    "05/15/2026",
                    "06/15/2026",
                    "12/31/2028",
                    "01/15/2029",
                    "03/01/2029",
                ],
            ]
        ]
    )

    def handler(request):
        if ".xlsx" in str(request.url):
            return httpx.Response(200, content=workbook)
        return httpx.Response(200, text='<a href="/documents/20142/1407078/NYISO-Interconnection-Queue-04302026.xlsx/file?t=1">Workbook</a>', request=request)

    _mock_client(monkeypatch, handler)

    records = NyisoInterconnectionQueueAdapter().fetch({"limit": 5, "keywords": ["load", "345"]})

    assert len(records) == 1
    assert records[0]["source"] == "nyiso_interconnection_queue"
    assert records[0]["source_type"] == "rto_iso"
    assert records[0]["signal_type"] == "interconnection_queue"
    assert records[0]["owner_type"] == "investor_owned_utility"
    assert records[0]["forecast_rfp_date"].year == 2027
    assert "345 kV" in records[0]["description"]
    assert records[0]["attachments"][1]["url"].startswith("https://www.nyiso.com/documents/")


def test_virginia_scc_transmission_cases_adapter_parses_cpcn_cases(monkeypatch):
    html = """
    <h2>Recent transmission line cases sorted by region:</h2>
    <div>NORTHERN VIRGINIA</div>
    <ul>
      <li>Dominion Energy Virginia
        <ul>
          <li><a href="/docketsearch#/caseDetails/145902">PUR-2025-00032</a>
            Culpeper County &ndash; Culpeper Technology Zone 230 kV Loop and Lines #2 and #1065 Conversion Project
            <ul><li><a href="/map.pdf">Technology Zone Project Map</a></li></ul>
          </li>
          <li><a href="/docketsearch#/caseDetails/140000">PUR-2021-00001</a>
            Routine 69 kV rebuild
          </li>
        </ul>
      </li>
    </ul>
    """

    def handler(request):
        return httpx.Response(200, text=html, request=request)

    _mock_client(monkeypatch, handler)

    records = VirginiaSccTransmissionCasesAdapter().fetch({"limit": 5, "keywords": ["technology zone", "230 kV"]})

    assert len(records) == 1
    assert records[0]["source"] == "virginia_scc_transmission_cases"
    assert records[0]["owner_type"] == "investor_owned_utility"
    assert records[0]["state"] == "VA"
    assert "Virginia SCC recent transmission case PUR-2025-00032" in records[0]["extracted_specs"]["evidence_excerpts"][0]


def test_georgia_psc_data_center_adapter_builds_large_load_signal_from_fact_sheet(monkeypatch):
    page = '<h4>Information on Data Centers</h4><p>Docket #44280 protects customers from data center related costs.</p><a href="/site/downloads/datacenterfactsheet.pdf">Fact Sheet</a>'
    fact_sheet = """
    DATA CENTER FACT SHEET
    Georgia Power must file quarterly reports with the PSC to track new data centers.
    The Commissioners voted to certify the construction of 9,985 MW of new energy generation,
    approximately 80 percent of which is expected to power data centers.
    """

    def handler(request):
        if str(request.url).endswith(".pdf"):
            return httpx.Response(200, content=fact_sheet.encode(), request=request)
        return httpx.Response(200, text=page, request=request)

    _mock_client(monkeypatch, handler)

    records = GeorgiaPscDataCenterAdapter().fetch({"keywords": ["data center", "georgia power"]})

    assert len(records) == 1
    assert records[0]["source"] == "georgia_psc_data_center"
    assert records[0]["owner_type"] == "investor_owned_utility"
    assert records[0]["project_type"] == "data_center_power"
    assert "9,985 MW" in records[0]["extracted_specs"]["evidence_excerpts"][0]


def test_texas_puc_dockets_adapter_filters_and_links_dockets(monkeypatch):
    html = """
    <table>
      <tr><th>Control</th><th>Filings</th><th>Utility</th><th>Description (Case Style)</th></tr>
      <tr>
        <td><a href="/search/filings/?ControlNumber=59818">59818</a></td>
        <td>1</td>
        <td>SOUTHWESTERN ELECTRIC POWER COMPANY</td>
        <td>APPLICATION TO AMEND ITS CERTIFICATE OF CONVENIENCE AND NECESSITY FOR A 765 KV TRANSMISSION LINE PROJECT</td>
      </tr>
      <tr><td>59820</td><td>1</td><td>Retailer</td><td>Routine retail electric provider update</td></tr>
    </table>
    """

    def handler(request):
        return httpx.Response(200, text=html, request=request)

    _mock_client(monkeypatch, handler)

    records = TexasPucDocketsAdapter().fetch({"limit": 5, "keywords": ["transmission"]})

    assert len(records) == 1
    assert records[0]["signal_type"] == "puc_docket"
    assert records[0]["state"] == "TX"
    assert records[0]["source_url"].endswith("ControlNumber=59818")
    assert records[0]["attachments"][1]["type"] == "evidence"


def test_loudoun_land_applications_adapter_queries_arcgis_and_ranks_stronger_signals(monkeypatch):
    payload = {
        "features": [
            {
                "attributes": {
                    "PlanNumber": "ZCOR-1",
                    "PlanName": "Generic Industrial Park",
                    "PlanDescription": "Industrial park zoning determination.",
                    "PlanType": "Zoning Determination",
                    "PlanStatus": "In Review",
                    "PlanApplicationDate": 1780000000000,
                    "AssignedTo": "Planner",
                }
            },
            {
                "attributes": {
                    "PlanNumber": "CMPT-1",
                    "PlanName": "Fractus-Lenticular Substations",
                    "PlanDescription": "Commission permit for electric substation infrastructure serving data center load.",
                    "PlanType": "Commission Permit",
                    "PlanStatus": "In Review",
                    "PlanApplicationDate": 1770000000000,
                    "AssignedTo": "Planner",
                }
            },
        ]
    }

    def handler(request):
        assert "/query" in str(request.url)
        return httpx.Response(200, json=payload)

    _mock_client(monkeypatch, handler)

    records = LoudounLandApplicationsAdapter().fetch({"limit": 2, "keywords": ["industrial park", "substation", "data center"]})

    assert len(records) == 2
    assert records[0]["title"].startswith("Loudoun land application CMPT-1")
    assert records[0]["signal_type"] == "zoning_or_permit"
    assert records[0]["attachments"][0]["type"] == "evidence"
