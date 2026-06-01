from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ElecBidSpec AI"
    environment: str = "development"
    api_prefix: str = "/api"

    database_url: str = Field(
        default="postgresql+psycopg://elecbidspec:elecbidspec@db:5432/elecbidspec",
        validation_alias="DATABASE_URL",
    )
    database_disable_pool: bool = Field(default=False, validation_alias="DATABASE_DISABLE_POOL")
    frontend_origin: str = Field(default="http://localhost:3000", validation_alias="FRONTEND_ORIGIN")
    admin_api_token: str | None = Field(default=None, validation_alias="ADMIN_API_TOKEN")
    auth_required: bool = Field(default=False, validation_alias="AUTH_REQUIRED")
    auth_session_ttl_hours: int = Field(default=168, validation_alias="AUTH_SESSION_TTL_HOURS")
    auth_admin_email: str | None = Field(default=None, validation_alias="AUTH_ADMIN_EMAIL")
    auth_admin_password: str | None = Field(default=None, validation_alias="AUTH_ADMIN_PASSWORD")
    auth_user_email: str | None = Field(default=None, validation_alias="AUTH_USER_EMAIL")
    auth_user_password: str | None = Field(default=None, validation_alias="AUTH_USER_PASSWORD")

    sam_gov_api_key: str | None = Field(default=None, validation_alias="SAM_GOV_API_KEY")
    sam_gov_api_base_url: str = Field(
        default="https://api.sam.gov/opportunities/v2/search",
        validation_alias="SAM_GOV_API_BASE_URL",
    )
    nypa_api_subscription_key: str | None = Field(default=None, validation_alias="NYPA_API_SUBSCRIPTION_KEY")

    smtp_host: str | None = Field(default=None, validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, validation_alias="SMTP_USERNAME")
    smtp_password: str | None = Field(default=None, validation_alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, validation_alias="SMTP_USE_TLS")
    alert_email_from: str | None = Field(default=None, validation_alias="ALERT_EMAIL_FROM")
    alert_send_cooldown_hours: int = Field(default=20, validation_alias="ALERT_SEND_COOLDOWN_HOURS")

    bedrock_proposals_enabled: bool = Field(default=False, validation_alias="BEDROCK_PROPOSALS_ENABLED")
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-haiku-20240307-v1:0",
        validation_alias="BEDROCK_MODEL_ID",
    )
    bedrock_region: str = Field(default="us-east-1", validation_alias=AliasChoices("BEDROCK_REGION", "AWS_REGION", "AWS_DEFAULT_REGION"))
    bedrock_max_tokens: int = Field(default=2500, validation_alias="BEDROCK_MAX_TOKENS")
    bedrock_temperature: float = Field(default=0.2, validation_alias="BEDROCK_TEMPERATURE")

    upload_dir: Path = Field(default=Path("/tmp/elecbidspec_uploads"), validation_alias="UPLOAD_DIR")
    upload_bucket: str | None = Field(default=None, validation_alias="UPLOAD_BUCKET")
    upload_prefix: str = Field(default="uploads", validation_alias="UPLOAD_PREFIX")

    bootstrap_database_on_startup: bool = Field(default=False, validation_alias="BOOTSTRAP_DATABASE_ON_STARTUP")
    run_migrations_on_startup: bool = Field(default=True, validation_alias="RUN_MIGRATIONS_ON_STARTUP")
    seed_database_on_startup: bool = Field(default=True, validation_alias="SEED_DATABASE_ON_STARTUP")
    worker_max_jobs_per_run: int = Field(default=5, validation_alias="WORKER_MAX_JOBS_PER_RUN")
    default_ingestion_enabled: bool = Field(default=True, validation_alias="DEFAULT_INGESTION_ENABLED")
    default_ingestion_refresh_hours: int = Field(default=6, validation_alias="DEFAULT_INGESTION_REFRESH_HOURS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings
