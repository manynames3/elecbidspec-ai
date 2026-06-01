from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db.session import Base


def json_type():
    return JSON().with_variant(JSONB, "postgresql")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(280), index=True)
    agency: Mapped[Optional[str]] = mapped_column(String(220), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(220), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(2), index=True, nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, index=True, nullable=True)
    naics_code: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(80), default="manual", index=True)
    source_type: Mapped[str] = mapped_column(String(80), default="manual", index=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bid_status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    estimated_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    value_confidence: Mapped[str] = mapped_column(String(40), default="unknown", index=True)
    value_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    minimum_value_match: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    attachments: Mapped[list] = mapped_column(MutableList.as_mutable(json_type()), default=list)
    extracted_specs: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    project_type: Mapped[str] = mapped_column(String(80), default="general_electrical", index=True)
    confidence_score: Mapped[float] = mapped_column(default=0.0)
    classification_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fit_score: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    fit_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(80), default="default", index=True)
    name: Mapped[str] = mapped_column(String(220), default="Sample Electrical Contractor")
    states_served: Mapped[list] = mapped_column(MutableList.as_mutable(json_type()), default=list)
    bonding_capacity: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    cable_types_supplied: Mapped[list] = mapped_column(MutableList.as_mutable(json_type()), default=list)
    installation_capabilities: Mapped[list] = mapped_column(MutableList.as_mutable(json_type()), default=list)
    labor_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    experience: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="user", index=True)
    tenant_id: Mapped[str] = mapped_column(String(80), default="default", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    adapter: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    params: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    result: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OpportunityWorkflow(Base):
    __tablename__ = "opportunity_workflows"
    __table_args__ = (UniqueConstraint("opportunity_id", "tenant_id", name="uq_opportunity_workflow_tenant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    opportunity_id: Mapped[int] = mapped_column(Integer, index=True)
    tenant_id: Mapped[str] = mapped_column(String(80), default="default", index=True)
    saved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    watched: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[str] = mapped_column(String(40), default="reviewing", index=True)
    owner: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    priority: Mapped[str] = mapped_column(String(40), default="normal", index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProposalArtifact(Base):
    __tablename__ = "proposal_artifacts"
    __table_args__ = (UniqueConstraint("opportunity_id", "tenant_id", name="uq_proposal_artifact_tenant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    opportunity_id: Mapped[int] = mapped_column(Integer, index=True)
    tenant_id: Mapped[str] = mapped_column(String(80), default="default", index=True)
    content: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    source: Mapped[str] = mapped_column(String(40), default="deterministic", index=True)
    status: Mapped[str] = mapped_column(String(40), default="ready", index=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AlertPreference(Base):
    __tablename__ = "alert_preferences"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_alert_preferences_tenant"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(80), default="default", index=True)
    email_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    min_fit_score: Mapped[int] = mapped_column(Integer, default=70)
    due_within_days: Mapped[int] = mapped_column(Integer, default=30)
    include_source_failures: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AlertRun(Base):
    __tablename__ = "alert_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(80), default="default", index=True)
    status: Mapped[str] = mapped_column(String(40), default="complete", index=True)
    digest: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sent_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SavedSearch(Base):
    __tablename__ = "saved_searches"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_saved_search_tenant_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(80), default="default", index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    filters: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    email_digest: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OpportunityAttachmentExtraction(Base):
    __tablename__ = "opportunity_attachment_extractions"
    __table_args__ = (UniqueConstraint("opportunity_id", "source_url", name="uq_attachment_extraction_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    opportunity_id: Mapped[int] = mapped_column(Integer, index=True)
    source_url: Mapped[str] = mapped_column(Text)
    filename: Mapped[Optional[str]] = mapped_column(String(260), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    attachment: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    extracted_specs: Mapped[dict] = mapped_column(MutableDict.as_mutable(json_type()), default=dict)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
