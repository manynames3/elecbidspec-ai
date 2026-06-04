from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import CompanyProfile, Opportunity
from app.services.backfill import backfill_existing_opportunities


def test_backfill_existing_opportunities_adds_pursuit_intelligence():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(
        CompanyProfile(
            tenant_id="default",
            name="Taihan Cable & Solution",
            states_served=["NATIONWIDE"],
            bonding_capacity=600_000_000,
            cable_types_supplied=["high_voltage", "medium_voltage", "hvdc"],
            installation_capabilities=["partner-led", "substation"],
            labor_type="partner-led",
            experience={"data_center_power": True, "substation_related": True},
        )
    )
    db.add(
        Opportunity(
            title="Dominion 500 kV data center interconnection",
            agency="Dominion Energy Virginia",
            state="VA",
            description="PUC filing for 500 kV data center large load interconnection with substation and underground cable scope.",
            source="virginia_scc_transmission_cases",
            source_type="regulatory",
            source_url="https://example.test/docket",
            bid_status="planning",
            project_stage="early_signal",
            signal_type="puc_docket",
            owner_type="investor_owned_utility",
            estimated_value=25_000_000,
            value_confidence="likely",
            minimum_value_match=True,
            attachments=[
                {
                    "type": "evidence",
                    "name": "Docket",
                    "url": "https://example.test/docket",
                    "excerpt": "Dominion 500 kV data center interconnection.",
                }
            ],
            extracted_specs={"keywords": ["data center", "500 kV"]},
            project_type="general_electrical",
            confidence_score=0.1,
        )
    )
    db.commit()

    result = backfill_existing_opportunities(db)
    opportunity = db.query(Opportunity).first()

    assert result["updated"] == 1
    assert opportunity.extracted_specs["taihan_intelligence"]["tier"] == "high"
    assert opportunity.extracted_specs["pursuit_intelligence"]["evidence_grade"] == "strong"
    assert opportunity.fit_score is not None

    db.close()
