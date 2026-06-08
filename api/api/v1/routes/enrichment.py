"""Prospect enrichment routes — on-demand rich data for site generation."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User
from schemas.enrichment import ProspectEnrichmentResponse, ProspectEnrichmentUpdate
from services.auth_service import get_current_active_user
from services.enrichment_service import enrichment_service

router = APIRouter(prefix="/prospects", tags=["enrichment"])


@router.get("/{prospect_id}/enrichment", response_model=ProspectEnrichmentResponse)
async def get_prospect_enrichment(
    prospect_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ProspectEnrichmentResponse:
    """Return the enrichment record for a prospect (404 if none yet)."""
    record = enrichment_service.get_for_prospect(db, current_user.id, prospect_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No enrichment for this prospect")
    return ProspectEnrichmentResponse.model_validate(record)


@router.post("/{prospect_id}/enrichment/run", response_model=ProspectEnrichmentResponse)
async def run_prospect_enrichment(
    prospect_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ProspectEnrichmentResponse:
    """Run (or re-run) enrichment scraping for a prospect."""
    prospect = enrichment_service.get_prospect_for_user(db, current_user.id, prospect_id)
    if not prospect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    record = await enrichment_service.enrich(db, current_user.id, prospect)
    return ProspectEnrichmentResponse.model_validate(record)


@router.patch("/{prospect_id}/enrichment", response_model=ProspectEnrichmentResponse)
async def update_prospect_enrichment(
    prospect_id: int,
    payload: ProspectEnrichmentUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ProspectEnrichmentResponse:
    """Apply manual edits to a prospect's enrichment data (creates the record if needed)."""
    prospect = enrichment_service.get_prospect_for_user(db, current_user.id, prospect_id)
    if not prospect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    record = enrichment_service.get_or_create(db, current_user.id, prospect_id)
    record = enrichment_service.update(db, record, updates)
    return ProspectEnrichmentResponse.model_validate(record)
