from __future__ import annotations

from app.services.ingestion.base import IngestionAdapter
from app.services.ingestion.public_json_feed import PublicJsonFeedAdapter
from app.services.ingestion.sam_gov import SamGovAdapter


ADAPTERS: dict[str, IngestionAdapter] = {
    SamGovAdapter.name: SamGovAdapter(),
    PublicJsonFeedAdapter.name: PublicJsonFeedAdapter(),
}
