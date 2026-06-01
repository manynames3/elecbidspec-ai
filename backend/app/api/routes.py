from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import CompanyProfile, IngestionJob, Opportunity
from app.schemas import (
    CompanyProfileCreate,
    CompanyProfileRead,
    IngestionJobCreate,
    IngestionJobRead,
    OpportunityCreate,
    OpportunityRead,
    ProposalRead,
    SearchRequest,
)
from app.services.classification import classify_bid
from app.services.extraction import extract_specs, parse_attachment
from app.services.fit_scoring import score_fit
from app.services.proposal import generate_proposal_package
from app.services.search import search_opportunities

router = APIRouter()


def opportunity_to_dict(opportunity: Opportunity) -> dict:
    return {
        "id": opportunity.id,
        "title": opportunity.title,
        "agency": opportunity.agency,
        "location": opportunity.location,
        "state": opportunity.state,
        "due_date": opportunity.due_date,
        "naics_code": opportunity.naics_code,
        "description": opportunity.description,
        "source": opportunity.source,
        "source_url": opportunity.source_url,
        "estimated_value": float(opportunity.estimated_value) if opportunity.estimated_value is not None else None,
        "attachments": opportunity.attachments or [],
        "extracted_specs": opportunity.extracted_specs or {},
        "project_type": opportunity.project_type,
        "confidence_score": opportunity.confidence_score,
        "classification_explanation": opportunity.classification_explanation,
        "fit_score": opportunity.fit_score,
        "fit_explanation": opportunity.fit_explanation,
        "created_at": opportunity.created_at,
        "updated_at": opportunity.updated_at,
    }


def get_profile_data(db: Session) -> dict | None:
    profile = db.query(CompanyProfile).first()
    if not profile:
        return None
    return {
        "name": profile.name,
        "states_served": profile.states_served,
        "bonding_capacity": float(profile.bonding_capacity) if profile.bonding_capacity is not None else None,
        "cable_types_supplied": profile.cable_types_supplied,
        "installation_capabilities": profile.installation_capabilities,
        "labor_type": profile.labor_type,
        "experience": profile.experience,
    }


def enrich_opportunity_data(data: dict, db: Session) -> dict:
    specs = data.get("extracted_specs") or extract_specs(data.get("description") or "")
    classification = classify_bid(data.get("title") or "", data.get("description") or "", specs)
    enriched = {
        **data,
        "extracted_specs": specs,
        "project_type": classification["project_type"],
        "confidence_score": classification["confidence_score"],
        "classification_explanation": classification["explanation"],
    }
    profile = get_profile_data(db)
    if profile:
        enriched.update(score_fit(enriched, profile))
    return enriched


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ElecBidSpec AI"}


@router.get("/opportunities", response_model=list[OpportunityRead])
def list_opportunities(
    db: Session = Depends(get_db),
    due_before: date | None = Query(default=None),
    due_after: date | None = Query(default=None),
    state: str | None = Query(default=None, min_length=2, max_length=2),
    project_type: str | None = Query(default=None),
    min_fit_score: int | None = Query(default=None, ge=0, le=100),
    min_value: Decimal | None = Query(default=None),
    source: str | None = Query(default=None),
) -> list[Opportunity]:
    query = db.query(Opportunity)
    if due_before:
        query = query.filter(Opportunity.due_date <= due_before)
    if due_after:
        query = query.filter(Opportunity.due_date >= due_after)
    if state:
        query = query.filter(Opportunity.state == state.upper())
    if project_type:
        query = query.filter(Opportunity.project_type == project_type)
    if min_fit_score is not None:
        query = query.filter(Opportunity.fit_score >= min_fit_score)
    if min_value is not None:
        query = query.filter(Opportunity.estimated_value >= min_value)
    if source:
        query = query.filter(Opportunity.source == source)
    return query.order_by(Opportunity.due_date.asc().nullslast(), Opportunity.fit_score.desc().nullslast()).all()


@router.post("/opportunities", response_model=OpportunityRead, status_code=201)
def create_opportunity(payload: OpportunityCreate, db: Session = Depends(get_db)) -> Opportunity:
    data = enrich_opportunity_data(payload.model_dump(), db)
    opportunity = Opportunity(**data)
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityRead)
def get_opportunity(opportunity_id: int, db: Session = Depends(get_db)) -> Opportunity:
    opportunity = db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opportunity


