from app.services.classification import classify_bid


def test_classify_data_center_power():
    result = classify_bid(
        "Hyperscale Data Center Critical Power",
        "Install switchgear, UPS distribution, medium voltage feeders, transformers, and fiber controls.",
        {"keywords": ["data center", "medium voltage"], "required_materials": ["switchgear", "transformer"]},
    )

    assert result["project_type"] == "data_center_power"
    assert result["confidence_score"] >= 0.6
    assert "data center" in result["explanation"]


def test_classify_fire_damage_rebuild():
    result = classify_bid(
        "Wildfire Distribution Rebuild",
        "Emergency repair of fire damage to overhead distribution pole line.",
        {"keywords": ["fire damage", "emergency repair", "distribution", "overhead"]},
    )

    assert result["project_type"] == "fire_damage_rebuild"

