"""Demo site routes for the website builder tunnel."""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from models.demo_site import DemoSite
from models.prospect_db import ProspectDB
from models.user import User
from schemas.demo_site import (
    DemoSiteCreateRequest,
    DemoSiteDesktopVideoRequestResponse,
    DemoSiteImagesResponse,
    DemoSiteImagesUpdateRequest,
    DemoSiteListResponse,
    DemoSitePreviewRequest,
    DemoSitePreviewResponse,
    DemoSitePublicResponse,
    DemoSiteResponse,
    DemoSiteServiceCardsResponse,
    DemoSiteServiceCardsSuggestionResponse,
    DemoSiteTemplateResponse,
    DemoSiteTheme,
    DemoSiteUpdateRequest,
    DemoSiteVideoStateResponse,
)
from schemas.prospection_video import ProspectionVideoDesktopFailureRequest
from services.auth_service import get_current_active_user
from services.brand_color_service import brand_color_service
from services.demo_site_service import demo_site_service, reenqueue_campaigns_after_demo_ready
from services.demo_video_service import (
    demo_video_service,
    has_ready_video,
    public_thumbnail_url,
    public_video_file_url,
    video_page_url,
)
from services.email_variables import EmailVariables
from services.presenter_video_service import presenter_video_service
from services.prospect_phones import first_mobile_e164
from services.prospect_search.desktop_app_presence import desktop_app_presence
from services.prospection_video_desktop_relay import demo_video_desktop_relay
from services.prospection_video_service import ALREADY_BUILDING_MESSAGE
from services.r2_storage_service import r2_storage
from services.service_card_suggestion_service import ServiceCardsUnavailableError
from services.site_export_service import site_export_service
from services.site_legal import site_legal_notice_service
from services.storyblok_service import StoryblokProvisionError, storyblok_service
from services.video_pipeline import VideoGenerationError

logger = logging.getLogger(__name__)

# Fixed budget for the Storyblok editor sequence; the rest of the timeline is the
# site scroll. The sidecar pads/trims the background to the exact total anyway.
_EDITOR_SEQUENCE_BUDGET_SECONDS = 17.0
_MIN_SITE_SCROLL_SECONDS = 6.0

router = APIRouter(prefix="/demo-sites", tags=["demo-sites"])

# Cap a single bulk site-generation request — each item provisions a CMS space.
_MAX_BULK_GENERATE = 25


class BulkDemoSiteCreateRequest(BaseModel):
    """Payload to generate demo sites for several prospects with one template."""

    prospect_ids: list[int] = Field(..., min_length=1, max_length=_MAX_BULK_GENERATE)
    template_id: str = Field(default="plumber-signature", max_length=64)
    theme: DemoSiteTheme | None = None
    invite_client_to_cms: bool = Field(default=False)


class DemoSiteReviewRequest(BaseModel):
    """Payload for the operator's manual "good to send" sign-off toggle."""

    reviewed: bool = Field(default=True)


def _serialize_demo_site(db: Session, site: DemoSite, *, include_brand_color: bool = False) -> DemoSiteResponse:
    """
    One site as the dashboard reads it, its video compared with the website clip in use.

    Args:
        db: Active database session.
        site: The demo site.
        include_brand_color: Whether to extract the prospect's logo colour (see :func:`_demo_site_response`).

    Returns:
        The site's response.
    """
    clip_in_use_since = demo_video_service.clip_in_use_since(db, site.user_id)
    return _demo_site_response(site, clip_in_use_since, include_brand_color=include_brand_color)


