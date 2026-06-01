import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.session import Base
from app.models import Opportunity
from app.services.attachment_ingestion import ingest_opportunity_attachments


def test_ingest_opportunity_attachments_fetches_and_merges_specs(monkeypatch, tmp_path):
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    opportunity = Opportunity(
        title="Underground feeder replacement",
        agency="Example Utility",
        source="example_portal",
        source_type="utility",
        source_url="https://example.gov/bids/123",
        bid_status="open",
        attachments=[],
        extracted_specs={},
        project_type="general_electrical",
        confidence_score=0.0,
    )
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)

    listing_html = '<html><body><a href="/docs/spec.txt">RFP electrical cable specification</a></body></html>'
    spec_text = (
        "The work includes underground cable, medium voltage conduit, trenching, installation, "
        "testing, and performance bond requirements. Submit proposal by 07/30/2026."
    )

    def handler(request):
        if str(request.url).endswith("/docs/spec.txt"):
            return httpx.Response(200, content=spec_text.encode("utf-8"), headers={"content-type": "text/plain"})
        return httpx.Response(200, text=listing_html, headers={"content-type": "text/html"})

    real_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **{key: value for key, value in kwargs.items() if key != "headers"}),
    )

    extractions = ingest_opportunity_attachments(db, opportunity)

    assert len(extractions) == 1
    assert extractions[0].status == "complete"
    assert "underground cable" in opportunity.extracted_specs["keywords"]
    assert "conduit" in opportunity.extracted_specs["required_materials"]
    assert opportunity.attachments[0]["url"] == "https://example.gov/docs/spec.txt"

    db.close()
    get_settings.cache_clear()
