"""
Automatisation routes — the auto-chaining tunnel.

An automatisation takes a batch of prospects (a selection, or — in full-auto — a
métier + ville + objectif en jours) and runs enrich → generate → (review) →
campaign, with pause/resume/cancel, a human review gate, and per-prospect
corrections. All endpoints are scoped to the authenticated user.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_db
from enums.order_status import WON_STATUSES
from models.acquisition_run import AcquisitionRun
from models.demo_site import DemoSite
from models.order import Order
from models.prospect_db import ProspectDB
from models.user import User
from schemas.acquisition import (
    AssignTemplatesRequest,
    EmailPreviewRequest,
    EmailPreviewResponse,
    ItemIdsRequest,
    RegenerateRequest,
    SequenceCreateRequest,
    SequenceDetailResponse,
    SequenceItemResponse,
    SequenceListResponse,
    SequenceResponse,
    SequenceStats,
    UsedProspectsResponse,
)
from services.acquisition_service import (
    CreateSequenceInput,
    SequenceFollowUp,
    acquisition_service,
)
from services.auth_service import get_current_user
from services.organization_service import organization_service

router = APIRouter(prefix="/automations", tags=["automations"])


def _run_note(run: AcquisitionRun) -> str | None:
    """Surface the most relevant note from the run's stats (seed/campaign/pause)."""
    stats: dict = run.stats or {}
    for key in ("pause_reason", "seed_note", "campaign_note"):
        value = stats.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _summary_response(db: Session, run: AcquisitionRun) -> SequenceResponse:
    """Build a summary response (list view) with fresh stats."""
    stats = acquisition_service.build_stats(db, run)
    return SequenceResponse(
        id=run.id,
        name=run.name,
        status=run.status,
        mode=run.mode,
        auto_enrich=run.auto_enrich,
        auto_generate=run.auto_generate,
        template_id=run.template_id,
        auto_campaign=run.auto_campaign,
        email_template_id_a=run.email_template_id_a,
        email_template_id_b=run.email_template_id_b,
        send_delay_minutes=run.send_delay_minutes,
        search_metiers=run.search_metiers,
        search_villes=run.search_villes,
        target_days=run.target_days,
        only_without_website=run.only_without_website,
        campaign_id=run.campaign_id,
        review_approved_at=run.review_approved_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
        stats=SequenceStats(**stats),
        note=_run_note(run),
    )


def _detail_response(db: Session, run: AcquisitionRun) -> SequenceDetailResponse:
    """Build a full response including per-prospect items (no N+1 queries)."""
    base = _summary_response(db, run)

    prospect_ids: list[int] = [item.prospect_id for item in run.items]
    prospects: dict[int, ProspectDB] = {}
    demo_by_id: dict[int, DemoSite] = {}
    won_ids: set[int] = set()

    if prospect_ids:
        for prospect in db.execute(select(ProspectDB).where(ProspectDB.id.in_(prospect_ids))).scalars().all():
            prospects[prospect.id] = prospect
        won_ids = {
            row[0]
            for row in db.execute(
                select(Order.prospect_id).where(
                    Order.user_id == run.user_id,
                    Order.prospect_id.in_(prospect_ids),
                    Order.status.in_(WON_STATUSES),
                )
            ).all()
            if row[0] is not None
        }

    demo_ids: list[int] = [item.demo_site_id for item in run.items if item.demo_site_id]
    if demo_ids:
        for site in db.execute(select(DemoSite).where(DemoSite.id.in_(demo_ids))).scalars().all():
            demo_by_id[site.id] = site

    items: list[SequenceItemResponse] = []
    for item in run.items:
        prospect: ProspectDB | None = prospects.get(item.prospect_id)
        site: DemoSite | None = demo_by_id.get(item.demo_site_id) if item.demo_site_id else None
        items.append(
            SequenceItemResponse(
                id=item.id,
                prospect_id=item.prospect_id,
                prospect_name=prospect.name if prospect else None,
                prospect_city=prospect.city if prospect else None,
                prospect_email=prospect.email if prospect else None,
                step=item.step,
                step_reason=item.step_reason,
                template_id=item.template_id,
                demo_site_id=item.demo_site_id,
                demo_slug=site.slug if site else None,
                demo_url=site.demo_url if site else None,
                demo_status=site.status if site else None,
                storyblok_editor_url=getattr(site, "storyblok_editor_url", None) if site else None,
                quality_score=item.quality_score,
                quality_flags=item.quality_flags,
                won=item.prospect_id in won_ids,
                updated_at=item.updated_at,
            )
        )

    return SequenceDetailResponse(**base.model_dump(), items=items)