def _demo_site_response(
    site: DemoSite, clip_in_use_since: datetime | None, *, include_brand_color: bool = False
) -> DemoSiteResponse:
    """Build API response including theme extracted from content JSON.

    ``include_brand_color`` extracts the prospect's logo colour (a download) for the Logo/Template
    action-colour picker — only the single-site detail/update paths ask for it, never list views.
    ``clip_in_use_since`` is when the website clip in use was chosen: a video published before was made with
    an older clip.
    """
    payload = DemoSiteResponse.model_validate(site).model_dump()
    content = site.content_json if isinstance(site.content_json, dict) else {}
    # ``theme`` only exists once the user edited colours; a generated site stores its real
    # colours (template defaults + brand colour) under ``palette`` — without this fallback the
    # editor shows the app-default blue/navy instead of the site's actual published colours.
    theme_raw = content.get("theme")
    if not isinstance(theme_raw, dict):
        theme_raw = content.get("palette")
    if isinstance(theme_raw, dict):
        payload["theme"] = {
            "primary": str(theme_raw.get("primary", "#0284c7")),
            "secondary": str(theme_raw.get("secondary", "#0f172a")),
            "accent": str(theme_raw.get("accent", "#f59e0b")),
        }
    if include_brand_color:
        logo = content.get("logo")
        if isinstance(logo, str) and logo.strip():
            payload["brand_color"] = brand_color_service.extract_brand_color(logo)
    if has_ready_video(site):
        payload["video_page_url"] = video_page_url(site.slug)
        payload["video_thumbnail_url"] = public_thumbnail_url(site.slug, site.video_generated_at)
    payload["is_video_desktop_build_started"] = demo_video_service.is_desktop_build_started(site)
    payload["is_video_waiting_for_storyblok_space"] = demo_video_service.is_waiting_for_storyblok_space(site)
    payload["is_video_made_with_older_clip"] = demo_video_service.is_made_with_older_clip(site, clip_in_use_since)
    return DemoSiteResponse(**payload)


def _refuse_while_desktop_builds(site: DemoSite) -> None:
    """Refuse to withdraw or delete a video the owner's desktop app is building: it would publish it anyway."""
    if demo_video_service.is_desktop_build_started(site):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=ALREADY_BUILDING_MESSAGE)


@router.get("/templates", response_model=list[DemoSiteTemplateResponse])
async def list_demo_templates() -> list[DemoSiteTemplateResponse]:
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
        country=payload.country,
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
    payload["content_json"] = demo_site_service.content_json_for_public(db, site)
    payload["legal"] = site_legal_notice_service.build_for_site(db, site, payload["content_json"])
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
    payload["content_json"] = demo_site_service.content_json_for_public(db, site)
    payload["legal"] = site_legal_notice_service.build_for_site(db, site, payload["content_json"])
    if site.storyblok_preview_token:
        payload["storyblok_region"] = settings.storyblok_region
    payload["video_available"] = has_ready_video(site)
    if payload["video_available"]:
        # URLs R2 : le lecteur charge la vidéo depuis Cloudflare, pas depuis l'API.
        payload["video_url"] = public_video_file_url(site.slug)
        payload["video_thumbnail_url"] = public_thumbnail_url(site.slug, site.video_generated_at)
    payload["sale_price_label"] = demo_site_service.sale_price_label(db, site)
    payload["expiry_date_label"] = demo_site_service.expiry_date_label(site)
    if site.user is not None:
        payload["owner_name"] = site.user.name
        payload["owner_company_name"] = site.user.company_name
        payload["owner_company_website_url"] = site.user.company_website_url
        payload["owner_contact_phone"] = site.user.contact_phone
        payload["owner_contact_email"] = site.user.contact_email
        # Guarded on the R2 public base so a dev setup without R2 never 500s here.
        if site.user.profile_photo_path and (settings.r2_public_base_url or "").strip():
            payload["owner_profile_photo_url"] = r2_storage.public_url(site.user.profile_photo_path)
    return DemoSitePublicResponse(**payload)


