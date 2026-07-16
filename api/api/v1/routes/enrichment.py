"""Prospect enrichment routes — on-demand rich data for site generation."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from enums.enrichment_status import EnrichmentStatus
from models.user import User
from schemas.enrichment import ProspectEnrichmentResponse, ProspectEnrichmentUpdate
from services.auth_service import get_current_active_user
from services.enrichment_service import enrichment_service

router = APIRouter(prefix="/prospects", tags=["enrichment"])

# Cap a single bulk enrichment request — each item drives a headless browser.
_MAX_BULK_ENRICH = 50


class BulkEnrichRequest(BaseModel):
    """Payload for POST /prospects/enrichment/bulk-run."""

    prospect_ids: list[int] = Field(..., min_length=1, max_length=_MAX_BULK_ENRICH)


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


@router.post("/{prospect_id}/enrichment/resolve-contact", response_model=ProspectEnrichmentResponse)
async def resolve_prospect_contact(
    prospect_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ProspectEnrichmentResponse:
    """(Re)run only the decision-maker name resolution for a prospect."""
    prospect = enrichment_service.get_prospect_for_user(db, current_user.id, prospect_id)
    if not prospect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    record = await enrichment_service.resolve_contact(db, current_user.id, prospect)
    return ProspectEnrichmentResponse.model_validate(record)


@router.post("/enrichment/bulk-run")
async def run_bulk_enrichment(
    payload: BulkEnrichRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Enrich several prospects in one call (runs sequentially to share one browser).

    Returns a per-prospect result list plus succeeded/failed counts. Missing
    prospects (not found / not owned) are reported as failures, never raised.
    """
    results: list[dict[str, Any]] = []
    succeeded = 0
    failed = 0

    for prospect_id in payload.prospect_ids:
        prospect = enrichment_service.get_prospect_for_user(db, current_user.id, prospect_id)
        if not prospect:
            results.append({"prospect_id": prospect_id, "status": "failed", "error": "Prospect introuvable"})
            failed += 1
            continue

        record = await enrichment_service.enrich(db, current_user.id, prospect)
        if record.status == EnrichmentStatus.COMPLETED.value:
            succeeded += 1
        else:
            failed += 1
        results.append({
            "prospect_id": prospect_id,
            "status": record.status,
            "error": record.error_message,
        })

    return {
        "results": results,
        "succeeded": succeeded,
        "failed": failed,
        "total": len(payload.prospect_ids),
    }


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