@router.post("/opportunities/{opportunity_id}/rescore", response_model=OpportunityRead)
def rescore_opportunity(opportunity_id: int, db: Session = Depends(get_db)) -> Opportunity:
    opportunity = db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    enriched = enrich_opportunity_data(opportunity_to_dict(opportunity), db)
    for key, value in enriched.items():
        if hasattr(opportunity, key) and key not in {"id", "created_at", "updated_at"}:
            setattr(opportunity, key, value)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.get("/opportunities/{opportunity_id}/proposal", response_model=ProposalRead)
def get_proposal(opportunity_id: int, db: Session = Depends(get_db)) -> dict:
    opportunity = db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return generate_proposal_package(opportunity_to_dict(opportunity))


@router.post("/search")
def natural_language_search(payload: SearchRequest, db: Session = Depends(get_db)) -> list[dict]:
    opportunities = [opportunity_to_dict(item) for item in db.query(Opportunity).all()]
    results = search_opportunities(payload.query, opportunities)
    return results[:25]


@router.post("/uploads", response_model=OpportunityRead, status_code=201)
async def upload_opportunity_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    title: str | None = Form(default=None),
    agency: str | None = Form(default=None),
    location: str | None = Form(default=None),
    state: str | None = Form(default=None),
    due_date: date | None = Form(default=None),
    naics_code: str | None = Form(default=None),
    estimated_value: Decimal | None = Form(default=None),
    source_url: str | None = Form(default=None),
) -> Opportunity:
    settings = get_settings()
    content = await file.read()
    storage_name = f"{uuid4()}-{Path(file.filename or 'upload').name}"
    storage_path = settings.upload_dir / storage_name
    storage_path.write_bytes(content)

    text = parse_attachment(content, file.filename or storage_name)
    specs = extract_specs(text)
    data = {
        "title": title or Path(file.filename or "Uploaded RFP").stem,
        "agency": agency,
        "location": location,
        "state": state.upper() if state else None,
        "due_date": due_date,
        "naics_code": naics_code,
        "description": text[:6000],
        "source": "manual_upload",
        "source_url": source_url,
        "estimated_value": estimated_value,
        "attachments": [{"name": file.filename, "stored_path": str(storage_path)}],
        "extracted_specs": specs,
    }
    opportunity = Opportunity(**enrich_opportunity_data(data, db))
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.get("/company-profile", response_model=CompanyProfileRead)
def get_company_profile(db: Session = Depends(get_db)) -> CompanyProfile:
    profile = db.query(CompanyProfile).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Company profile not found. Seed or create a profile first.")
    return profile


@router.put("/company-profile", response_model=CompanyProfileRead)
def upsert_company_profile(payload: CompanyProfileCreate, db: Session = Depends(get_db)) -> CompanyProfile:
    profile = db.query(CompanyProfile).first()
    if profile:
        for key, value in payload.model_dump().items():
            setattr(profile, key, value)
    else:
        profile = CompanyProfile(**payload.model_dump())
        db.add(profile)
    db.commit()
    db.refresh(profile)
    for opportunity in db.query(Opportunity).all():
        enriched = enrich_opportunity_data(opportunity_to_dict(opportunity), db)
        opportunity.fit_score = enriched.get("fit_score")
        opportunity.fit_explanation = enriched.get("fit_explanation")
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/ingestion/jobs", response_model=IngestionJobRead, status_code=202)
def create_ingestion_job(payload: IngestionJobCreate, db: Session = Depends(get_db)) -> IngestionJob:
    if payload.adapter != "sam_gov":
        raise HTTPException(status_code=400, detail="Only the sam_gov adapter is implemented in this MVP.")
    job = IngestionJob(adapter=payload.adapter, params=payload.params, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/ingestion/jobs", response_model=list[IngestionJobRead])
def list_ingestion_jobs(db: Session = Depends(get_db)) -> list[IngestionJob]:
    return db.query(IngestionJob).order_by(IngestionJob.created_at.desc()).limit(50).all()

