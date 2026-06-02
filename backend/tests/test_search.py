from app.services.search import parse_value_threshold, search_opportunities


def test_parse_value_threshold_handles_minimum_mil_language():
    assert parse_value_threshold("public bids above minimum $5mil range") == 5_000_000
    assert parse_value_threshold("data center power at least $10M") == 10_000_000


def test_search_prioritizes_ai_data_center_infrastructure():
    opportunities = [
        {
            "id": 1,
            "title": "Office lighting replacement",
            "description": "Replace fixtures.",
            "source_type": "state_local",
            "bid_status": "open",
            "project_type": "general_electrical",
            "fit_score": 70,
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
    assert "AI/data center infrastructure indicators" in results[0]["search_explanation"]
