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
    assert result["evidence_strength"] == {
        "named_utility": True,
        "explicit_voltage": True,
        "data_center_or_load": True,
        "cable_specific_scope": True,
    }


def test_taihan_intelligence_does_not_overprioritize_generic_queue_records():
    opportunity = {
        "title": "SPP active GI request GEN-2024-352: Sibley 345 kV Substation",
        "agency": "Southwest Power Pool",
        "description": "Generator interconnection request at Sibley 345 kV Substation.",
        "source_type": "rto_iso",
        "project_stage": "early_signal",
        "signal_type": "interconnection_queue",
        "owner_type": "private_developer",
        "minimum_value_match": True,
        "fit_score": 88,
        "extracted_specs": {"keywords": ["substation", "high voltage"]},
    }

    result = assess_taihan_intelligence(opportunity)

    assert result["tier"] != "high"
    assert result["score"] < 82
    assert result["cable_relevance"] == "medium"
    assert result["evidence_strength"] == {
        "named_utility": False,
        "explicit_voltage": True,
        "data_center_or_load": False,
        "cable_specific_scope": False,
    }


def test_taihan_intelligence_prioritizes_named_utility_voltage_and_cable_scope():
    opportunity = {
        "title": "Oncor 345 kV substation feeder and conductor upgrade",
        "agency": "Oncor",
        "description": "Early regulatory filing for 345 kV substation work with underground cable, feeder, conductor, and duct bank scope.",
        "source_type": "regulatory",
        "project_stage": "early_signal",
        "signal_type": "puc_docket",
        "owner_type": "investor_owned_utility",
        "minimum_value_match": True,
        "fit_score": 90,
        "extracted_specs": {"keywords": ["345 kV", "substation", "underground cable", "conductor"]},
    }

    result = assess_taihan_intelligence(opportunity)

    assert result["tier"] == "high"
    assert result["cable_relevance"] == "high"
    assert result["evidence_strength"]["named_utility"] is True
    assert result["evidence_strength"]["explicit_voltage"] is True
    assert result["evidence_strength"]["cable_specific_scope"] is True


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
