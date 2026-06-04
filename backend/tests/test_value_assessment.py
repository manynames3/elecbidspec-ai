from app.services.value_assessment import (
    assess_value,
    infer_estimated_value,
    infer_owner_type,
    infer_project_stage,
    infer_signal_type,
    infer_source_type,
    normalize_bid_status,
)


def test_assess_value_confirms_posted_value_over_minimum():
    result = assess_value({"estimated_value": 7_500_000, "description": "Medium voltage cable install."})

    assert result["minimum_value_match"] is True
    assert result["value_confidence"] == "confirmed"


def test_assess_value_marks_scope_likely_when_value_missing():
    result = assess_value(
        {
            "title": "Data center substation and high voltage distribution campus",
            "description": "Furnish switchgear, transformers, medium voltage feeders, performance bond required.",
            "extracted_specs": {"keywords": ["data center", "substation", "high voltage"]},
        }
    )

    assert result["minimum_value_match"] is True
    assert result["value_confidence"] == "likely"


def test_assess_value_marks_public_power_hub_scope_likely_when_value_missing():
    result = assess_value(
        {
            "title": "Hunts Point shore power hub infrastructure delivery",
            "description": "Design, construction, installation, energization, shore power connections, and yard infrastructure.",
            "extracted_specs": {"installation_scope": ["installation", "energization"]},
        }
    )

    assert result["minimum_value_match"] is True
    assert result["value_confidence"] == "likely"


def test_assess_value_marks_active_public_power_bid_package_likely_when_value_missing():
    result = assess_value(
        {
            "title": "EXT GSA | Power Station Block 8 Bid Package 1",
            "description": "Department: General Services Agency Category: Construction/Construction Services Type: Seeking Bids Status: Open",
            "source_type": "state_local",
            "project_stage": "active_bid",
            "bid_status": "open",
        }
    )

    assert result["minimum_value_match"] is True
    assert result["value_confidence"] == "likely"


def test_assess_value_does_not_promote_market_research_commodity_notices():
    result = assess_value(
        {
            "title": "PULL BOXES, ELECTRICAL, MARKET RESEARCH SURVEY",
            "description": "Category: Commodity Type: RFQ - Request for Quote Status: Open",
            "source_type": "state_local",
            "project_stage": "active_bid",
            "bid_status": "open",
        }
    )

    assert result["minimum_value_match"] is False
    assert result["value_confidence"] == "unknown"


def test_assess_value_does_not_promote_non_power_distribution_contracts():
    result = assess_value(
        {
            "title": "Requirements contract for food distribution services",
            "description": "Category: Services Method: Competitive Sealed Bids Status: Open",
            "source_type": "state_local",
            "project_stage": "active_bid",
            "bid_status": "open",
        }
    )

    assert result["minimum_value_match"] is False
    assert result["value_confidence"] == "unknown"


def test_infer_estimated_value_from_notice_text():
    value = infer_estimated_value("Estimated value exceeds $12.5M for the project.")

    assert value == 12_500_000
    assert infer_estimated_value("Budget is above $5mil for the project.") == 5_000_000


def test_normalizes_portal_status_and_manual_public_agency_type():
    assert normalize_bid_status("Sources Sought", None) == "open"
    assert infer_source_type("manual_upload", "City of Austin Public Works") == "state_local"
    assert infer_source_type("iso_ne_interconnection_queue", "ISO New England") == "rto_iso"
    assert infer_source_type("texas_puc_dockets", "Public Utility Commission of Texas") == "regulatory"
    assert infer_source_type("loudoun_land_applications", "Loudoun County") == "land_use"


def test_infers_upstream_iou_signal_context():
    data = {
        "title": "PUC docket for Dominion Energy data center interconnection",
        "agency": "Virginia State Corporation Commission",
        "description": "Rate case filing describes large load interconnection, 230kV substation work, and future EHV cable procurement.",
        "source_type": "regulatory",
        "bid_status": "open",
        "project_stage": "active_bid",
        "owner_type": "public_agency",
    }

    assert infer_owner_type(data) == "investor_owned_utility"
    assert infer_project_stage(data) == "early_signal"
    assert infer_signal_type(data) == "puc_docket"
