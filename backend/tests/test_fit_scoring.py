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

