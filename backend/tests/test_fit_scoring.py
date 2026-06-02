from app.services.fit_scoring import score_fit


def test_fit_scoring_rewards_location_bonding_and_capabilities():
    opportunity = {
        "state": "CA",
        "estimated_value": 5_000_000,
        "project_type": "underground_installation",
        "description": "Union underground conduit and cable installation.",
        "title": "Underground Cable Install",
        "extracted_specs": {
            "keywords": ["underground cable", "conduit", "trenching"],
            "required_materials": ["cable", "conduit"],
        },
    }
    profile = {
        "states_served": ["CA"],
        "bonding_capacity": 10_000_000,
        "cable_types_supplied": ["medium_voltage", "conduit"],
        "installation_capabilities": ["underground", "trenching", "conduit"],
        "labor_type": "union",
        "experience": {"underground_installation": True},
    }

    result = score_fit(opportunity, profile)

    assert result["fit_score"] >= 85
    assert "Serves project state CA" in result["fit_explanation"]


def test_fit_scoring_accepts_nationwide_state_profile():
    result = score_fit(
        {
            "state": "NY",
            "estimated_value": 8_000_000,
            "project_type": "substation_related",
            "description": "Substation transformer work.",
            "title": "Transformer Replacement",
            "extracted_specs": {"keywords": ["substation", "transformer"], "required_materials": ["transformer"]},
        },
        {
            "states_served": ["NATIONWIDE"],
            "bonding_capacity": 600_000_000,
            "cable_types_supplied": ["high_voltage"],
            "installation_capabilities": ["substation", "transformer"],
            "labor_type": "partner-led",
            "experience": {"substation_related": True},
        },
    )

    assert "Serves project state NY" in result["fit_explanation"]
