from __future__ import annotations

from typing import Any

DEFAULT_ELECTRICAL_SOURCE_KEYWORDS = [
    "electrical",
    "electric",
    "electrical systems",
    "electrical installations",
    "electric work",
    "battery electric",
    "battery-electric",
    "low voltage",
    "medium voltage",
    "high voltage",
    "shore power",
    "power hub",
    "power station",
    "cable",
    "conduit",
    "underground",
    "utility",
    "transformer",
    "substation",
    "switchgear",
    "fire alarm",
    "generator",
    "energization",
    "data center",
    "transmission",
    "distribution",
    "lighting",
    "lights",
    "airfield lights",
    "lighting infrastructure",
]


def _catalog_entry(
    source: str,
    label: str,
    category: str,
    coverage: str,
    adapter: str,
    source_url: str | None = None,
    directory_only: bool = False,
    requires_setting: str | None = None,
    portal_gated: bool = False,
    access_note: str | None = None,
    job_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "source": source,
        "label": label,
        "category": category,
        "coverage": coverage,
        "adapter": adapter,
    }
    if source_url:
        entry["source_url"] = source_url
    if directory_only:
        entry["directory_only"] = True
    if requires_setting:
        entry["requires_setting"] = requires_setting
    if portal_gated:
        entry["portal_gated"] = True
    if access_note:
        entry["access_note"] = access_note
    if job_params:
        entry["job_params"] = job_params
    return entry


