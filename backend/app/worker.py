from __future__ import annotations

import logging
import time

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import AlertPreference, AlertRun, CompanyProfile, IngestionJob, Opportunity
from app.services.alerts import build_alert_digest
from app.services.email_alerts import send_alert_digest_email
from app.services.fit_scoring import score_fit
from app.services.ingestion.defaults import available_default_public_bid_jobs
from app.services.ingestion.registry import ADAPTERS
from app.services.value_assessment import assess_value, infer_source_type, normalize_bid_status

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("elecbidspec.worker")


def _default_job_label(adapter: str, params: dict | None) -> str:
    job_params = params or {}
    return str(job_params.get("job_label") or job_params.get("source") or adapter)


def _same_default_job(job: IngestionJob, adapter: str, label: str) -> bool:
    return job.adapter == adapter and _default_job_label(job.adapter, job.params) == label


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
    updated = 0
    profile = _profile_data(db)
    params = job.params or {}
    update_existing = bool(params.get("update_existing"))
    records = list(adapter.fetch(params))
    deleted_existing = 0
    replace_source = params.get("source") or params.get("job_label")
    if params.get("replace_source_records") and replace_source:
        deleted_existing = db.query(Opportunity).filter(Opportunity.source == str(replace_source)).delete(synchronize_session=False)
        db.commit()
    for data in records:
        existing = None
        if data.get("source_url"):
            existing = db.query(Opportunity).filter(Opportunity.source_url == data["source_url"]).first()
        inferred_source_type = infer_source_type(data.get("source"), data.get("agency"))
        if not data.get("source_type") or (data.get("source_type") == "manual" and inferred_source_type != "manual"):
            data["source_type"] = inferred_source_type
        data["bid_status"] = normalize_bid_status(data.get("bid_status"), data.get("due_date"))
        data.update(assess_value(data))
        if profile:
            data.update(score_fit(data, profile))
        if existing:
            if update_existing:
                for key, value in data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                updated += 1
            else:
                skipped += 1
            continue
        db.add(Opportunity(**data))
        imported += 1
    job.status = "complete"
    job.result = {"imported": imported, "updated": updated, "skipped": skipped, "deleted_existing": deleted_existing}
    db.commit()


def enqueue_default_jobs_if_due(db: Session, refresh_hours: int | None = None) -> int:
    settings = get_settings()
    if not settings.default_ingestion_enabled:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(hours=refresh_hours or settings.default_ingestion_refresh_hours)
    queued = 0
    for job_spec in available_default_public_bid_jobs(settings):
        adapter = job_spec["adapter"]
        label = _default_job_label(adapter, job_spec.get("params"))
        active_jobs = (
            db.query(IngestionJob)
            .filter(IngestionJob.adapter == adapter, IngestionJob.status.in_(["queued", "running"]))
            .order_by(IngestionJob.created_at.desc())
            .limit(25)
            .all()
        )
        if any(_same_default_job(job, adapter, label) for job in active_jobs):
            continue

        recent_complete_jobs = (
            db.query(IngestionJob)
            .filter(IngestionJob.adapter == adapter, IngestionJob.status == "complete")
            .order_by(IngestionJob.updated_at.desc())
            .limit(50)
            .all()
        )
        last_complete = next(
            (job for job in recent_complete_jobs if _same_default_job(job, adapter, label)),
            None,
        )
        if last_complete and last_complete.updated_at:
            last_updated = last_complete.updated_at
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)
            if last_updated >= cutoff:
                continue

        db.add(
            IngestionJob(
                adapter=adapter,
                params={**job_spec["params"], "scheduled": True, "update_existing": True},
                status="queued",
            )
        )
        queued += 1
    if queued:
        db.commit()
    return queued


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


def run_due_alerts(db: Session) -> int:
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.alert_send_cooldown_hours)
    created = 0
    preferences = (
        db.query(AlertPreference)
        .filter(AlertPreference.enabled == True, AlertPreference.email_to.isnot(None))  # noqa: E712
        .order_by(AlertPreference.updated_at.asc())
        .all()
    )
    for preference in preferences:
        latest = (
            db.query(AlertRun)
            .filter(AlertRun.tenant_id == preference.tenant_id)
            .order_by(AlertRun.created_at.desc())
            .first()
        )
        if latest and latest.created_at:
            latest_at = latest.created_at.replace(tzinfo=timezone.utc) if latest.created_at.tzinfo is None else latest.created_at
            if latest_at >= cutoff:
                continue
        digest = build_alert_digest(db, preference.tenant_id, preference)
        delivery = send_alert_digest_email(preference.email_to, digest)
        db.add(
            AlertRun(
                tenant_id=preference.tenant_id,
                status=delivery["status"] or "complete",
                digest=digest,
                error=delivery["error"],
                sent_to=preference.email_to if delivery["status"] == "sent" else None,
            )
        )
        created += 1
    if created:
        db.commit()
    return created


def main() -> None:
    logger.info("ElecBidSpec AI worker started")
    while True:
        did_work = run_once()
        time.sleep(2 if did_work else 10)


if __name__ == "__main__":
    main()
