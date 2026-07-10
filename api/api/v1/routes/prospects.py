"""
Prospect management routes.
"""
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from models.prospect import (
    Prospect,
    ProspectCreate,
    ProspectUpdate,
    ProspectEnrichRequest,
    ProspectSearchSuggestion,
    ProspectSearchSuggestionsRequest,
)
from models.search import ProspectSearchRequest, ProspectSearchResponse
from models.credit_settings import CreditSettings
from models.prospect_db import ProspectDB
from models.user import User
from services.prospect_service import prospect_service
from services.prospect_enrichment_service import prospect_enrichment_service
from services.scraper_service import scraper_service
from services.auth_service import require_auth
from services.credit_service import credit_service
from services.organization_service import OrganizationError, organization_service
from services.lighthouse_service import LighthouseAuditError, lighthouse_service
from core.database import get_db


router = APIRouter(
    prefix="/prospects",
    tags=["prospects"]
)


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


@router.post(
    "/search",
    response_model=ProspectSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search for prospects (deprecated)",
    description="⚠️ DEPRECATED: Use POST /scraping-jobs instead for better UX with async processing"
)
async def search_prospects(
    request: ProspectSearchRequest,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
) -> ProspectSearchResponse:
    """
    Search for prospects matching the given criteria.
    
    ⚠️ DEPRECATED: This endpoint is synchronous and blocks until scraping is complete.
    Use POST /scraping-jobs instead for better user experience with async processing,
    real-time progress updates, and ability to leave/return to the page.
    
    Args:
        request: Search criteria including category, city, and max results
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        ProspectSearchResponse with matching prospects and statistics
        
    Raises:
        HTTPException: If search fails or insufficient credits
        
    Example:
        >>> POST /prospects/search
        {
            "category": "restaurant",
            "city": "Paris",
            "max_results": 20,
            "source": "pagesjaunes"
        }
    """
    try:
        # Get credit settings
        credit_settings: CreditSettings | None = db.query(CreditSettings).filter(
            CreditSettings.id == 1
        ).first()
        
        if not credit_settings:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Credit settings not configured"
            )
        
        # Calculate total credits needed
        credits_per_search = credit_settings.credits_per_search
        max_credits_needed = credits_per_search + (request.max_results * credit_settings.credits_per_result)
        
        # Check user balance
        user_balance = credit_service.get_user_balance(db, current_user.id)
        
        # For admin users, balance is -1 (unlimited)
        if user_balance != -1:
            if user_balance < credits_per_search:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Insufficient credits. You need at least {credits_per_search} credits to perform a search. Current balance: {user_balance}"
                )
        
        # Run scrapers to get fresh data
        source_value = request.source.value if request.source else None
        
        scraped_prospects = await scraper_service.scrape_all(
            category=request.category or "",
            city=request.city or "",
            max_results=request.max_results,
            source_filter=source_value,
            only_without_website=request.only_without_website,
        )
        
        # Save scraped prospects to database
        prospects = []
        skipped_count = 0
        
        for prospect_data in scraped_prospects:
            # Check for duplicates
            is_duplicate = await prospect_service.check_duplicate(
                db=db,
                name=prospect_data.name,
                city=prospect_data.city,
                user_id=current_user.id
            )
            
            if is_duplicate:
                skipped_count += 1
                # Still include in results but don't save
                continue
            
            # Save to database
            prospect = await prospect_service.create_prospect(
                db=db,
                prospect=prospect_data,
                user_id=current_user.id
            )
            prospects.append(prospect)
        
        # Calculate actual credits needed based on results
        actual_credits_needed = credits_per_search + (len(prospects) * credit_settings.credits_per_result)
        
        # Deduct credits from user account (if not admin)
        if user_balance != -1:
            if user_balance < actual_credits_needed:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=f"Insufficient credits. This search requires {actual_credits_needed} credits. Current balance: {user_balance}"
                )
            
            # Deduct credits
            success = credit_service.use_credits(
                db=db,
                user_id=current_user.id,
                amount=actual_credits_needed,
                description=f"Prospect search: {request.category or 'all'} in {request.city or 'all locations'} ({len(prospects)} results)",
                metadata=f"search_category:{request.category or 'all'},search_city:{request.city or 'all'},results_count:{len(prospects)},skipped:{skipped_count}"
            )
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail="Failed to deduct credits. Please try again."
                )
        
        # Calculate statistics
        has_website = sum(1 for p in prospects if p.website)
        without_website = len(prospects) - has_website
        
        return ProspectSearchResponse(
            total=len(prospects),
            prospects=prospects,
            has_website=has_website,
            without_website=without_website
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get(
    "",
    response_model=List[Prospect],
    summary="List all saved prospects",
    description="Get a list of all prospects saved by the current user"
)
async def list_prospects(
    skip: int = 0,
    limit: int = 1000,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
) -> List[Prospect]:
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


@router.post(
    "/search-suggestions",
    response_model=List[ProspectSearchSuggestion],
    summary="Search businesses on Google Maps",
    description="Return Google Maps business suggestions for autocomplete when adding a prospect manually",
)
async def search_prospect_suggestions(
    request: ProspectSearchSuggestionsRequest,
    current_user: User = Depends(require_auth),
) -> List[ProspectSearchSuggestion]:
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


@router.get(
    "/{prospect_id}",
    response_model=Prospect,
    summary="Get prospect by ID",
    description="Retrieve a specific prospect by its ID"
)
async def get_prospect(
    prospect_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
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
    description="Create a new prospect manually"
)
async def create_prospect(
    prospect: ProspectCreate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
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
    return await prospect_service.create_prospect(
        db=db,
        prospect=prospect,
        user_id=current_user.id,
        organization_id=organization_service.user_org_id(db, current_user.id),
    )


@router.put(
    "/{prospect_id}",
    response_model=Prospect,
    summary="Update a prospect",
    description="Update an existing prospect by ID"
)
async def update_prospect(
    prospect_id: int,
    update_data: ProspectUpdate,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prospect {prospect_id} not found"
        )
    return prospect


@router.delete(
    "/{prospect_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a prospect",
    description="Delete a prospect by ID"
)
async def delete_prospect(
    prospect_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prospect {prospect_id} not found"
        )

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
    row.lighthouse_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return prospect_service._to_models_with_reservers(db, [row])[0]
