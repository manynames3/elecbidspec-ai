from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ElecBidSpec AI"
    environment: str = "development"
    api_prefix: str = "/api"

    database_url: str = Field(
        default="postgresql+psycopg://elecbidspec:elecbidspec@db:5432/elecbidspec",
        validation_alias="DATABASE_URL",
    )
    frontend_origin: str = Field(default="http://localhost:3000", validation_alias="FRONTEND_ORIGIN")

    sam_gov_api_key: str | None = Field(default=None, validation_alias="SAM_GOV_API_KEY")
    sam_gov_api_base_url: str = Field(
        default="https://api.sam.gov/opportunities/v2/search",
        validation_alias="SAM_GOV_API_BASE_URL",
    )

    upload_dir: Path = Field(default=Path("/tmp/elecbidspec_uploads"), validation_alias="UPLOAD_DIR")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings

