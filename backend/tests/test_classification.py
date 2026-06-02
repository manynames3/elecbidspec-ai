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


def test_classify_ai_infrastructure_power_as_data_center():
    result = classify_bid(
        "AI Infrastructure Campus Utility Interconnection",
        "Construct critical power systems for GPU clusters, UPS rooms, switchgear, and 230kV substation feed.",
        {"keywords": ["ai infrastructure", "critical power"], "required_materials": ["ups", "switchgear", "busduct"]},
    )

    assert result["project_type"] == "data_center_power"
    assert "ai infrastructure" in result["explanation"]


def test_short_data_center_terms_do_not_match_inside_words():
    result = classify_bid(
        "Office electrical supplies",
        "Provide electrical supplies and replacement parts for maintenance.",
        {"keywords": ["electrical"], "required_materials": []},
    )

    assert result["project_type"] != "data_center_power"


def test_delivery_ups_does_not_classify_as_data_center_power():
    result = classify_bid(
        "Central station monitoring",
        "Bid packages may be sent by FedEx, UPS, USPS, or hand delivery.",
        {"keywords": [], "required_materials": ["ups"]},
    )

    assert result["project_type"] != "data_center_power"


def test_switchgear_alone_is_not_data_center_power():
    result = classify_bid(
        "Outdoor switchgear replacement",
        "Furnish 4160V switchgear and related electrical equipment.",
        {"keywords": [], "required_materials": ["switchgear"]},
    )

    assert result["project_type"] != "data_center_power"