DEFAULT_SOURCE_CATALOG = [
    _catalog_entry("sam_gov", "SAM.gov", "federal", "Nationwide federal opportunities", "sam_gov", requires_setting="sam_gov_api_key"),
    _catalog_entry("txdot_bid_items", "TxDOT", "state_dot", "Texas statewide DOT lettings", "txdot_bid_items", "https://data.texas.gov/Transportation/Official-and-Unofficial-Bid-Items/qh8x-rm8r"),
    _catalog_entry("pa_emarketplace", "PA eMarketplace", "state_local", "Pennsylvania statewide open solicitations", "pa_emarketplace", "https://www.emarketplace.state.pa.us/Search.aspx/Home.aspx"),
    _catalog_entry("nypa", "NY Power Authority", "utility", "New York utility RFQ/RFPs", "nypa", "https://rfp.nypa.gov/", requires_setting="nypa_api_subscription_key"),
    _catalog_entry("nyc_city_record", "NYC City Record", "state_local", "New York City public solicitations", "nyc_city_record"),
    _catalog_entry("nyc_school_construction_authority", "NYC School Construction", "education", "NYC School Construction Authority solicitations", "nyc_city_record"),
    _catalog_entry("la_ramp", "Los Angeles RAMP", "state_local", "Los Angeles city/county and LADWP-linked postings", "public_json_feed", "https://data.lacity.org/"),
    _catalog_entry("chicago_solicitations", "Chicago/CTA", "state_local", "City of Chicago and CTA solicitations", "chicago_solicitations"),
    _catalog_entry("sf_open_bids", "San Francisco", "state_local", "San Francisco open bid opportunities", "sf_open_bids"),
    _catalog_entry("montgomery_md_solicitations", "Montgomery County", "state_local", "Montgomery County, MD active solicitations", "public_json_feed"),
    _catalog_entry(
        "ca_dot",
        "Caltrans",
        "state_dot",
        "California state transportation bid opportunities",
        "public_portal_links",
        "https://caleprocure.ca.gov/",
        portal_gated=True,
        access_note="Cal eProcure currently returns an automated 403 response to server-side public monitoring.",
    ),
    _catalog_entry("fl_dot", "FDOT", "state_dot", "Florida transportation lettings and procurement", "public_portal_links", "https://www.fdot.gov/contracts/"),
    _catalog_entry("ny_dot", "NYSDOT", "state_dot", "New York transportation contract opportunities", "public_portal_links", "https://www.dot.ny.gov/doing-business/opportunities/const-notices"),
    _catalog_entry("ga_dot", "GDOT", "state_dot", "Georgia transportation bid opportunities", "public_portal_links", "https://www.dot.ga.gov/GDOT/Pages/Contractors.aspx"),
    _catalog_entry("il_dot", "IDOT", "state_dot", "Illinois transportation lettings and bids", "public_portal_links", "https://idot.illinois.gov/doing-business/procurements.html"),
    _catalog_entry(
        "oh_dot",
        "Ohio DOT / OhioBuys",
        "state_dot",
        "Ohio transportation bid opportunities through OhioBuys public solicitations",
        "public_portal_links",
        "https://ohiobuys.ohio.gov/page.aspx/en/rfp/request_browse_public",
        portal_gated=True,
        access_note="OhioBuys serves a browser/captcha check before public solicitation details.",
    ),
    _catalog_entry("nc_evp", "NC eVP", "state_local", "North Carolina statewide public solicitations including schools, utilities, airports, and authorities", "public_portal_links", "https://evp.nc.gov/solicitations/"),
    _catalog_entry("va_dot", "VDOT", "state_dot", "Virginia transportation bids and proposals", "public_portal_links", "https://www.virginiadot.org/business/const/default.asp"),
    _catalog_entry("az_dot", "ADOT", "state_dot", "Arizona transportation procurement and construction opportunities", "public_portal_links", "https://azdot.gov/business/contracts-and-specifications"),
    _catalog_entry(
        "tva_procurement",
        "TVA",
        "utility",
        "Tennessee Valley Authority supplier and sourcing opportunities",
        "public_portal_links",
        "https://www.tva.com/information/suppliers",
        portal_gated=True,
        access_note="TVA supplier pages are protected by a browser challenge from server-side monitors.",
    ),
    _catalog_entry(
        "bpa_procurement",
        "BPA",
        "utility",
        "Bonneville Power Administration acquisition opportunities",
        "public_portal_links",
        "https://www.bpa.gov/energy-and-services/customers-and-contractors/buying-or-selling-products-and-services",
        access_note="BPA publishes supplier instructions and procurement category documents; open opportunity detail is often routed through federal channels.",
    ),
    _catalog_entry("ladwp", "LADWP", "utility", "Los Angeles Department of Water and Power opportunities through regional procurement portals", "public_portal_links", "https://www.ladwp.com/"),
    _catalog_entry("austin_energy", "Austin Energy", "utility", "Austin Energy and City of Austin procurement", "public_portal_links", "https://financeonline.austintexas.gov/afo/account_services/solicitation/solicitation.cfm"),
    _catalog_entry(
        "cps_energy",
        "CPS Energy",
        "utility",
        "San Antonio CPS Energy procurement opportunities",
        "public_portal_links",
        "https://www.cpsenergy.com/content/corporate/en/work-with-us/procurement-and-suppliers/bid-opportunities.html",
        portal_gated=True,
        access_note="CPS Energy directs active opportunities to its supplier management system.",
    ),
    _catalog_entry(
        "jea",
        "JEA",
        "utility",
        "Jacksonville JEA procurement opportunities",
        "jea_procurement",
        "https://www.jea.com/about/procurement/formal_procurement_opportunities/?ns=y",
    ),
    _catalog_entry(
        "srp",
        "SRP",
        "utility",
        "Salt River Project procurement and supplier opportunities",
        "public_portal_links",
        "https://www.srpnet.com/about/suppliers",
        portal_gated=True,
        access_note="SRP supplier pages are protected by a browser challenge from server-side monitors.",
    ),
    _catalog_entry("port_authority_ny_nj", "Port Authority NY/NJ", "airport_authority", "Airport, port, and transit authority bid opportunities", "public_portal_links", "https://www.panynj.gov/port-authority/en/business-opportunities/solicitations-advertisements.html"),
    _catalog_entry(
        "la_metro",
        "LA Metro",
        "transit",
        "Los Angeles Metro procurement opportunities",
        "public_portal_links",
        "https://business.metro.net/webcenter/portal/VendorPortal/pages_home/solicitations/openSolicitations.",
        portal_gated=True,
        access_note="LA Metro exposes a JavaScript procurement portal that needs a browser session for opportunity details.",
        job_params={"verify_tls": False},
    ),
    _catalog_entry("septa", "SEPTA", "transit", "Southeastern Pennsylvania Transportation Authority procurement", "public_portal_links", "https://www5.septa.org/business/procurement/"),
    _catalog_entry(
        "ny_mta",
        "MTA",
        "transit",
        "New York MTA procurement opportunities",
        "public_portal_links",
        "https://new.mta.info/doing-business-with-us/procurement",
        portal_gated=True,
        access_note="MTA procurement pages return an Akamai denial to server-side monitors.",
    ),
    _catalog_entry(
        "dfw_airport",
        "DFW Airport",
        "airport_authority",
        "Dallas Fort Worth Airport procurement opportunities",
        "bonfire_portal",
        "https://dfwairport.bonfirehub.com/portal/?tab=openOpportunities",
    ),
    _catalog_entry("uc_procurement", "University of California", "university", "University of California construction and procurement opportunities", "public_portal_links", "https://www.ucop.edu/procurement-services/"),
    _catalog_entry("houston_water", "Houston Public Works", "water_authority", "Houston water, wastewater, and public works solicitations", "public_portal_links", "https://www.houstontx.gov/bizwithhou/"),
]

