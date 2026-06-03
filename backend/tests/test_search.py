from datetime import date, timedelta

from app.services.search import parse_due_before, parse_owner_type, parse_project_stage, parse_state_filter, parse_value_threshold, search_opportunities


def test_parse_value_threshold_handles_minimum_mil_language():
    assert parse_value_threshold("public bids above minimum $5mil range") == 5_000_000
    assert parse_value_threshold("data center power at least $10M") == 10_000_000


def test_parse_due_before_and_state_filter_from_natural_language():
    assert parse_due_before("due in the next 30 days") == date.today() + timedelta(days=30)
    assert parse_state_filter("Show conduit bids over $5M in Texas") == "TX"
    assert parse_state_filter("show data center work in CA") == "CA"


def test_parse_stage_and_owner_from_utility_signal_language():
    assert parse_project_stage("show PUC rate case signals before RFP") == "early_signal"
    assert parse_project_stage("find future data center projects long before bidding") == "early_signal"
    assert parse_project_stage("find AVL prequalification opportunities") == "pre_rfp"
    assert parse_owner_type("show investor-owned utility data center signals") == "investor_owned_utility"


def test_search_boosts_requested_state_match():
    opportunities = [
        {
            "id": 1,
            "title": "Conduit and underground feeder replacement",
            "description": "Cable installation and trenching.",
            "state": "OK",
            "source_type": "state_local",
            "bid_status": "open",
            "project_type": "underground_installation",
            "fit_score": 88,
            "estimated_value": 8_000_000,
            "minimum_value_match": True,
            "extracted_specs": {"keywords": ["conduit"], "required_materials": ["cable"]},
        },
        {
            "id": 2,
            "title": "Conduit and underground feeder replacement",
            "description": "Cable installation and trenching.",
            "state": "TX",
            "source_type": "state_local",
            "bid_status": "open",
            "project_type": "underground_installation",
            "fit_score": 82,
            "estimated_value": 8_000_000,
            "minimum_value_match": True,
            "extracted_specs": {"keywords": ["conduit"], "required_materials": ["cable"]},
        },
    ]

    results = search_opportunities("Show conduit bids over $5M in Texas", opportunities)

    assert results[0]["opportunity"]["id"] == 2
    assert "Located in TX" in results[0]["search_explanation"]


def test_search_prioritizes_ai_data_center_infrastructure():
    opportunities = [
        {
            "id": 1,
            "title": "Office lighting replacement over $20M",
            "description": "Replace fixtures.",
            "source_type": "state_local",
            "bid_status": "open",
            "project_type": "general_electrical",
            "fit_score": 70,
            "estimated_value": 20_000_000,
            "extracted_specs": {"keywords": ["lighting"], "required_materials": []},
        },
        {
            "id": 2,
            "title": "Hyperscale AI data center critical power campus",
            "description": "Medium voltage feeders, UPS, switchgear, generators, and utility interconnection.",
            "source_type": "utility",
            "bid_status": "open",
            "project_type": "data_center_power",
            "fit_score": 92,
            "estimated_value": 25_000_000,
            "extracted_specs": {
                "keywords": ["ai infrastructure", "data center", "critical power"],
                "required_materials": ["ups", "switchgear"],
            },
        },
    ]

    results = search_opportunities("show AI infrastructure data center opportunities over $10M", opportunities)

    assert results[0]["opportunity"]["id"] == 2
    assert all(result["opportunity"]["id"] != 1 for result in results)
    assert "AI/data center infrastructure indicators" in results[0]["search_explanation"]


def test_search_prioritizes_iou_early_signals_for_data_center_load():
    opportunities = [
        {
            "id": 1,
            "title": "Open municipal substation bid",
            "description": "Active public RFP for transformer replacement.",
            "state": "TX",
            "source_type": "utility",
            "bid_status": "open",
            "project_stage": "active_bid",
            "signal_type": None,
            "owner_type": "public_power_or_utility",
            "project_type": "substation_related",
            "fit_score": 84,
            "estimated_value": 12_000_000,
            "minimum_value_match": True,
            "extracted_specs": {"keywords": ["substation"], "required_materials": []},
        },
        {
            "id": 2,
            "title": "PUC docket for investor-owned utility AI campus interconnection",
            "description": "Rate case filing references 230kV substation, EHV cable, and data center large load interconnection.",
            "state": "TX",
            "source_type": "regulatory",
            "bid_status": "open",
            "project_stage": "early_signal",
            "signal_type": "puc_docket",
            "owner_type": "investor_owned_utility",
            "project_type": "data_center_power",
            "fit_score": 90,
            "estimated_value": None,
            "minimum_value_match": True,
            "extracted_specs": {"keywords": ["data center", "substation", "high voltage"], "required_materials": ["ehv cable"]},
        },
    ]

    results = search_opportunities("show investor-owned utility data center early signals in Texas", opportunities)

    assert results[0]["opportunity"]["id"] == 2
    assert "Stage matches early signal" in results[0]["search_explanation"]
    assert "Owner type matches investor owned utility" in results[0]["search_explanation"]
