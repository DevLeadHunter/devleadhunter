"""Prospect enrichment routes — on-demand rich data for site generation."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from enums.enrichment_status import EnrichmentStatus
from models.user import User
from schemas.enrichment import ProspectEnrichmentResponse, ProspectEnrichmentUpdate
from scrappers.enrichment_scraper import EnrichmentData
from services.auth_service import get_current_active_user
from services.enrichment_service import enrichment_service

router = APIRouter(prefix="/prospects", tags=["enrichment"])

# Cap a single bulk enrichment request — each item drives a headless browser.
_MAX_BULK_ENRICH = 50

_DISMISSED_ENRICHMENT_REFUSAL = "Prospect écarté : remettez-le dans vos prospects pour l'enrichir."


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
    scraped_data: EnrichmentData | None = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ProspectEnrichmentResponse:
    """Run (or re-run) enrichment for a prospect.

    The desktop app scrapes on the user's own machine (Google blocks datacenter
    IPs) and posts the result as ``scraped_data``; without it the server scrapes
    itself, which is what the web build does.
    """
    prospect = enrichment_service.get_prospect_for_user(db, current_user.id, prospect_id)
    if not prospect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    if prospect.is_dismissed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_DISMISSED_ENRICHMENT_REFUSAL)
    record = await enrichment_service.enrich(db, current_user.id, prospect, scraped_data=scraped_data)
    return ProspectEnrichmentResponse.model_validate(record)


@router.post("/{prospect_id}/enrichment/rehost-photos", response_model=ProspectEnrichmentResponse)
async def rehost_prospect_photos(
    prospect_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ProspectEnrichmentResponse:
    """Move a prospect's already-collected photos to permanent R2 storage, without re-scraping.

    Repairs an enrichment whose Facebook photos are still fbcdn URLs (or predate the R2 rehost): each
    live link is downloaded server-side and rehosted, the user's photo order/selection preserved. The
    demo site must be regenerated afterwards to pick up the new URLs.
    """
    prospect = enrichment_service.get_prospect_for_user(db, current_user.id, prospect_id)
    if not prospect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    record = enrichment_service.get_for_prospect(db, current_user.id, prospect_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No enrichment for this prospect")
    record = await enrichment_service.rehost_existing_photos(db, record)
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


@router.post("/{prospect_id}/enrichment/contact-proposal/confirm", response_model=ProspectEnrichmentResponse)
async def confirm_contact_proposal(
    prospect_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ProspectEnrichmentResponse:
    """Promote the « à confirmer » decision-maker name to the trusted contact."""
    prospect = enrichment_service.get_prospect_for_user(db, current_user.id, prospect_id)
    if not prospect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    record = enrichment_service.get_for_prospect(db, current_user.id, prospect_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No enrichment for this prospect")
    try:
        record = enrichment_service.confirm_proposed_contact(db, record)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ProspectEnrichmentResponse.model_validate(record)


@router.post("/{prospect_id}/enrichment/contact-proposal/reject", response_model=ProspectEnrichmentResponse)
async def reject_contact_proposal(
    prospect_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ProspectEnrichmentResponse:
    """Reject the « à confirmer » name — the same identity is never re-proposed."""
    prospect = enrichment_service.get_prospect_for_user(db, current_user.id, prospect_id)
    if not prospect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect not found")
    record = enrichment_service.get_for_prospect(db, current_user.id, prospect_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No enrichment for this prospect")
    try:
        record = enrichment_service.reject_proposed_contact(db, record)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
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
        if prospect.is_dismissed:
            results.append({"prospect_id": prospect_id, "status": "failed", "error": _DISMISSED_ENRICHMENT_REFUSAL})
            failed += 1
            continue

        record = await enrichment_service.enrich(db, current_user.id, prospect)
        if record.status == EnrichmentStatus.COMPLETED.value:
            succeeded += 1
        else:
            failed += 1
        results.append(
            {
                "prospect_id": prospect_id,
                "status": record.status,
                "error": record.error_message,
            }
        )

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
    # Facebook photos are saved as fbcdn URLs the site can't render; rehost them to R2 on save so newly
    # added FB photos show up on the site instead of being silently dropped.
    if ("photos" in updates or "logo_url" in updates) and enrichment_service.has_unrehostable_photos(record):
        record = await enrichment_service.rehost_existing_photos(db, record)
    return ProspectEnrichmentResponse.model_validate(record)
