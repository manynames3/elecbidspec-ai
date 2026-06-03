from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.main import app
from app.models import CompanyProfile, Opportunity, SavedSearch, User
from app.api.routes import get_db
from app.services.auth import hash_password
from app.services.tenancy import PUBLIC_TENANT_ID


def _client_with_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    db = Session()
    db.add(CompanyProfile(tenant_id="default", name="Default Profile"))
    db.add(SavedSearch(tenant_id="default", name="Default tenant search", query="data center"))
    db.commit()
    db.close()

    def override_get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), Session


def test_unauthenticated_account_status_does_not_expose_default_saved_searches():
    client, _ = _client_with_db()
    try:
        response = client.get("/api/account/status")
        assert response.status_code == 200
        payload = response.json()
        assert payload["authenticated"] is False
        assert payload["onboarding"]["saved_search_count"] == 0
        assert payload["onboarding"]["alert_configured"] is False
    finally:
        app.dependency_overrides.clear()


def test_account_owned_routes_require_login_even_when_demo_data_is_public():
    client, _ = _client_with_db()
    try:
        protected_paths = [
            "/api/company-profile",
            "/api/alerts/preferences",
            "/api/saved-searches",
            "/api/opportunities/1/workflow",
            "/api/workflow/opportunities",
            "/api/opportunities?saved_only=true",
        ]
        for path in protected_paths:
            assert client.get(path).status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_private_uploaded_opportunities_are_visible_only_to_owning_tenant():
    client, Session = _client_with_db()
    db = Session()
    public = Opportunity(
        tenant_id=PUBLIC_TENANT_ID,
        title="Public substation opportunity",
        source="seed",
        source_type="sample",
        bid_status="open",
        attachments=[],
        extracted_specs={},
        project_type="substation_related",
        confidence_score=0.8,
    )
    tenant_a = Opportunity(
        tenant_id="tenant-a",
        title="Tenant A uploaded RFP",
        source="manual_upload",
        source_type="manual",
        bid_status="open",
        attachments=[],
        extracted_specs={},
        project_type="underground_installation",
        confidence_score=0.7,
    )
    tenant_b = Opportunity(
        tenant_id="tenant-b",
        title="Tenant B uploaded RFP",
        source="manual_upload",
        source_type="manual",
        bid_status="open",
        attachments=[],
        extracted_specs={},
        project_type="data_center_power",
        confidence_score=0.7,
    )
    db.add_all([public, tenant_a, tenant_b])
    db.add(User(email="a@example.com", password_hash=hash_password("secret"), role="user", tenant_id="tenant-a", is_active=True))
    db.commit()
    tenant_b_id = tenant_b.id
    db.close()

    try:
        public_titles = {item["title"] for item in client.get("/api/opportunities").json()}
        assert public_titles == {"Public substation opportunity"}

        login = client.post("/api/auth/login", json={"email": "a@example.com", "password": "secret"})
        token = login.json()["token"]
        tenant_titles = {item["title"] for item in client.get("/api/opportunities", headers={"Authorization": f"Bearer {token}"}).json()}
        assert tenant_titles == {"Public substation opportunity", "Tenant A uploaded RFP"}

        assert client.get(f"/api/opportunities/{tenant_b_id}", headers={"Authorization": f"Bearer {token}"}).status_code == 404
    finally:
        app.dependency_overrides.clear()
