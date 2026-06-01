from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import CompanyProfile, Opportunity
from app.services.classification import classify_bid
from app.services.extraction import extract_specs
from app.services.fit_scoring import score_fit
from app.services.value_assessment import assess_value, infer_source_type, normalize_bid_status


SEED_DIR = Path(__file__).parent / "seed_data"
LEGACY_SAMPLE_PROFILE_NAMES = {"Sample Electrical Contractor", "Tri-State Cable & Power Services"}


def _parse_date(value: str | None):
    return date.fromisoformat(value) if value else None


def load_json(name: str):
    return json.loads((SEED_DIR / name).read_text())


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

    if db.query(Opportunity).count() > 0:
        db.commit()
        return

    for item in load_json("sample_opportunities.json"):
        specs = extract_specs(item.get("description") or "")
        classification = classify_bid(item["title"], item.get("description") or "", specs)
        opportunity_data = {
            **item,
            "due_date": _parse_date(item.get("due_date")),
            "estimated_value": Decimal(str(item["estimated_value"])) if item.get("estimated_value") else None,
            "attachments": [],
            "extracted_specs": specs,
            "source_type": item.get("source_type") or infer_source_type(item.get("source"), item.get("agency")),
            "bid_status": normalize_bid_status(item.get("bid_status"), _parse_date(item.get("due_date"))),
            "project_type": classification["project_type"],
            "confidence_score": classification["confidence_score"],
            "classification_explanation": classification["explanation"],
        }
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
