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


class OpportunityWorkflowBase(BaseModel):
    saved: bool = False
    watched: bool = False
    hidden: bool = False
    status: str = "reviewing"
    owner: str | None = None
    priority: str = "normal"
    notes: str | None = None


class OpportunityWorkflowUpdate(BaseModel):
    saved: bool | None = None
    watched: bool | None = None
    hidden: bool | None = None
    status: str | None = None
    owner: str | None = None
    priority: str | None = None
    notes: str | None = None


class OpportunityWorkflowRead(OpportunityWorkflowBase):
    id: int
    opportunity_id: int
    tenant_id: str
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


class AttachmentExtractionRead(BaseModel):
    id: int
    opportunity_id: int
    source_url: str
    filename: str | None = None
    status: str
    attachment: dict = Field(default_factory=dict)
    extracted_specs: dict = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttachmentIngestionResult(BaseModel):
    opportunity: OpportunityRead
    extractions: list[AttachmentExtractionRead]


class AlertPreferenceBase(BaseModel):
    email_to: str | None = None
    min_fit_score: int = Field(default=70, ge=0, le=100)
    due_within_days: int = Field(default=30, ge=1, le=365)
    include_source_failures: bool = True
    enabled: bool = True


class AlertPreferenceUpdate(BaseModel):
    email_to: str | None = None
    min_fit_score: int | None = Field(default=None, ge=0, le=100)
    due_within_days: int | None = Field(default=None, ge=1, le=365)
    include_source_failures: bool | None = None
    enabled: bool | None = None


class AlertPreferenceRead(AlertPreferenceBase):
    id: int
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AlertRunRead(BaseModel):
    id: int
    tenant_id: str
    status: str
    digest: dict
    error: str | None = None
    sent_to: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SavedSearchBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    query: str | None = None
    filters: dict = Field(default_factory=dict)
    enabled: bool = True
    email_digest: bool = True


class SavedSearchCreate(SavedSearchBase):
    pass


class SavedSearchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    query: str | None = None
    filters: dict | None = None
    enabled: bool | None = None
    email_digest: bool | None = None


class SavedSearchRead(SavedSearchBase):
    id: int
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
