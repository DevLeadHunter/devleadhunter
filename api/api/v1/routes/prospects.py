"""
Prospect management routes.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from models.prospect import (
    Prospect,
    ProspectCreate,
    ProspectEmailsUpdate,
    ProspectEnrichRequest,
    ProspectPhonesUpdate,
    ProspectSearchSuggestion,
    ProspectSearchSuggestionsRequest,
    ProspectUpdate,
)
from models.prospect_db import ProspectDB
from models.user import User
from schemas.sourcing import WebsiteEquipmentScanRequest, WebsiteEquipmentScanResponse
from services.auth_service import require_auth
from services.enrichment_service import enrichment_service
from services.lighthouse_service import LighthouseAuditError, lighthouse_service
from services.organization_service import OrganizationError, organization_service
from services.prospect_emails import set_prospect_emails
from services.prospect_enrichment_service import prospect_enrichment_service
from services.prospect_phones import set_prospect_phones
from services.prospect_service import prospect_service
from services.website_equipment_service import website_equipment_service

router = APIRouter(prefix="/prospects", tags=["prospects"])


def _get_visible_db_prospect(db: Session, prospect_id: int, user: User) -> ProspectDB:
    """Load a prospect row visible to the user (their own, or shared with their org).

    Raises:
        HTTPException: 404 when the prospect does not exist or belongs to
            neither the user nor their organization (no cross-org leak).
    """
    row = db.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prospect {prospect_id} not found",
        )
    if row.user_id != user.id:
        org_id = organization_service.user_org_id(db, user.id)
        if org_id is None or row.organization_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Prospect {prospect_id} not found",
            )
    return row


def _assert_not_reserved_by_other(db: Session, user: User, row: ProspectDB) -> None:
    """403 when another organization member currently holds the prospect."""
    try:
        organization_service.assert_prospect_actionable(db, user.id, row)
    except OrganizationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get(
    "",
    response_model=list[Prospect],
    summary="List all saved prospects",
    description="Get a list of all prospects saved by the current user",
)
async def list_prospects(
    skip: int = 0, limit: int = 1000, current_user: User = Depends(require_auth), db: Session = Depends(get_db)
) -> list[Prospect]:
    """
    Get all saved prospects for the current user.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of saved prospects
    """
    return await prospect_service.get_all_prospects(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        organization_id=organization_service.user_org_id(db, current_user.id),
    )


@router.get(
    "/dismissed",
    response_model=list[Prospect],
    summary="List the prospects set aside",
    description="The « écartés » prospects: kept so no search finds them again, out of every other list.",
)
async def list_dismissed_prospects(
    current_user: User = Depends(require_auth), db: Session = Depends(get_db)
) -> list[Prospect]:
    """List the prospects set aside, the latest first."""
    return prospect_service.get_dismissed_prospects(
        db, current_user.id, organization_service.user_org_id(db, current_user.id)
    )


@router.post(
    "/search-suggestions",
    response_model=list[ProspectSearchSuggestion],
    summary="Search businesses on Google Maps",
    description="Return Google Maps business suggestions for autocomplete when adding a prospect manually",
)
async def search_prospect_suggestions(
    request: ProspectSearchSuggestionsRequest,
    current_user: User = Depends(require_auth),
) -> list[ProspectSearchSuggestion]:
    """Search Google Maps for business name suggestions without saving a prospect."""
    del current_user
    try:
        return await prospect_enrichment_service.search_suggestions(
            query=request.query,
            city=request.city,
            max_results=request.max_results,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {exc}",
        ) from exc


@router.post(
    "/enrich",
    response_model=ProspectCreate,
    summary="Enrich a prospect from Google Maps",
    description="Pre-fill prospect fields from a Google Maps link and/or business name",
)
async def enrich_prospect(
    request: ProspectEnrichRequest,
    current_user: User = Depends(require_auth),
) -> ProspectCreate:
    """Fetch public business details from Google Maps without saving the prospect."""
    del current_user
    try:
        return await prospect_enrichment_service.enrich_from_google(
            business_name=request.business_name,
            google_maps_url=request.google_maps_url,
            city=request.city,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Enrichment failed: {exc}",
        ) from exc


class DoNotContactRequest(BaseModel):
    """Payload for POST /prospects/{id}/do-not-contact."""

    enabled: bool = Field(..., description="True to stop all outreach to this prospect, False to re-allow it")
    reason: str | None = Field(None, max_length=500, description="Optional note on why contact is stopped")


class SmsAutoExclusionRequest(BaseModel):
    """Payload for POST /prospects/{id}/sms-auto-exclusion."""

    excluded: bool = Field(..., description="True to skip every automated SMS for this prospect, False to re-allow")


class DismissalRequest(BaseModel):
    """Payload for POST /prospects/{id}/dismissal."""

    reason: str = Field(..., min_length=1, max_length=500, description="Why the prospect is set aside")


@router.get(
    "/{prospect_id}",
    response_model=Prospect,
    summary="Get prospect by ID",
    description="Retrieve a specific prospect by its ID",
)
async def get_prospect(
    prospect_id: int, current_user: User = Depends(require_auth), db: Session = Depends(get_db)
) -> Prospect:
    """
    Get a prospect by ID.

    Args:
        prospect_id: Unique prospect identifier
        current_user: Current authenticated user
        db: Database session

    Returns:
        Prospect object

    Raises:
        HTTPException: If prospect not found or not owned by user
    """
    # Visibility: own prospect, or shared with the caller's organization.
    row = _get_visible_db_prospect(db, prospect_id, current_user)
    return prospect_service._to_models_with_reservers(db, [row])[0]


@router.post(
    "",
    response_model=Prospect,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new prospect",
    description="Create a new prospect manually",
)
async def create_prospect(
    prospect: ProspectCreate, current_user: User = Depends(require_auth), db: Session = Depends(get_db)
) -> Prospect:
    """
    Create a new prospect manually.

    Args:
        prospect: Prospect data to create
        current_user: Current authenticated user
        db: Database session

    Returns:
        Created prospect with generated ID
    """
    created = await prospect_service.create_prospect(
        db=db,
        prospect=prospect,
        user_id=current_user.id,
        organization_id=organization_service.user_org_id(db, current_user.id),
    )
    enrichment_service.schedule_contact_resolution([created.id])
    return created


@router.put(
    "/{prospect_id}",
    response_model=Prospect,
    summary="Update a prospect",
    description="Update an existing prospect by ID",
)
async def update_prospect(
    prospect_id: int,
    update_data: ProspectUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Prospect:
    """
    Update a prospect.

    Args:
        prospect_id: Prospect ID to update
        update_data: Fields to update
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated prospect

    Raises:
        HTTPException: If prospect not found or not owned by user
    """
    # Visible to the org, but blocked while another member holds the prospect.
    row = _get_visible_db_prospect(db, prospect_id, current_user)
    _assert_not_reserved_by_other(db, current_user, row)

    prospect = await prospect_service.update_prospect(db, prospect_id, update_data)
    if not prospect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prospect {prospect_id} not found")
    return prospect


@router.put(
    "/{prospect_id}/emails",
    response_model=Prospect,
    summary="Replace a prospect's email list",
    description="Set the full ordered email list (first = primary). Covers reorder, add and remove.",
)
async def update_prospect_emails(
    prospect_id: int,
    payload: ProspectEmailsUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Prospect:
    """Replace a prospect's ordered email list; ``emails[0]`` becomes the primary.

    Args:
        prospect_id: Prospect to edit.
        payload: The new ordered email list.
        current_user: Authenticated caller.
        db: Database session.

    Returns:
        The updated prospect.

    Raises:
        HTTPException: 404 when not visible, 403 when reserved by another member.
    """
    row = _get_visible_db_prospect(db, prospect_id, current_user)
    _assert_not_reserved_by_other(db, current_user, row)

    set_prospect_emails(row, list(payload.emails))
    db.add(row)
    db.commit()
    db.refresh(row)
    return prospect_service._to_models_with_reservers(db, [row])[0]


@router.put(
    "/{prospect_id}/phones",
    response_model=Prospect,
    summary="Replace a prospect's phone list",
    description="Set the full ordered phone list (first = primary). Covers reorder, add and remove.",
)
async def update_prospect_phones(
    prospect_id: int,
    payload: ProspectPhonesUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Prospect:
    """Replace a prospect's ordered phone list; ``phones[0]`` becomes the primary.

    Args:
        prospect_id: Prospect to edit.
        payload: The new ordered phone list.
        current_user: Authenticated caller.
        db: Database session.

    Returns:
        The updated prospect.

    Raises:
        HTTPException: 404 when not visible, 403 when reserved by another member.
    """
    row = _get_visible_db_prospect(db, prospect_id, current_user)
    _assert_not_reserved_by_other(db, current_user, row)

    set_prospect_phones(row, list(payload.phones))
    db.add(row)
    db.commit()
    db.refresh(row)
    return prospect_service._to_models_with_reservers(db, [row])[0]


@router.delete(
    "/{prospect_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a prospect",
    description="Delete a prospect by ID",
)
async def delete_prospect(
    prospect_id: int, current_user: User = Depends(require_auth), db: Session = Depends(get_db)
) -> None:
    """
    Delete a prospect.

    Args:
        prospect_id: Prospect ID to delete
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If prospect not found or not owned by user
    """
    # Deleting stays creator-only (destructive), and is blocked while reserved
    # by another member.
    row = _get_visible_db_prospect(db, prospect_id, current_user)
    if row.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seul le créateur du prospect peut le supprimer",
        )
    _assert_not_reserved_by_other(db, current_user, row)

    deleted = await prospect_service.delete_prospect(db, prospect_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prospect {prospect_id} not found")


@router.post(
    "/{prospect_id}/reserve",
    response_model=Prospect,
    summary="Reserve a prospect",
    description="Take the prospect for yourself — other organization members see it locked",
)
async def reserve_prospect(
    prospect_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Prospect:
    """Reserve a shared prospect for the caller (anti double-outreach)."""
    row = _get_visible_db_prospect(db, prospect_id, current_user)
    try:
        row = organization_service.reserve_prospect(db, current_user.id, row)
    except OrganizationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return prospect_service._to_models_with_reservers(db, [row])[0]


@router.delete(
    "/{prospect_id}/reserve",
    response_model=Prospect,
    summary="Release a prospect reservation",
    description="Free the prospect so another organization member can take it",
)
async def release_prospect(
    prospect_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Prospect:
    """Release the caller's reservation (org owner can force-release)."""
    row = _get_visible_db_prospect(db, prospect_id, current_user)
    try:
        row = organization_service.release_prospect(db, current_user.id, row)
    except OrganizationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return prospect_service._to_models_with_reservers(db, [row])[0]


