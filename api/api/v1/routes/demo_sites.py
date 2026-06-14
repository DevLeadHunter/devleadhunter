"""Demo site routes for the website builder tunnel."""
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from models.prospect_db import ProspectDB
from models.user import User
from schemas.demo_site import (
    DemoSiteCreateRequest,
    DemoSiteListResponse,
    DemoSitePreviewRequest,
    DemoSitePreviewResponse,
    DemoSitePublicResponse,
    DemoSiteResponse,
    DemoSiteTemplateResponse,
    DemoSiteTheme,
    DemoSiteUpdateRequest,
)
from services.auth_service import get_current_active_user
from services.demo_site_service import demo_site_service

router = APIRouter(prefix="/demo-sites", tags=["demo-sites"])

# Cap a single bulk site-generation request — each item provisions a CMS space.
_MAX_BULK_GENERATE = 25


class BulkDemoSiteCreateRequest(BaseModel):
    """Payload to generate demo sites for several prospects with one template."""

    prospect_ids: list[int] = Field(..., min_length=1, max_length=_MAX_BULK_GENERATE)
    template_id: str = Field(default="plumber-simple", max_length=64)
    theme: DemoSiteTheme | None = None
    invite_client_to_cms: bool = Field(default=False)


def _serialize_demo_site(site) -> DemoSiteResponse:
    """Build API response including theme extracted from content JSON."""
    payload = DemoSiteResponse.model_validate(site).model_dump()
    theme_raw = (site.content_json or {}).get("theme") if isinstance(site.content_json, dict) else None
    if isinstance(theme_raw, dict):
        payload["theme"] = {
            "primary": str(theme_raw.get("primary", "#0284c7")),
            "secondary": str(theme_raw.get("secondary", "#0f172a")),
            "accent": str(theme_raw.get("accent", "#f59e0b")),
        }
    return DemoSiteResponse(**payload)


@router.get("/templates", response_model=List[DemoSiteTemplateResponse])
async def list_demo_templates() -> List[DemoSiteTemplateResponse]:
    """List templates available in the site builder stepper."""
    return [DemoSiteTemplateResponse(**template) for template in demo_site_service.list_templates()]


@router.post("/preview", response_model=DemoSitePreviewResponse)
async def preview_demo_site(payload: DemoSitePreviewRequest) -> DemoSitePreviewResponse:
    """Build demo site content for client-side preview without provisioning."""
    known_templates = {template["id"] for template in demo_site_service.list_templates()}
    if payload.template_id not in known_templates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown template_id")

    theme_dict = payload.theme.model_dump() if payload.theme else None
    content_json = demo_site_service.build_preview_content(
        business_name=payload.business_name,
        template_id=payload.template_id,
        phone=payload.phone,
        email=str(payload.email) if payload.email else None,
        city=payload.city,
        description=payload.description,
        theme=theme_dict,
    )
    return DemoSitePreviewResponse(template_id=payload.template_id, content_json=content_json)


@router.get("/public/by-domain", response_model=DemoSitePublicResponse)
async def get_public_demo_site_by_domain(
    host: str,
    db: Session = Depends(get_db),
) -> DemoSitePublicResponse:
    """Public endpoint to serve a sold site on its own domain (host → site)."""
    site = demo_site_service.get_public_by_domain(db, host)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No site for this domain")
    payload = DemoSitePublicResponse.model_validate(site).model_dump()
    if site.storyblok_preview_token:
        payload["storyblok_region"] = settings.storyblok_region
    return DemoSitePublicResponse(**payload)


@router.get("/public/{slug}", response_model=DemoSitePublicResponse)
async def get_public_demo_site(
    slug: str,
    db: Session = Depends(get_db),
) -> DemoSitePublicResponse:
    """Public endpoint consumed by demo.dibodev.fr/{slug}."""
    site = demo_site_service.get_public_by_slug(db, slug)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found or expired")
    payload = DemoSitePublicResponse.model_validate(site).model_dump()
    if site.storyblok_preview_token:
        payload["storyblok_region"] = settings.storyblok_region
    return DemoSitePublicResponse(**payload)


