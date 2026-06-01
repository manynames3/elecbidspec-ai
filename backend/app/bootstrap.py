from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import get_settings
from app.seed import main as seed_main

logger = logging.getLogger("elecbidspec.bootstrap")


def run_migrations() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(alembic_cfg, "head")


def bootstrap_database() -> None:
    settings = get_settings()
    if settings.run_migrations_on_startup:
        logger.info("Running database migrations")
        run_migrations()
    if settings.seed_database_on_startup:
        logger.info("Ensuring seed data exists")
        seed_main()
