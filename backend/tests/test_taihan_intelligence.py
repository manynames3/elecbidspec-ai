from app.services.taihan_intelligence import add_taihan_intelligence, assess_taihan_intelligence


def test_taihan_intelligence_prioritizes_data_center_hv_upstream_signal():
    opportunity = {
        "title": "PUC docket for 500 kV data center transmission interconnection",
        "agency": "Dominion Energy Virginia",
        "description": "Large load data center campus requires 500 kV transmission, substation, transformer, and underground cable work.",
        "source_type": "regulatory",
        "project_stage": "early_signal",
        "signal_type": "puc_docket",
        "owner_type": "investor_owned_utility",
        "minimum_value_match": True,
        "fit_score": 91,
        "extracted_specs": {"keywords": ["data center", "high voltage", "substation", "underground cable"]},
    }

    result = assess_taihan_intelligence(opportunity)

    assert result["tier"] == "high"
    assert result["score"] >= 75
    assert result["cable_relevance"] == "high"
    assert result["procurement_path"] == "utility_rfp_or_avl"
    assert "HV/EHV cable package" in result["taihan_angle"]


def test_add_taihan_intelligence_preserves_existing_specs():
    opportunity = {
        "title": "Routine lighting retrofit",
        "description": "Low-voltage lighting work.",
        "project_stage": "active_bid",
        "source_type": "state_local",
        "extracted_specs": {"keywords": ["electrical"]},
    }

    enriched = add_taihan_intelligence(opportunity)

    assert enriched["extracted_specs"]["keywords"] == ["electrical"]
    assert enriched["extracted_specs"]["taihan_intelligence"]["tier"] in {"low", "medium", "high"}
