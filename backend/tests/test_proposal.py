import sys
import zipfile
from io import BytesIO
from types import SimpleNamespace

from app.core.config import get_settings
from app.services.proposal import generate_bedrock_proposal, generate_deterministic_proposal
from app.services.proposal_docx import generate_proposal_docx
from app.services.proposal_pdf import generate_proposal_pdf


def _opportunity():
    return {
        "title": "Substation transformer replacement",
        "agency": "Example Utility",
        "due_date": "2026-07-01",
        "project_type": "substation_related",
        "estimated_value": 12_000_000,
        "bid_status": "open",
        "value_confidence": "confirmed",
        "extracted_specs": {
            "keywords": ["substation", "transformer", "high voltage"],
            "required_materials": ["transformer", "medium voltage cable"],
            "installation_scope": ["testing and commissioning"],
        },
    }


def _taihan_profile():
    return {
        "name": "Taihan Cable & Solution",
        "states_served": ["NATIONWIDE"],
        "bonding_capacity": 600_000_000,
        "cable_types_supplied": ["high_voltage", "medium_voltage", "hvdc", "submarine_cable"],
        "installation_capabilities": ["substation", "connection", "construction", "turnkey_project_support"],
        "labor_type": "partner-led",
        "experience": {"substation_related": True},
    }


def test_deterministic_proposal_uses_company_profile_context():
    proposal = generate_deterministic_proposal(_opportunity(), _taihan_profile())

    assert "Taihan Cable & Solution" in proposal["draft_executive_summary"]
    assert any("Taihan Cable & Solution" in item for item in proposal["required_documents_checklist"])
    assert proposal["compliance_matrix"][0]["requirement"] == "Technical scope"
    assert "Recommendation:" in proposal["bid_no_bid_memo"]


def test_bedrock_proposal_parses_structured_response(monkeypatch):
    class FakeBedrockClient:
        def converse(self, **kwargs):
            assert kwargs["modelId"] == "test-model"
            assert kwargs["toolConfig"]["toolChoice"]["tool"]["name"] == "create_proposal_package"
            prompt = kwargs["messages"][0]["content"][0]["text"]
            assert "Taihan Cable & Solution" in prompt
            return {
                "output": {
                    "message": {
                        "content": [
                            {
                                "text": """
                                {
                                  "bid_summary": "Taihan-ready bid summary.",
                                  "scope_checklist": ["Confirm cable schedule."],
                                  "missing_information_checklist": ["Confirm final drawings."],
                                  "required_documents_checklist": ["Taihan capability statement."],
                                  "risk_flags": ["Validate outage window."],
                                  "draft_executive_summary": "Taihan Cable & Solution offers an optimized response.",
                                  "compliance_matrix": [{"requirement":"Cable schedule","status":"Review required","evidence":"Spec section","owner":"Taihan"}],
                                  "bid_no_bid_memo": "Recommendation: pursue.",
                                  "partner_email_template": "Subject: Partner support"
                                }
                                """
                            }
                        ]
                    }
                }
            }

    fake_boto3 = SimpleNamespace(client=lambda service_name, region_name=None: FakeBedrockClient())
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setenv("BEDROCK_PROPOSALS_ENABLED", "true")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "test-model")
    monkeypatch.setenv("BEDROCK_REGION", "us-east-1")
    get_settings.cache_clear()

    baseline = generate_deterministic_proposal(_opportunity(), _taihan_profile())
    proposal = generate_bedrock_proposal(_opportunity(), _taihan_profile(), baseline)

    assert proposal["bid_summary"] == "Taihan-ready bid summary."
    assert proposal["scope_checklist"] == ["Confirm cable schedule."]

    get_settings.cache_clear()


def test_bedrock_proposal_parses_tool_use_response(monkeypatch):
    class FakeBedrockClient:
        def converse(self, **kwargs):
            assert kwargs["toolConfig"]["toolChoice"]["tool"]["name"] == "create_proposal_package"
            return {
                "output": {
                    "message": {
                        "content": [
                            {
                                "toolUse": {
                                    "name": "create_proposal_package",
                                    "input": {
                                        "bid_summary": "Tool-generated Taihan bid summary.",
                                        "scope_checklist": ["Review high-voltage cable schedule."],
                                        "missing_information_checklist": ["Confirm outage window."],
                                        "required_documents_checklist": ["Taihan capability statement."],
                                        "risk_flags": ["Validate bonding requirement."],
                                        "draft_executive_summary": "Taihan Cable & Solution can support compliant cable supply.",
                                        "compliance_matrix": [
                                            {
                                                "requirement": "Cable supply",
                                                "status": "Review required",
                                                "evidence": "High-voltage cable schedule",
                                                "owner": "Taihan",
                                            }
                                        ],
                                        "bid_no_bid_memo": "Recommendation: pursue.",
                                        "partner_email_template": "Subject: Partner support",
                                    },
                                }
                            }
                        ]
                    }
                }
            }

    fake_boto3 = SimpleNamespace(client=lambda service_name, region_name=None: FakeBedrockClient())
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setenv("BEDROCK_PROPOSALS_ENABLED", "true")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "test-model")
    monkeypatch.setenv("BEDROCK_REGION", "us-east-1")
    get_settings.cache_clear()

    baseline = generate_deterministic_proposal(_opportunity(), _taihan_profile())
    proposal = generate_bedrock_proposal(_opportunity(), _taihan_profile(), baseline)

    assert proposal["bid_summary"] == "Tool-generated Taihan bid summary."
    assert proposal["scope_checklist"] == ["Review high-voltage cable schedule."]

    get_settings.cache_clear()


def test_proposal_docx_contains_word_package_parts():
    proposal = generate_deterministic_proposal(_opportunity(), _taihan_profile())
    content = generate_proposal_docx(_opportunity(), proposal, _taihan_profile())

    assert content.startswith(b"PK")
    with zipfile.ZipFile(BytesIO(content)) as docx:
        assert "word/document.xml" in docx.namelist()
        document_xml = docx.read("word/document.xml").decode("utf-8")
        assert "Taihan Cable &amp; Solution" in document_xml
        assert "Pursuit Decision Brief" in document_xml


def test_proposal_pdf_contains_pdf_document():
    proposal = generate_deterministic_proposal(_opportunity(), _taihan_profile())
    content = generate_proposal_pdf(_opportunity(), proposal, _taihan_profile())

    assert content.startswith(b"%PDF-1.4")
    assert b"Taihan Cable & Solution Proposal Prep Package" in content
    assert b"Pursuit Decision Brief" in content
    assert b"%%EOF" in content
