from __future__ import annotations

from app.services.ingestion.base import IngestionAdapter
from app.services.ingestion.nyc_city_record import NycCityRecordAdapter
from app.services.ingestion.public_html_scrape import PublicHtmlScrapeAdapter
from app.services.ingestion.public_json_feed import PublicJsonFeedAdapter
from app.services.ingestion.sam_gov import SamGovAdapter


ADAPTERS: dict[str, IngestionAdapter] = {
    NycCityRecordAdapter.name: NycCityRecordAdapter(),
    SamGovAdapter.name: SamGovAdapter(),
    PublicJsonFeedAdapter.name: PublicJsonFeedAdapter(),
    PublicHtmlScrapeAdapter.name: PublicHtmlScrapeAdapter(),
}
