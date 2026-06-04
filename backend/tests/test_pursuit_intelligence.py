from app.services.intelligence_report import build_opportunity_brief, build_weekly_intelligence_report, generate_opportunity_brief_pdf, generate_weekly_intelligence_pdf
from app.services.pursuit_intelligence import add_pursuit_intelligence


def _opportunity():
    return {
        "id": 101,
        "title": "Dominion 500 kV data center interconnection and underground cable signal",
        "agency": "Dominion Energy Virginia",
        "description": "PUC filing references a 500 kV transmission interconnection for a large load data center campus with substation and underground cable scope.",
        "source": "virginia_scc_transmission_cases",
        "source_type": "regulatory",
        "source_url": "https://example.test/docket",
        "project_stage": "early_signal",
        "signal_type": "puc_docket",
        "owner_type": "investor_owned_utility",
        "estimated_value": 25_000_000,
        "value_confidence": "likely",
        "minimum_value_match": True,
        "fit_score": 91,
        "attachments": [
            {
                "type": "evidence",
                "name": "Virginia SCC docket",
                "url": "https://example.test/docket",
                "source": "virginia_scc_transmission_cases",
                "excerpt": "Dominion 500 kV data center interconnection and underground cable scope.",
            }
        ],
        "extracted_specs": {"keywords": ["data center", "500 kV", "underground cable", "substation"]},
        "project_type": "data_center_power",
        "confidence_score": 0.9,
    }


def test_add_pursuit_intelligence_adds_evidence_actions_and_analyst_review():
    enriched = add_pursuit_intelligence(_opportunity(), {"name": "Taihan Cable & Solution", "labor_type": "partner-led"})
    pursuit = enriched["extracted_specs"]["pursuit_intelligence"]
    taihan = enriched["extracted_specs"]["taihan_intelligence"]

    assert taihan["tier"] == "high"
    assert taihan["score_breakdown"]
    assert pursuit["evidence_grade"] == "strong"
    assert pursuit["source_evidence"][0]["excerpt"]
    assert pursuit["next_actions"]
    assert pursuit["relationship_targets"]
    assert pursuit["partner_targets"]
    assert pursuit["analyst_review"]["recommended_status"] == "verified_signal"


def test_weekly_report_and_brief_pdf_are_generated():
    enriched = add_pursuit_intelligence(_opportunity(), {"name": "Taihan Cable & Solution", "labor_type": "partner-led"})
    report = build_weekly_intelligence_report([enriched], [{"source": "virginia_scc_transmission_cases", "status": "healthy"}], {"name": "Taihan Cable & Solution"})
    brief = build_opportunity_brief(enriched, {"name": "Taihan Cable & Solution"})

    assert report["summary"]["high_priority"] == 1
    assert report["top_signals"][0]["id"] == 101
    assert brief["pursuit_decision"] == "escalate"
    assert generate_weekly_intelligence_pdf(report).startswith(b"%PDF-1.4")
    assert generate_opportunity_brief_pdf(brief).startswith(b"%PDF-1.4")