@router.post(
    "/{prospect_id}/do-not-contact",
    response_model=Prospect,
    summary="Stop or resume outreach to a prospect",
    description="Mark « ne plus contacter » (blocks campaigns + SMS and holds back pending sends), or lift it.",
)
async def set_prospect_do_not_contact(
    prospect_id: int,
    request: DoNotContactRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Prospect:
    """Stop (or resume) all outreach to a prospect.

    Raises:
        HTTPException: 404 when not visible, 403 when reserved by another member.
    """
    row = _get_visible_db_prospect(db, prospect_id, current_user)
    _assert_not_reserved_by_other(db, current_user, row)
    prospect = await prospect_service.set_do_not_contact(
        db, prospect_id, user_id=current_user.id, enabled=request.enabled, reason=request.reason
    )
    if not prospect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prospect {prospect_id} not found")
    return prospect


@router.post(
    "/{prospect_id}/dismissal",
    response_model=Prospect,
    summary="Set a prospect aside",
    description="« Écarter » a prospect: kept so no search finds it again, out of every list, campaign and enrichment.",
)
async def dismiss_prospect(
    prospect_id: int,
    request: DismissalRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Prospect:
    """Set a prospect aside, its pending sends held back.

    Raises:
        HTTPException: 404 when not visible, 403 when reserved by another member.
    """
    row = _get_visible_db_prospect(db, prospect_id, current_user)
    _assert_not_reserved_by_other(db, current_user, row)
    prospect = prospect_service.dismiss(db, prospect_id, reason=request.reason, dismissed_by_user_id=current_user.id)
    if not prospect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prospect {prospect_id} not found")
    return prospect


@router.delete(
    "/{prospect_id}/dismissal",
    response_model=Prospect,
    summary="Take a prospect back",
    description="Bring an « écarté » prospect back to the lists, campaigns and enrichment.",
)
async def restore_prospect(
    prospect_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Prospect:
    """Take a prospect back from the « Écartés » tab.

    Raises:
        HTTPException: 404 when not visible, 403 when reserved by another member.
    """
    row = _get_visible_db_prospect(db, prospect_id, current_user)
    _assert_not_reserved_by_other(db, current_user, row)
    prospect = prospect_service.restore(db, prospect_id, user_id=current_user.id)
    if not prospect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prospect {prospect_id} not found")
    return prospect


@router.post(
    "/{prospect_id}/sms-auto-exclusion",
    response_model=Prospect,
    summary="Exclude or re-include a prospect in the automated SMS",
    description="Opt one prospect out of every automated SMS (relance J+30 and cold) — campaigns and email stay.",
)
async def set_prospect_sms_auto_exclusion(
    prospect_id: int,
    request: SmsAutoExclusionRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Prospect:
    """Exclude (or re-include) a prospect from every automated SMS.

    Raises:
        HTTPException: 404 when not visible, 403 when reserved by another member.
    """
    row = _get_visible_db_prospect(db, prospect_id, current_user)
    _assert_not_reserved_by_other(db, current_user, row)
    prospect = await prospect_service.set_sms_auto_excluded(
        db, prospect_id, user_id=current_user.id, excluded=request.excluded
    )
    if not prospect:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Prospect {prospect_id} not found")
    return prospect


@router.post(
    "/{prospect_id}/lighthouse-audit",
    response_model=Prospect,
    summary="Audit the prospect's existing website",
    description="Run a PageSpeed Insights (Lighthouse) audit on the prospect's website — slow (30-60s)",
)
async def lighthouse_audit(
    prospect_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Prospect:
    """Audit the prospect's existing website and persist the result.

    Raises:
        HTTPException: 400 when the prospect has no website, 502 when the
            audit itself fails (site unreachable, PSI error).
    """
    row = _get_visible_db_prospect(db, prospect_id, current_user)
    _assert_not_reserved_by_other(db, current_user, row)
    if not row.website or not row.website.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce prospect n'a pas de site web à auditer",
        )

    try:
        result = await lighthouse_service.audit_website(row.website)
    except LighthouseAuditError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    row.lighthouse_json = result
    row.lighthouse_at = datetime.now(UTC)
    db.commit()
    db.refresh(row)
    return prospect_service._to_models_with_reservers(db, [row])[0]


@router.post(
    "/{prospect_id}/website-equipment",
    response_model=Prospect,
    summary="Scan the prospect's website for a chat widget and a contact form",
    description="Read the home page (and the contact page it links to) — a chat widget means « déjà équipé »",
)
async def scan_website_equipment(
    prospect_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> Prospect:
    """Scan one prospect's website now and persist what was found.

    Raises:
        HTTPException: 400 when there is no live website to scan, 502 when the
            site cannot be read (offline, blocked, not HTML).
    """
    row = _get_visible_db_prospect(db, prospect_id, current_user)
    _assert_not_reserved_by_other(db, current_user, row)
    if not website_equipment_service.is_scannable(row):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce prospect n'a pas de site en ligne à analyser",
        )
    if not await website_equipment_service.refresh_prospect(db, row):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Le site n'a pas pu être lu (hors ligne, protégé ou pas une page web)",
        )
    db.refresh(row)
    return prospect_service._to_models_with_reservers(db, [row])[0]


@router.post(
    "/website-equipment/scan",
    response_model=WebsiteEquipmentScanResponse,
    summary="Scan several prospects' websites in the background",
)
async def scan_websites_equipment(
    payload: WebsiteEquipmentScanRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> WebsiteEquipmentScanResponse:
    """Queue a background scan for the visible prospects that have a live website."""
    scannable_ids: list[int] = []
    for prospect_id in dict.fromkeys(payload.prospect_ids):
        try:
            row = _get_visible_db_prospect(db, prospect_id, current_user)
        except HTTPException:
            continue
        if website_equipment_service.is_scannable(row):
            scannable_ids.append(row.id)
    website_equipment_service.schedule_refresh(scannable_ids)
    return WebsiteEquipmentScanResponse(scheduled=len(scannable_ids))
