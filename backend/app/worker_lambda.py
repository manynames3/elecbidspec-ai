from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.worker import run_once

logger = logging.getLogger("elecbidspec.worker_lambda")


def handler(event: dict[str, Any], context: Any) -> dict[str, int | bool]:
    settings = get_settings()
    processed = 0
    for _ in range(settings.worker_max_jobs_per_run):
        if not run_once():
            break
        processed += 1
    logger.info("Processed %s ingestion jobs", processed)
    return {"processed": processed, "had_work": processed > 0}
