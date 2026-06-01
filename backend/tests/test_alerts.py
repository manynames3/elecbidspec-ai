from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import AlertPreference, Opportunity, OpportunityWorkflow, SavedSearch
from app.services.alerts import build_alert_digest


def test_build_alert_digest_filters_high_fit_and_hidden_opportunities():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    visible = Opportunity(
        title="Data center substation package",
        agency="Example Authority",
        state="VA",
        due_date=date.today() + timedelta(days=10),
        source="example_live",
        source_type="state_local",
        bid_status="open",
        estimated_value=12_000_000,
        value_confidence="confirmed",
        minimum_value_match=True,
        attachments=[],
        extracted_specs={"keywords": ["data center", "substation"]},
        project_type="data_center_power",
        confidence_score=0.9,
        fit_score=86,
    )
    hidden = Opportunity(
        title="Hidden substation package",
        agency="Example Authority",
        state="VA",
        due_date=date.today() + timedelta(days=10),
        source="example_live",
        source_type="state_local",
        bid_status="open",
        estimated_value=10_000_000,
        value_confidence="confirmed",
        minimum_value_match=True,
        attachments=[],
        extracted_specs={"keywords": ["substation"]},
        project_type="substation_related",
        confidence_score=0.8,
        fit_score=90,
    )
    db.add_all([visible, hidden])
    db.commit()
    db.refresh(visible)
    db.refresh(hidden)
    db.add(OpportunityWorkflow(opportunity_id=hidden.id, tenant_id="default", hidden=True))
    preference = AlertPreference(tenant_id="default", min_fit_score=70, due_within_days=30)
    saved_search = SavedSearch(
        tenant_id="default",
        name="Data center power",
        query="data center substation over $10M",
        filters={"real_only": "true", "bid_status": "open"},
    )
    db.add(preference)
    db.add(saved_search)
    db.commit()
    db.refresh(preference)

    digest = build_alert_digest(db, "default", preference)

    assert digest["counts"]["high_fit"] == 1
    assert digest["high_fit"][0]["id"] == visible.id
    assert digest["counts"]["due_soon"] == 1
    assert digest["counts"]["saved_searches"] == 1
    assert digest["counts"]["saved_search_matches"] == 1
    assert digest["saved_searches"][0]["matches"][0]["opportunity"]["id"] == visible.id

    db.close()