DEFAULT_PUBLIC_BID_JOBS = [
    {
        "adapter": "sam_gov",
        "requires_setting": "sam_gov_api_key",
        "params": {
            "job_label": "sam_gov",
            "limit": 50,
            "posted_window_days": 90,
            "ptype": "o",
            "status": "active",
            "keyword": "electrical cable OR high voltage OR medium voltage OR substation OR conduit OR transformer",
            "update_existing": True,
        },
    },
    {
        "adapter": "txdot_bid_items",
        "params": {
            "job_label": "txdot_bid_items",
            "limit": 50,
            "source_limit": 5000,
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "update_existing": True,
        },
    },
    {
        "adapter": "pa_emarketplace",
        "params": {
            "job_label": "pa_emarketplace",
            "limit": 50,
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "update_existing": True,
        },
    },
    {
        "adapter": "nypa",
        "requires_setting": "nypa_api_subscription_key",
        "params": {
            "job_label": "nypa",
            "limit": 50,
            "update_existing": True,
        },
    },
    {
        "adapter": "nyc_city_record",
        "params": {
            "job_label": "nyc_city_record",
            "limit": 25,
            "source_limit": 300,
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "update_existing": True,
        },
    },
    {
        "adapter": "nyc_city_record",
        "params": {
            "job_label": "nyc_school_construction_authority",
            "source": "nyc_school_construction_authority",
            "source_type": "education",
            "limit": 25,
            "source_limit": 300,
            "agency_keywords": ["School Construction Authority"],
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "update_existing": True,
        },
    },
    {
        "adapter": "sf_open_bids",
        "params": {
            "job_label": "sf_open_bids",
            "limit": 25,
            "source_limit": 300,
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "update_existing": True,
        },
    },
    {
        "adapter": "public_json_feed",
        "params": {
            "job_label": "la_ramp",
            "source": "la_ramp",
            "source_type": "state_local",
            "url": "https://data.lacity.org/resource/hf3r-utnq.json",
            "location": "Los Angeles, CA",
            "state": "CA",
            "agency_prefix": "Los Angeles RAMP",
            "limit": 50,
            "source_limit": 500,
            "order": "closedate ASC",
            "query_params": {
                "$where": "stagename in('Open', 'Amended')",
            },
            "mapping": {
                "title": "title",
                "agency": "department",
                "due_date": "closedate",
                "bid_status": "stagename",
                "source_url": "url.url",
            },
            "description_template": (
                "RAMP ID: {rampid}\n"
                "Department: {department}\n"
                "Category: {category}\n"
                "Type: {type}\n"
                "Status: {stagename}\n"
                "Open date: {bidpost}"
            ),
            "keyword_fields": ["title", "category", "type"],
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "status_allow": ["open", "amended"],
            "update_existing": True,
        },
    },
    {
        "adapter": "public_json_feed",
        "params": {
            "job_label": "montgomery_md_solicitations",
            "source": "montgomery_md_solicitations",
            "source_type": "state_local",
            "url": "https://data.montgomerycountymd.gov/resource/eeq6-nnwe.json",
            "location": "Montgomery County, MD",
            "state": "MD",
            "agency_prefix": "Montgomery County, MD",
            "limit": 25,
            "source_limit": 300,
            "order": "closingdate ASC",
            "query_params": {
                "$where": "status = 'Active'",
            },
            "mapping": {
                "title": "description",
                "agency": "department",
                "due_date": "closingdate",
                "bid_status": "status",
            },
            "source_url_template": "https://data.montgomerycountymd.gov/Government/Solicitations/eeq6-nnwe?number={number}",
            "description_template": (
                "Solicitation number: {number}\n"
                "Type: {type}\n"
                "Department: {department}\n"
                "Buyer: {buyer}\n"
                "Department contact: {deptcontact}\n"
                "Construction solicitation: {construction}\n"
                "LSBRP: {lsbrpindicator}"
            ),
            "keyword_fields": ["description", "department", "type"],
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "status_allow": ["active"],
            "update_existing": True,
        },
    },
    {
        "adapter": "chicago_solicitations",
        "params": {
            "job_label": "chicago_solicitations",
            "limit": 25,
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "update_existing": True,
        },
    },
    {
        "adapter": "jea_procurement",
        "params": {
            "job_label": "jea",
            "source": "jea",
            "source_type": "utility",
            "agency": "JEA",
            "state": "FL",
            "location": "Jacksonville, FL",
            "limit": 25,
            "source_limit": 1200,
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "update_existing": True,
        },
    },
    {
        "adapter": "bonfire_portal",
        "params": {
            "job_label": "dfw_airport",
            "source": "dfw_airport",
            "source_type": "airport_authority",
            "agency": "DFW Airport",
            "state": "TX",
            "location": "Dallas-Fort Worth, TX",
            "portal_url": "https://dfwairport.bonfirehub.com/portal/?tab=openOpportunities",
            "limit": 25,
            "source_limit": 250,
            "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
            "update_existing": True,
        },
    },
]

