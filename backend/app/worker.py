from __future__ import annotations

import logging
import time

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import CompanyProfile, IngestionJob, Opportunity
from app.services.fit_scoring import score_fit
from app.services.ingestion.sam_gov import SamGovAdapter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("elecbidspec.worker")

ADAPTERS = {"sam_gov": SamGovAdapter()}


def _profile_data(db: Session) -> dict | None:
    profile = db.query(CompanyProfile).first()
    if not profile:
        return None
    return {
        "states_served": profile.states_served,
        "bonding_capacity": float(profile.bonding_capacity) if profile.bonding_capacity is not None else None,
        "cable_types_supplied": profile.cable_types_supplied,
        "installation_capabilities": profile.installation_capabilities,
        "labor_type": profile.labor_type,
        "experience": profile.experience,
    }


def process_job(db: Session, job: IngestionJob) -> None:
    adapter = ADAPTERS.get(job.adapter)
    if not adapter:
        raise ValueError(f"Unknown ingestion adapter: {job.adapter}")

    job.status = "running"
    db.commit()
    imported = 0
    skipped = 0
    profile = _profile_data(db)
    for data in adapter.fetch(job.params or {}):
        existing = None
        if data.get("source_url"):
            existing = db.query(Opportunity).filter(Opportunity.source_url == data["source_url"]).first()
        if existing:
            skipped += 1
            continue
        if profile:
            data.update(score_fit(data, profile))
        db.add(Opportunity(**data))
        imported += 1
    job.status = "complete"
    job.result = {"imported": imported, "skipped": skipped}
    db.commit()


def run_once() -> bool:
    db = SessionLocal()
    try:
        job = db.query(IngestionJob).filter(IngestionJob.status == "queued").order_by(IngestionJob.created_at.asc()).first()
        if not job:
            return False
        try:
            process_job(db, job)
        except Exception as exc:  # noqa: BLE001 - worker should persist job errors
            logger.exception("Ingestion job failed")
            job.status = "failed"
            job.error = str(exc)
            db.commit()
        return True
    finally:
        db.close()


def main() -> None:
    logger.info("ElecBidSpec AI worker started")
    while True:
        did_work = run_once()
        time.sleep(2 if did_work else 10)


if __name__ == "__main__":
    main()

