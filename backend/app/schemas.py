from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OpportunityBase(BaseModel):
    title: str
    agency: str | None = None
    location: str | None = None
    state: str | None = None
    due_date: date | None = None
    naics_code: str | None = None
    description: str | None = None
    source: str = "manual"
    source_type: str = "manual"
    source_url: str | None = None
    bid_status: str = "open"
    estimated_value: Decimal | None = None
    value_confidence: str = "unknown"
    value_explanation: str | None = None
    minimum_value_match: bool = False
    attachments: list[dict] = Field(default_factory=list)


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityUpdate(BaseModel):
    title: str | None = None
    agency: str | None = None
    location: str | None = None
    state: str | None = None
    due_date: date | None = None
    naics_code: str | None = None
    description: str | None = None
    source: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    bid_status: str | None = None
    estimated_value: Decimal | None = None
    value_confidence: str | None = None
    value_explanation: str | None = None
    minimum_value_match: bool | None = None


class OpportunityRead(OpportunityBase):
    id: int
    extracted_specs: dict = Field(default_factory=dict)
    project_type: str
    confidence_score: float
    classification_explanation: str | None = None
    fit_score: int | None = None
    fit_explanation: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SearchRequest(BaseModel):
    query: str


class UserRead(BaseModel):
    id: int
    email: str
    role: str
    tenant_id: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserRead
    expires_at: datetime


class ProposalRead(BaseModel):
    bid_summary: str
    scope_checklist: list[str]
    missing_information_checklist: list[str]
    required_documents_checklist: list[str]
    risk_flags: list[str]
    draft_executive_summary: str
    compliance_matrix: list[dict[str, str]]
    bid_no_bid_memo: str
    partner_email_template: str


class CompanyProfileBase(BaseModel):
    name: str
    tenant_id: str = "default"
    states_served: list[str] = Field(default_factory=list)
    bonding_capacity: Decimal | None = None
    cable_types_supplied: list[str] = Field(default_factory=list)
    installation_capabilities: list[str] = Field(default_factory=list)
    labor_type: str | None = None
    experience: dict = Field(default_factory=dict)


class CompanyProfileCreate(CompanyProfileBase):
    pass


class CompanyProfileRead(CompanyProfileBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IngestionJobCreate(BaseModel):
    adapter: str = "sam_gov"
    params: dict = Field(default_factory=dict)


class IngestionJobRead(BaseModel):
    id: int
    adapter: str
    status: str
    params: dict
    result: dict
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