PORTAL_SOURCE_STATES = {
    "ca_dot": "CA",
    "fl_dot": "FL",
    "ny_dot": "NY",
    "ga_dot": "GA",
    "il_dot": "IL",
    "oh_dot": "OH",
    "nc_evp": "NC",
    "va_dot": "VA",
    "az_dot": "AZ",
    "ladwp": "CA",
    "austin_energy": "TX",
    "cps_energy": "TX",
    "jea": "FL",
    "srp": "AZ",
    "port_authority_ny_nj": "NY",
    "la_metro": "CA",
    "septa": "PA",
    "ny_mta": "NY",
    "dfw_airport": "TX",
    "uc_procurement": "CA",
    "houston_water": "TX",
}

DEFAULT_PUBLIC_BID_JOBS.extend(
    [
        {
            "adapter": "public_portal_links",
            "params": {
                "job_label": catalog["source"],
                "source": catalog["source"],
                "source_type": catalog["category"],
                "url": catalog["source_url"],
                "label": catalog["label"],
                "agency": catalog["label"],
                "state": PORTAL_SOURCE_STATES.get(catalog["source"]),
                "limit": 25,
                "source_limit": 600,
                "keywords": DEFAULT_ELECTRICAL_SOURCE_KEYWORDS,
                "update_existing": True,
                **(catalog.get("job_params") or {}),
            },
        }
        for catalog in DEFAULT_SOURCE_CATALOG
        if catalog.get("adapter") == "public_portal_links" and catalog.get("source_url")
    ]
)


def missing_required_setting(settings: Any, job_spec: dict[str, Any]) -> str | None:
    required = job_spec.get("requires_setting")
    if required and not getattr(settings, str(required), None):
        return str(required)
    return None


def available_default_public_bid_jobs(settings: Any) -> list[dict[str, Any]]:
    return [job for job in DEFAULT_PUBLIC_BID_JOBS if missing_required_setting(settings, job) is None]


def skipped_default_public_bid_jobs(settings: Any) -> list[dict[str, Any]]:
    return [job for job in DEFAULT_PUBLIC_BID_JOBS if missing_required_setting(settings, job) is not None]