def _get_or_404(db: Session, run_id: int, user_id: int) -> AcquisitionRun:
    """Fetch an automatisation owned by the user or raise 404."""
    run = acquisition_service.get_for_user(db, user_id, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Automatisation introuvable")
    return run


@router.post("", response_model=SequenceDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_automation(
    payload: SequenceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Create and start an automatisation (selection or full-auto query)."""
    has_query: bool = bool(payload.search_metiers and payload.search_villes and payload.target_days)
    if not payload.prospect_ids and not has_query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Fournis une sélection de prospects, ou un métier + une ville + un objectif en jours.",
        )

    org_id: int | None = organization_service.user_org_id(db, current_user.id)
    run = acquisition_service.create_from_prospects(
        db,
        current_user.id,
        org_id,
        CreateSequenceInput(
            name=payload.name,
            prospect_ids=payload.prospect_ids,
            mode=payload.mode.value,
            auto_enrich=payload.auto_enrich,
            auto_generate=payload.auto_generate,
            template_id=payload.template_id,
            auto_campaign=payload.auto_campaign,
            email_template_id_a=payload.email_template_id_a,
            email_template_id_b=payload.email_template_id_b,
            send_delay_minutes=payload.send_delay_minutes,
            follow_ups=[
                SequenceFollowUp(template_id=fu.template_id, delay_days=fu.delay_days) for fu in payload.follow_ups
            ],
            search_metiers=payload.search_metiers,
            search_villes=payload.search_villes,
            target_days=payload.target_days,
            only_without_website=payload.only_without_website,
        ),
    )
    if not run.items and not has_query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Aucun prospect valide (déjà utilisés ou hors de ta visibilité).",
        )
    return _detail_response(db, run)


@router.get("", response_model=SequenceListResponse)
async def list_automations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceListResponse:
    """List the user's automatisations, newest first."""
    runs = acquisition_service.list_for_user(db, current_user.id)
    return SequenceListResponse(
        sequences=[_summary_response(db, run) for run in runs],
        total=len(runs),
    )


@router.get("/used-prospects", response_model=UsedProspectsResponse)
async def used_prospects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UsedProspectsResponse:
    """Prospect ids already claimed by an automatisation (for the picker)."""
    return UsedProspectsResponse(prospect_ids=sorted(acquisition_service.used_prospect_ids(db, current_user.id)))


@router.get("/{run_id}", response_model=SequenceDetailResponse)
async def get_automation(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Get an automatisation with its per-prospect pipeline."""
    run = _get_or_404(db, run_id, current_user.id)
    return _detail_response(db, run)


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_automation(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete an automatisation and its items (prospects/sites untouched)."""
    run = _get_or_404(db, run_id, current_user.id)
    acquisition_service.delete(db, run)


@router.post("/{run_id}/pause", response_model=SequenceDetailResponse)
async def pause_automation(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Pause a running automatisation."""
    run = _get_or_404(db, run_id, current_user.id)
    acquisition_service.pause(db, run)
    return _detail_response(db, run)


@router.post("/{run_id}/resume", response_model=SequenceDetailResponse)
async def resume_automation(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Resume a paused automatisation."""
    run = _get_or_404(db, run_id, current_user.id)
    acquisition_service.resume(db, run)
    return _detail_response(db, run)


@router.post("/{run_id}/cancel", response_model=SequenceDetailResponse)
async def cancel_automation(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Cancel an automatisation (non-destructive — stops the automation only)."""
    run = _get_or_404(db, run_id, current_user.id)
    acquisition_service.cancel(db, run)
    return _detail_response(db, run)


@router.post("/{run_id}/approve", response_model=SequenceDetailResponse)
async def approve_automation(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Approve the review gate — the machine may now campaign the generated sites."""
    run = _get_or_404(db, run_id, current_user.id)
    if run.status != "awaiting_review":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="L'automatisation n'est pas en attente de validation",
        )
    acquisition_service.approve_review(db, run)
    return _detail_response(db, run)


@router.post("/{run_id}/assign-templates", response_model=SequenceDetailResponse)
async def assign_templates(
    run_id: int,
    data: AssignTemplatesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Assign a demo template to some (or all pre-generation) items."""
    run = _get_or_404(db, run_id, current_user.id)
    acquisition_service.assign_templates(db, run, data.template_id, data.item_ids)
    db.refresh(run)
    return _detail_response(db, run)


@router.post("/{run_id}/regenerate", response_model=SequenceDetailResponse)
async def regenerate_items(
    run_id: int,
    data: RegenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Regenerate the given items (optionally with a new template)."""
    run = _get_or_404(db, run_id, current_user.id)
    acquisition_service.regenerate_items(db, run, data.item_ids, data.template_id)
    db.refresh(run)
    return _detail_response(db, run)


@router.post("/{run_id}/reenrich", response_model=SequenceDetailResponse)
async def reenrich_items(
    run_id: int,
    data: ItemIdsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Re-enrich then re-generate the given items."""
    run = _get_or_404(db, run_id, current_user.id)
    acquisition_service.reenrich_items(db, run, data.item_ids)
    db.refresh(run)
    return _detail_response(db, run)


@router.post("/{run_id}/exclude", response_model=SequenceDetailResponse)
async def exclude_items(
    run_id: int,
    data: ItemIdsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Exclude items from the automatisation (frees their prospects)."""
    run = _get_or_404(db, run_id, current_user.id)
    acquisition_service.exclude_items(db, run, data.item_ids)
    db.refresh(run)
    return _detail_response(db, run)


@router.post("/{run_id}/preview-email", response_model=EmailPreviewResponse)
async def preview_email(
    run_id: int,
    data: EmailPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EmailPreviewResponse:
    """Render the real email for one item with a given template."""
    run = _get_or_404(db, run_id, current_user.id)
    preview = acquisition_service.preview_email(db, run, data.item_id, data.template_id)
    if preview is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect ou modèle introuvable")
    return EmailPreviewResponse(subject=preview["subject"], body_html=preview["body_html"])
