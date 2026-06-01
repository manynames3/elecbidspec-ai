from __future__ import annotations

from app.services.ingestion.base import IngestionAdapter
from app.services.ingestion.chicago_solicitations import ChicagoSolicitationsAdapter
from app.services.ingestion.nyc_city_record import NycCityRecordAdapter
from app.services.ingestion.nypa import NypaAdapter
from app.services.ingestion.pa_emarketplace import PennsylvaniaEMarketplaceAdapter
from app.services.ingestion.public_html_scrape import PublicHtmlScrapeAdapter
from app.services.ingestion.public_json_feed import PublicJsonFeedAdapter
from app.services.ingestion.public_portal_links import PublicPortalLinksAdapter
from app.services.ingestion.sam_gov import SamGovAdapter
from app.services.ingestion.sf_open_bids import SfOpenBidsAdapter
from app.services.ingestion.txdot_bid_items import TxdotBidItemsAdapter


ADAPTERS: dict[str, IngestionAdapter] = {
    ChicagoSolicitationsAdapter.name: ChicagoSolicitationsAdapter(),
    NycCityRecordAdapter.name: NycCityRecordAdapter(),
    NypaAdapter.name: NypaAdapter(),
    PennsylvaniaEMarketplaceAdapter.name: PennsylvaniaEMarketplaceAdapter(),
    SamGovAdapter.name: SamGovAdapter(),
    SfOpenBidsAdapter.name: SfOpenBidsAdapter(),
    TxdotBidItemsAdapter.name: TxdotBidItemsAdapter(),
    PublicJsonFeedAdapter.name: PublicJsonFeedAdapter(),
    PublicHtmlScrapeAdapter.name: PublicHtmlScrapeAdapter(),
    PublicPortalLinksAdapter.name: PublicPortalLinksAdapter(),
}
