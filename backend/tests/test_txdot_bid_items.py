import httpx

from app.services.ingestion.txdot_bid_items import TxdotBidItemsAdapter


def test_txdot_bid_items_adapter_groups_relevant_project_rows(monkeypatch):
    payload = [
        {
            "controlling_project_id_ccsj": "0001-01-001",
            "control_section_job_csj": "0001-01-001",
            "project_number": "C 1-1-1",
            "project_id": "A001",
            "county": "Travis",
            "district_division": "Austin",
            "highway": "IH 35",
            "project_classification": "Roadway illumination",
            "project_type": "Construction",
            "bid_recieved_until_date_and": "2026-07-01T13:00:00.000",
            "bid_item_description": "ELECTRICAL CONDUIT",
            "specification_description": "INSTALL CONDUIT AND CONDUCTOR",
            "sealed_engineer_s_estimate_1": "6500000",
        },
        {
            "controlling_project_id_ccsj": "0001-01-001",
            "control_section_job_csj": "0001-01-001",
            "project_number": "C 1-1-1",
            "county": "Travis",
            "district_division": "Austin",
            "highway": "IH 35",
            "bid_recieved_until_date_and": "2026-07-01T13:00:00.000",
            "bid_item_description": "GROUND BOX",
            "specification_description": "ELECTRICAL PULL BOX",
        },
        {
            "controlling_project_id_ccsj": "0002-02-002",
            "project_number": "C 2-2-2",
            "county": "Hays",
            "bid_recieved_until_date_and": "2026-07-01T13:00:00.000",
            "bid_item_description": "ASPHALT",
            "specification_description": "PAVEMENT",
        },
    ]

    def handler(request):
        assert "bid_recieved_until_date_and" in str(request.url)
        return httpx.Response(200, json=payload)

    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=httpx.MockTransport(handler)))

    records = TxdotBidItemsAdapter().fetch({"limit": 5, "due_after": "2026-06-01"})

    assert len(records) == 1
    assert records[0]["source"] == "txdot_bid_items"
    assert records[0]["state"] == "TX"
    assert records[0]["estimated_value"] == 6_500_000
    assert "GROUND BOX" in records[0]["description"]
