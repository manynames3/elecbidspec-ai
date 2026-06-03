from __future__ import annotations

from app.services.ingestion.base import IngestionAdapter
from app.services.ingestion.bonfire_portal import BonfirePortalAdapter
from app.services.ingestion.chicago_solicitations import ChicagoSolicitationsAdapter
from app.services.ingestion.jea_procurement import JeaProcurementAdapter
from app.services.ingestion.nyc_city_record import NycCityRecordAdapter
from app.services.ingestion.nypa import NypaAdapter
from app.services.ingestion.pa_emarketplace import PennsylvaniaEMarketplaceAdapter
from app.services.ingestion.public_bid_page import PublicBidPageAdapter
from app.services.ingestion.public_html_scrape import PublicHtmlScrapeAdapter
from app.services.ingestion.public_json_feed import PublicJsonFeedAdapter
from app.services.ingestion.public_portal_links import PublicPortalLinksAdapter
from app.services.ingestion.sam_gov import SamGovAdapter
from app.services.ingestion.sf_open_bids import SfOpenBidsAdapter
from app.services.ingestion.txdot_bid_items import TxdotBidItemsAdapter
from app.services.ingestion.upstream_signals import (
    CaisoInterconnectionQueueAdapter,
    ErcotCapacityChangesAdapter,
    GeorgiaPscDataCenterAdapter,
    IsoNeInterconnectionQueueAdapter,
    LoudounLandApplicationsAdapter,
    MisoErasInterconnectionAdapter,
    NyisoInterconnectionQueueAdapter,
    PjmProjectConstructionAdapter,
    SppGiActiveRequestsAdapter,
    TexasPucDocketsAdapter,
    VirginiaSccTransmissionCasesAdapter,
)


ADAPTERS: dict[str, IngestionAdapter] = {
    BonfirePortalAdapter.name: BonfirePortalAdapter(),
    ChicagoSolicitationsAdapter.name: ChicagoSolicitationsAdapter(),
    JeaProcurementAdapter.name: JeaProcurementAdapter(),
    NycCityRecordAdapter.name: NycCityRecordAdapter(),
    NypaAdapter.name: NypaAdapter(),
    PennsylvaniaEMarketplaceAdapter.name: PennsylvaniaEMarketplaceAdapter(),
    SamGovAdapter.name: SamGovAdapter(),
    SfOpenBidsAdapter.name: SfOpenBidsAdapter(),
    TxdotBidItemsAdapter.name: TxdotBidItemsAdapter(),
    PjmProjectConstructionAdapter.name: PjmProjectConstructionAdapter(),
    CaisoInterconnectionQueueAdapter.name: CaisoInterconnectionQueueAdapter(),
    ErcotCapacityChangesAdapter.name: ErcotCapacityChangesAdapter(),
    IsoNeInterconnectionQueueAdapter.name: IsoNeInterconnectionQueueAdapter(),
    SppGiActiveRequestsAdapter.name: SppGiActiveRequestsAdapter(),
    MisoErasInterconnectionAdapter.name: MisoErasInterconnectionAdapter(),
    NyisoInterconnectionQueueAdapter.name: NyisoInterconnectionQueueAdapter(),
    VirginiaSccTransmissionCasesAdapter.name: VirginiaSccTransmissionCasesAdapter(),
    GeorgiaPscDataCenterAdapter.name: GeorgiaPscDataCenterAdapter(),
    TexasPucDocketsAdapter.name: TexasPucDocketsAdapter(),
    LoudounLandApplicationsAdapter.name: LoudounLandApplicationsAdapter(),
    PublicBidPageAdapter.name: PublicBidPageAdapter(),
    PublicJsonFeedAdapter.name: PublicJsonFeedAdapter(),
    PublicHtmlScrapeAdapter.name: PublicHtmlScrapeAdapter(),
    PublicPortalLinksAdapter.name: PublicPortalLinksAdapter(),
}
