from __future__ import annotations

import logging

from mangum import Mangum

from app.bootstrap import bootstrap_database
from app.core.config import get_settings
from app.main import app

logger = logging.getLogger("elecbidspec.lambda")

settings = get_settings()
if settings.bootstrap_database_on_startup:
    try:
        bootstrap_database()
    except Exception:
        logger.exception("Database bootstrap failed during Lambda cold start")
        raise

handler = Mangum(app, lifespan="off")
