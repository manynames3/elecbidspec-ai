from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.worker import enqueue_default_jobs_if_due, run_once

logger = logging.getLogger("elecbidspec.worker_lambda")


def handler(event: dict[str, Any], context: Any) -> dict[str, int | bool]:
    settings = get_settings()
    queued = 0
    db = SessionLocal()
    try:
        queued = enqueue_default_jobs_if_due(db)
    finally:
        db.close()

    processed = 0
    for _ in range(settings.worker_max_jobs_per_run):
        if not run_once():
            break
        processed += 1
    logger.info("Processed %s ingestion jobs", processed)
    return {"queued": queued, "processed": processed, "had_work": processed > 0}
