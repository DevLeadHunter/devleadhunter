"""Demo site routes for the website builder tunnel."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from models.user import User
from schemas.demo_site import (
    DemoSiteCreateRequest,
    DemoSiteListResponse,
    DemoSitePublicResponse,
    DemoSiteResponse,
    DemoSiteTemplateResponse,
    DemoSiteUpdateRequest,
)
from services.auth_service import get_current_active_user
from services.demo_site_service import demo_site_service

router = APIRouter(prefix="/demo-sites", tags=["demo-sites"])


@router.get("/templates", response_model=List[DemoSiteTemplateResponse])
async def list_demo_templates() -> List[DemoSiteTemplateResponse]:
    """List templates available in the site builder stepper."""
    return [DemoSiteTemplateResponse(**template) for template in demo_site_service.list_templates()]


@router.get("/public/{slug}", response_model=DemoSitePublicResponse)
async def get_public_demo_site(
    slug: str,
    db: Session = Depends(get_db),
) -> DemoSitePublicResponse:
    """Public endpoint consumed by demo.dibodev.fr/{slug}."""
    site = demo_site_service.get_public_by_slug(db, slug)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found or expired")
    return DemoSitePublicResponse.model_validate(site)


@router.get("", response_model=DemoSiteListResponse)
async def list_my_demo_sites(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteListResponse:
    """List demo sites created by the authenticated user."""
    items = demo_site_service.list_for_user(db, current_user.id)
    return DemoSiteListResponse(
        items=[DemoSiteResponse.model_validate(item) for item in items],
        total=len(items),
    )


@router.post("", response_model=DemoSiteResponse, status_code=status.HTTP_201_CREATED)
async def create_demo_site(
    payload: DemoSiteCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Create and provision a demo website from the stepper tunnel."""
    known_templates = {template["id"] for template in demo_site_service.list_templates()}
    if payload.template_id not in known_templates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown template_id")

    try:
        site = await demo_site_service.create_demo_site(
            db,
            user=current_user,
            business_name=payload.business_name,
            template_id=payload.template_id,
            phone=payload.phone,
            email=str(payload.email),
            city=payload.city,
            description=payload.description,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DemoSiteResponse.model_validate(site)


@router.post("/{demo_site_id}/verify", response_model=DemoSiteResponse)
async def verify_demo_site(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Re-run live URL checks for a demo site owned by the current user."""
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    if site.status in {DemoSiteStatus.DELETED.value, DemoSiteStatus.EXPIRED.value}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Demo site can no longer be verified")

    site = await demo_site_service.verify_and_update(db, site)
    return DemoSiteResponse.model_validate(site)


@router.get("/{demo_site_id}", response_model=DemoSiteResponse)
async def get_demo_site(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Get a single demo site owned by the current user."""
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    return DemoSiteResponse.model_validate(site)


def _get_editable_demo_site(db: Session, user_id: int, demo_site_id: int):
    """Fetch a demo site that can be edited or regenerated."""
    site = demo_site_service.get_for_user(db, user_id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    if site.status in {DemoSiteStatus.DELETED.value, DemoSiteStatus.EXPIRED.value, DemoSiteStatus.PROVISIONING.value}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Demo site cannot be modified")
    return site


@router.patch("/{demo_site_id}", response_model=DemoSiteResponse)
async def update_demo_site(
    demo_site_id: int,
    payload: DemoSiteUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Update demo site business fields and regenerate its content."""
    site = _get_editable_demo_site(db, current_user.id, demo_site_id)

    if payload.template_id is not None:
        known_templates = {template["id"] for template in demo_site_service.list_templates()}
        if payload.template_id not in known_templates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown template_id")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    try:
        site = await demo_site_service.update_demo_site(db, site, **update_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DemoSiteResponse.model_validate(site)


@router.post("/{demo_site_id}/regenerate", response_model=DemoSiteResponse)
async def regenerate_demo_site(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Rebuild demo site content from stored fields without changing them."""
    site = _get_editable_demo_site(db, current_user.id, demo_site_id)
    site = await demo_site_service.regenerate_demo_site(db, site)
    return DemoSiteResponse.model_validate(site)


@router.delete("/{demo_site_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_demo_site(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a demo site owned by the current user."""
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    await demo_site_service.delete_demo_site(db, site)
