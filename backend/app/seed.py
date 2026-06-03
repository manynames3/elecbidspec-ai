from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import CompanyProfile, Opportunity, User
from app.services.classification import classify_bid
from app.services.auth import hash_password
from app.services.extraction import extract_specs
from app.services.fit_scoring import score_fit
from app.services.value_assessment import assess_value, infer_owner_type, infer_project_stage, infer_signal_type, infer_source_type, normalize_bid_status


SEED_DIR = Path(__file__).parent / "seed_data"
LEGACY_SAMPLE_PROFILE_NAMES = {"Sample Electrical Contractor", "Tri-State Cable & Power Services"}


def _parse_date(value: str | None):
    return date.fromisoformat(value) if value else None


def load_json(name: str):
    return json.loads((SEED_DIR / name).read_text())


def _ensure_user(db: Session, email: str | None, password: str | None, role: str, tenant_id: str = "default") -> None:
    if not email or not password:
        return
    normalized_email = email.strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    password_hash = hash_password(password)
    if user:
        user.password_hash = password_hash
        user.role = role
        user.tenant_id = tenant_id
        user.is_active = True
    else:
        db.add(
            User(
                email=normalized_email,
                password_hash=password_hash,
                role=role,
                tenant_id=tenant_id,
                is_active=True,
            )
        )


def ensure_auth_seed_data(db: Session) -> None:
    settings = get_settings()
    _ensure_user(db, settings.auth_admin_email, settings.auth_admin_password, "admin")
    _ensure_user(db, settings.auth_user_email, settings.auth_user_password, "user")


def ensure_seed_data(db: Session) -> None:
    profile_data = load_json("sample_profile.json")
    profile = db.query(CompanyProfile).first()
    if not profile:
        profile = CompanyProfile(**profile_data)
        db.add(profile)
        db.flush()
    elif profile.name in LEGACY_SAMPLE_PROFILE_NAMES:
        for key, value in profile_data.items():
            setattr(profile, key, value)
        db.flush()
    ensure_auth_seed_data(db)

    if db.query(Opportunity).count() > 0:
        db.commit()
        return

    for item in load_json("sample_opportunities.json"):
        specs = extract_specs(item.get("description") or "")
        attachments = item.get("attachments") or []
        if attachments:
            specs["evidence_links"] = attachments
        classification = classify_bid(item["title"], item.get("description") or "", specs)
        opportunity_data = {
            **item,
            "due_date": _parse_date(item.get("due_date")),
            "forecast_rfp_date": _parse_date(item.get("forecast_rfp_date")),
            "estimated_value": Decimal(str(item["estimated_value"])) if item.get("estimated_value") else None,
            "attachments": attachments,
            "extracted_specs": specs,
            "source_type": item.get("source_type") or infer_source_type(item.get("source"), item.get("agency")),
            "bid_status": normalize_bid_status(item.get("bid_status"), _parse_date(item.get("due_date"))),
            "project_type": classification["project_type"],
            "confidence_score": classification["confidence_score"],
            "classification_explanation": classification["explanation"],
        }
        opportunity_data["owner_type"] = infer_owner_type(opportunity_data)
        opportunity_data["project_stage"] = infer_project_stage(opportunity_data)
        opportunity_data["signal_type"] = infer_signal_type(opportunity_data)
        opportunity_data.update(assess_value(opportunity_data))
        fit = score_fit(opportunity_data, profile_data)
        opportunity_data.update(fit)
        db.add(Opportunity(**opportunity_data))
    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        ensure_seed_data(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
