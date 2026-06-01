from __future__ import annotations

from app.services.ingestion.base import IngestionAdapter
from app.services.ingestion.chicago_solicitations import ChicagoSolicitationsAdapter
from app.services.ingestion.nyc_city_record import NycCityRecordAdapter
from app.services.ingestion.public_html_scrape import PublicHtmlScrapeAdapter
from app.services.ingestion.public_json_feed import PublicJsonFeedAdapter
from app.services.ingestion.sam_gov import SamGovAdapter
from app.services.ingestion.sf_open_bids import SfOpenBidsAdapter


ADAPTERS: dict[str, IngestionAdapter] = {
    ChicagoSolicitationsAdapter.name: ChicagoSolicitationsAdapter(),
    NycCityRecordAdapter.name: NycCityRecordAdapter(),
    SamGovAdapter.name: SamGovAdapter(),
    SfOpenBidsAdapter.name: SfOpenBidsAdapter(),
    PublicJsonFeedAdapter.name: PublicJsonFeedAdapter(),
    PublicHtmlScrapeAdapter.name: PublicHtmlScrapeAdapter(),
}