@router.get("/public/{slug}/video.mp4")
async def stream_public_demo_video(
    slug: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """
    Redirect to the prospection video on R2.

    Kept as a permanent redirect target because emails already sent embed this
    API URL — the bytes themselves are served by Cloudflare, never by the VPS.
    """
    site = demo_site_service.get_public_by_slug(db, slug)
    if not site or not has_ready_video(site):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    return RedirectResponse(url=public_video_file_url(site.slug), status_code=status.HTTP_302_FOUND)


@router.get("/public/{slug}/video-thumbnail.jpg")
async def serve_public_demo_video_thumbnail(
    slug: str,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Redirect to the personalised email thumbnail ({vignette_video} image) on R2."""
    site = demo_site_service.get_public_by_slug(db, slug)
    if not site or not has_ready_video(site):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found")
    return RedirectResponse(
        url=public_thumbnail_url(site.slug, site.video_generated_at), status_code=status.HTTP_302_FOUND
    )


@router.get("", response_model=DemoSiteListResponse)
async def list_my_demo_sites(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteListResponse:
    """List demo sites created by the authenticated user."""
    items = demo_site_service.list_for_user(db, current_user.id)
    clip_in_use_since = demo_video_service.clip_in_use_since(db, current_user.id)
    return DemoSiteListResponse(
        items=[_demo_site_response(item, clip_in_use_since) for item in items],
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
            email=str(payload.email) if payload.email else None,
            city=payload.city,
            description=payload.description,
            invite_client_to_cms=payload.invite_client_to_cms,
            theme=payload.theme.model_dump() if payload.theme else None,
            prospect_id=payload.prospect_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    reenqueue_campaigns_after_demo_ready(db, site.prospect_id, site.user_id)
    return _serialize_demo_site(db, site)


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
            db.query(ProspectDB).filter(ProspectDB.id == prospect_id, ProspectDB.user_id == current_user.id).first()
        )
        if not prospect:
            results.append({"prospect_id": prospect_id, "status": "failed", "error": "Prospect introuvable"})
            failed += 1
            continue
        # Generate for anyone reachable — by email, or by SMS (a mobile 06/07 for a cold SMS).
        # Only a prospect with neither is skipped (there is no way to send them the link).
        has_email = bool(prospect.email and prospect.email.strip())
        if not has_email and first_mobile_e164(prospect) is None:
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
            results.append(
                {
                    "prospect_id": prospect_id,
                    "demo_site_id": site.id,
                    "slug": site.slug,
                    "status": site.status,
                }
            )
            created += 1
            reenqueue_campaigns_after_demo_ready(db, site.prospect_id, site.user_id)
        except Exception as exc:
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
    return _serialize_demo_site(db, site)


@router.post("/{demo_site_id}/review", response_model=DemoSiteResponse)
async def review_demo_site(
    demo_site_id: int,
    payload: DemoSiteReviewRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Record (or clear) the operator's manual "good to send" sign-off for a site.

    Surfaced in the campaign forecast so the operator can tick a site off after checking it,
    ahead of the automatic send. Independent from ``/verify`` (the automated live-URL check).
    """
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")

    site = demo_site_service.set_reviewed(db, site, payload.reviewed)
    return _serialize_demo_site(db, site)


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
    return _serialize_demo_site(db, site, include_brand_color=True)


@router.get("/{demo_site_id}/export")
async def export_demo_site_code(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Response:
    """Download the generated site's source as a standalone, runnable zip.

    Rebuilds a self-contained fork of the template with the client's ``content_json``
    baked in (see ``site_export_service``) — meant for bespoke work after a sale.
    """
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    try:
        data, filename = await site_export_service.build_export(site)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Site code export failed for slug=%s", site.slug)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Échec de la récupération du code de la template. Réessayez plus tard.",
        ) from exc
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
    return _serialize_demo_site(db, site, include_brand_color=True)


@router.post("/{demo_site_id}/regenerate", response_model=DemoSiteResponse)
async def regenerate_demo_site(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Rebuild demo site content from stored fields without changing them."""
    site = _get_editable_demo_site(db, current_user.id, demo_site_id)
    site = await demo_site_service.regenerate_demo_site(db, site)
    reenqueue_campaigns_after_demo_ready(db, site.prospect_id, site.user_id)
    return _serialize_demo_site(db, site, include_brand_color=True)


@router.post("/{demo_site_id}/storyblok-space", response_model=DemoSiteResponse)
async def provision_demo_site_storyblok_space(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Create the CMS space of a site generated without one (Storyblok's daily limit), its content kept."""
    site = _get_editable_demo_site(db, current_user.id, demo_site_id)
    try:
        site = await demo_site_service.provision_missing_storyblok_space(db, site)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except StoryblokProvisionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return _serialize_demo_site(db, site)


@router.post("/{demo_site_id}/restore-images", response_model=DemoSiteResponse)
async def restore_demo_site_images(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Move a demo's fragile content images (Storyblok/Google/Facebook) onto permanent R2, in place.

    Keeps the published site byte-identical — same texts, same photos, same order — so a dormant demo
    revived for a J+30 relance shows exactly what the prospect first saw, without depending on a
    Storyblok space that expiry has since deleted. Works on any status (an expired demo included).
    """
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    await demo_site_service.persist_content_images_to_r2(site)
    db.commit()
    db.refresh(site)
    return _serialize_demo_site(db, site)


@router.get("/{demo_site_id}/images", response_model=DemoSiteImagesResponse)
async def get_demo_site_images(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteImagesResponse:
    """Return the site's photo pool and current placement (hero/about/gallery by order)."""
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    images = demo_site_service.get_site_images(db, site)
    return DemoSiteImagesResponse(**images)


@router.put("/{demo_site_id}/images", response_model=DemoSiteResponse)
async def update_demo_site_images(
    demo_site_id: int,
    payload: DemoSiteImagesUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Save a user-curated photo placement and regenerate the site so it goes live."""
    site = _get_editable_demo_site(db, current_user.id, demo_site_id)
    site = await demo_site_service.set_site_images(db, site, payload.order)
    return _serialize_demo_site(db, site, include_brand_color=True)


@router.get("/{demo_site_id}/service-cards", response_model=DemoSiteServiceCardsResponse)
async def get_demo_site_service_cards(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteServiceCardsResponse:
    """The editable section cards (food « Nos spécialités »), their curation state and the labelled photo pool."""
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    return DemoSiteServiceCardsResponse(**demo_site_service.get_service_cards(db, site))


@router.post("/{demo_site_id}/service-cards/suggest", response_model=DemoSiteServiceCardsSuggestionResponse)
async def suggest_demo_site_service_cards(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteServiceCardsSuggestionResponse:
    """Compose the section cards with the AI (the pool photos are labelled first).

    Nothing is saved here: the dashboard previews the cards live, lets the operator edit them, and
    saves them with the other pending edits through the PATCH (``services``).
    """
    site = _get_editable_demo_site(db, current_user.id, demo_site_id)
    try:
        result = await demo_site_service.suggest_service_cards(db, site)
    except ServiceCardsUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DemoSiteServiceCardsSuggestionResponse(**result)


@router.get("/{demo_site_id}/video/state", response_model=DemoSiteVideoStateResponse)
async def get_demo_site_video_state(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteVideoStateResponse:
    """Where the prospection video stands, for the dashboard to follow a generation without reloading the site."""
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    is_video_ready = has_ready_video(site)
    clip_in_use_since = demo_video_service.clip_in_use_since(db, current_user.id)
    return DemoSiteVideoStateResponse(
        video_status=site.video_status,
        video_error=site.video_error,
        video_generated_at=site.video_generated_at,
        video_desktop_requested_at=site.video_desktop_requested_at,
        is_video_desktop_build_started=demo_video_service.is_desktop_build_started(site),
        is_video_made_with_older_clip=demo_video_service.is_made_with_older_clip(site, clip_in_use_since),
        is_video_waiting_for_storyblok_space=demo_video_service.is_waiting_for_storyblok_space(site),
        video_page_url=video_page_url(site.slug) if is_video_ready else None,
        video_thumbnail_url=public_thumbnail_url(site.slug, site.video_generated_at) if is_video_ready else None,
    )


@router.get("/video/desktop-requests", response_model=list[DemoSiteDesktopVideoRequestResponse])
async def list_desktop_video_requests(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[DemoSiteDesktopVideoRequestResponse]:
    """Site videos the caller's desktop app must build, their site ready to be filmed. Only the desktop app calls this."""
    desktop_app_presence.mark_seen(current_user.id)
    return [
        DemoSiteDesktopVideoRequestResponse(
            demo_site_id=site.id,
            slug=site.slug,
            business_name=site.business_name,
            requested_at=site.video_desktop_requested_at,
        )
        for site in demo_video_desktop_relay.waiting_subjects(db, current_user.id)
    ]


@router.post(
    "/{demo_site_id}/video/desktop-request", response_model=DemoSiteResponse, status_code=status.HTTP_202_ACCEPTED
)
async def request_demo_site_video_from_desktop(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Ask the owner's desktop app to build the prospection video; a site without its Storyblok space waits for it."""
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    try:
        site = demo_video_desktop_relay.request(db, site, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _serialize_demo_site(db, site)


@router.delete("/{demo_site_id}/video/desktop-request", response_model=DemoSiteResponse)
async def cancel_demo_site_video_desktop_request(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Withdraw the video request left for the desktop app; a video already published is untouched."""
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    _refuse_while_desktop_builds(site)
    return _serialize_demo_site(db, demo_video_desktop_relay.clear_request(db, site))


@router.post("/{demo_site_id}/video/desktop-claim", response_model=DemoSiteResponse)
async def claim_demo_site_video_desktop_request(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Tell that the caller's desktop app starts building the requested video, so nothing else takes it."""
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    try:
        demo_video_desktop_relay.claim(site)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _serialize_demo_site(db, site)


@router.post("/{demo_site_id}/video/desktop-failure", response_model=DemoSiteResponse)
async def report_demo_site_video_desktop_failure(
    demo_site_id: int,
    payload: ProspectionVideoDesktopFailureRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Close a requested video the desktop app could not build, with the reason the dashboard shows."""
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    try:
        site = demo_video_desktop_relay.record_failure(db, site, payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _serialize_demo_site(db, site)


@router.get("/{demo_site_id}/video-background-context")
async def get_demo_site_video_background_context(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Everything the desktop sidecar needs to render this site's video *background*
    (linear site scroll + Storyblok editor edit), sized to the presenter clip.

    The background is produced on the desktop because it needs the owner's Storyblok
    session; the sidecar montages the whole video and the app posts it via ``POST /{id}/video-final``.
    """
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    if not site.demo_url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ce site démo n'a pas d'URL publique.")
    if not site.storyblok_space_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce site n'a pas d'espace Storyblok (séquence éditeur impossible).",
        )
    presenter = presenter_video_service.get_for_user(db, current_user.id)
    if presenter is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucun clip de présentation enregistré.")

    total_seconds = presenter.duration_seconds - presenter.intro_seconds - presenter.outro_seconds
    story_id = await storyblok_service.get_home_story_id(site.storyblok_space_id)
    if story_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Home story Storyblok introuvable.")

    # User-chosen split when set (Paramètres → Vidéo : « Partie site ») so the speech
    # timing matches; otherwise the historical automatic split (editor budget carved
    # out of the middle). Clamped so both parts stay inside the middle segment.
    if presenter.site_seconds is not None:
        site_seconds = min(max(presenter.site_seconds, _MIN_SITE_SCROLL_SECONDS), total_seconds)
    else:
        site_seconds = max(_MIN_SITE_SCROLL_SECONDS, total_seconds - _EDITOR_SEQUENCE_BUDGET_SECONDS)
    accroche = demo_site_service.hero_line(site)
    # First name + presenter durations let the sidecar do the FULL montage locally
    # (greeting « Bonjour {prénom} », webcam PiP timing) — no VPS round-trip.
    first_name: str | None = None
    if site.prospect_id:
        resolved_first, _last, _gender = EmailVariables.resolved_contact(db, site.prospect_id)
        first_name = resolved_first or None
    return {
        "slug": site.slug,
        "demo_url": site.demo_url,
        "space_id": str(site.storyblok_space_id),
        "story_id": str(story_id),
        "accroche": accroche,
        "first_name": first_name,
        "presenter_duration": presenter.duration_seconds,
        "presenter_intro": presenter.intro_seconds,
        "presenter_outro": presenter.outro_seconds,
        "site_seconds": round(site_seconds, 2),
        "hold_seconds": 1.0,
        "total_seconds": round(total_seconds, 2),
        "out_width": 1280,
        "out_height": 720,
        "fps": 30,
    }


@router.post("/{demo_site_id}/video-final", response_model=DemoSiteResponse)
async def upload_demo_site_video_final(
    demo_site_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """
    Store a desktop-produced FINAL prospection video and mark the site ready.

    The desktop sidecar does the whole montage locally and returns a zip
    (``video.mp4`` + ``thumbnail.jpg``); here we just push both to R2 and flip the
    status — the VPS never touches ffmpeg for a desktop-generated video.
    """
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    try:
        await demo_video_service.store_desktop_video(db, site, file.file)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except VideoGenerationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    site = demo_video_desktop_relay.clear_request(db, site)
    return _serialize_demo_site(db, site)


@router.delete("/{demo_site_id}/video", response_model=DemoSiteResponse)
async def delete_demo_site_video(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Delete the generated prospection video and reset the video state."""
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    _refuse_while_desktop_builds(site)
    site = demo_video_service.clear_video(db, site)
    site = demo_video_desktop_relay.clear_request(db, site)
    return _serialize_demo_site(db, site)


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
    return _serialize_demo_site(db, site)


@router.post("/{demo_site_id}/refresh-cms-status", response_model=DemoSiteResponse)
async def refresh_demo_site_cms_status(
    demo_site_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> DemoSiteResponse:
    """Re-read whether the client has joined the Storyblok space (invited → pending → joined)."""
    site = demo_site_service.get_for_user(db, current_user.id, demo_site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo site not found")
    site = await demo_site_service.refresh_cms_collaborator_status(db, site)
    return _serialize_demo_site(db, site)


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