@router.get("", response_model=DemoSiteListResponse)
async def list_my_demo_sites(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteListResponse:
    """List demo sites created by the authenticated user."""
    items = demo_site_service.list_for_user(db, current_user.id)
    return DemoSiteListResponse(
        items=[_serialize_demo_site(item) for item in items],
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
            invite_client_to_cms=payload.invite_client_to_cms,
            theme=payload.theme.model_dump() if payload.theme else None,
            prospect_id=payload.prospect_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_demo_site(site)


@router.post("/bulk")
async def create_demo_sites_bulk(
    payload: BulkDemoSiteCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Generate demo sites for several prospects using the same template.

    Runs sequentially (each item provisions a CMS space and verifies the URL).
    Prospects without an email are skipped and reported (the demo record needs a
    client email); missing prospects and provisioning errors are reported per item.
    """
    known_templates = {template["id"] for template in demo_site_service.list_templates()}
    if payload.template_id not in known_templates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown template_id")

    theme_dict = payload.theme.model_dump() if payload.theme else None
    results: list[dict[str, Any]] = []
    created = 0
    failed = 0
    skipped_no_email: list[dict[str, Any]] = []

    for prospect_id in payload.prospect_ids:
        prospect: ProspectDB | None = (
            db.query(ProspectDB)
            .filter(ProspectDB.id == prospect_id, ProspectDB.user_id == current_user.id)
            .first()
        )
        if not prospect:
            results.append({"prospect_id": prospect_id, "status": "failed", "error": "Prospect introuvable"})
            failed += 1
            continue
        if not prospect.email or not prospect.email.strip():
            skipped_no_email.append({"id": prospect_id, "name": prospect.name or ""})
            continue

        try:
            site = await demo_site_service.create_demo_site(
                db,
                user=current_user,
                business_name=prospect.name or f"Prospect {prospect_id}",
                template_id=payload.template_id,
                phone=prospect.phone,
                email=prospect.email,
                city=prospect.city,
                description=None,
                invite_client_to_cms=payload.invite_client_to_cms,
                theme=theme_dict,
                prospect_id=prospect.id,
            )
            results.append({
                "prospect_id": prospect_id,
                "demo_site_id": site.id,
                "slug": site.slug,
                "status": site.status,
            })
            created += 1
        except Exception as exc:  # noqa: BLE001 — report per item, never fail the whole batch
            results.append({"prospect_id": prospect_id, "status": "failed", "error": str(exc)})
            failed += 1

    return {
        "results": results,
        "created": created,
        "failed": failed,
        "skipped_no_email": skipped_no_email,
        "total": len(payload.prospect_ids),
    }


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
    return _serialize_demo_site(site)


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
    return _serialize_demo_site(site)


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

    theme_data = update_data.pop("theme", None)
    if theme_data is not None:
        update_data["theme"] = theme_data

    try:
        site = await demo_site_service.update_demo_site(db, site, **update_data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_demo_site(site)


@router.post("/{demo_site_id}/regenerate", response_model=DemoSiteResponse)
async def regenerate_demo_site(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Rebuild demo site content from stored fields without changing them."""
    site = _get_editable_demo_site(db, current_user.id, demo_site_id)
    site = await demo_site_service.regenerate_demo_site(db, site)
    return _serialize_demo_site(site)


@router.post("/{demo_site_id}/invite-cms", response_model=DemoSiteResponse)
async def invite_demo_site_client_to_cms(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Send a Storyblok CMS invitation to the demo site client."""
    site = _get_editable_demo_site(db, current_user.id, demo_site_id)
    try:
        site = await demo_site_service.invite_client_to_cms(db, site)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_demo_site(site)


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
