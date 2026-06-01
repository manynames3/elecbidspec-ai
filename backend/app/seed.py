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


SEED_DIR = Path(__file__).parent / "seed_data"


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
            "project_type": classification["project_type"],
            "confidence_score": classification["confidence_score"],
            "classification_explanation": classification["explanation"],
        }
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

