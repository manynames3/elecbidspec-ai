import httpx

from app.services.ingestion.bonfire_portal import BonfirePortalAdapter


def test_bonfire_portal_adapter_reads_public_open_opportunities(monkeypatch):
    payload = {
        "success": 1,
        "payload": {
            "projects": {
                "234204": {
                    "ProjectID": "234204",
                    "ReferenceID": "PA1992",
                    "ProjectName": "Terminal A Critical Equipment Protection",
                    "DateClose": "2026-06-10 19:00:00",
                    "DepartmentID": "2215",
                },
                "230674": {
                    "ProjectID": "230674",
                    "ReferenceID": "PA2069",
                    "ProjectName": "Fitness Equipment Maintenance Services",
                    "DateClose": "2026-06-08 19:00:00",
                },
            }
        },
    }

    def handler(request):
        if str(request.url).endswith("/PublicPortal/getOpenPublicOpportunitiesSectionData"):
            return httpx.Response(200, json=payload)
        return httpx.Response(200, text="<html></html>")

    real_client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **{key: value for key, value in kwargs.items() if key != "headers"}),
    )

    records = BonfirePortalAdapter().fetch(
        {
            "portal_url": "https://dfwairport.bonfirehub.com/portal/?tab=openOpportunities",
            "source": "dfw_airport",
            "source_type": "airport_authority",
            "agency": "DFW Airport",
            "state": "TX",
            "keywords": ["equipment protection", "airfield lights"],
        }
    )

    assert len(records) == 1
    assert records[0]["title"] == "Terminal A Critical Equipment Protection"
    assert records[0]["due_date"].isoformat() == "2026-06-10"
    assert records[0]["source_url"].endswith("projectId=234204")
