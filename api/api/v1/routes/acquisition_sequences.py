"""
Acquisition sequence routes — the auto-chaining tunnel ("Séquences").

A sequence takes a batch of prospects and runs enrich → generate → (review) →
campaign automatically, with pause/resume/cancel and a human review gate.
All endpoints are scoped to the authenticated user.
"""
from __future__ import annotations

from typing import Any, List, Optional

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
    SequenceCreateRequest,
    SequenceDetailResponse,
    SequenceItemResponse,
    SequenceListResponse,
    SequenceResponse,
    SequenceStats,
)
from services.acquisition_service import (
    CreateSequenceInput,
    SequenceFollowUp,
    acquisition_service,
)
from services.auth_service import get_current_user
from services.organization_service import organization_service

router = APIRouter(prefix="/acquisition-sequences", tags=["acquisition-sequences"])


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------

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
        campaign_id=run.campaign_id,
        max_credits=run.max_credits,
        daily_email_cap=run.daily_email_cap,
        review_approved_at=run.review_approved_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
        stats=SequenceStats(**stats),
    )


def _detail_response(db: Session, run: AcquisitionRun) -> SequenceDetailResponse:
    """Build a full response including per-prospect items (no N+1 queries)."""
    base = _summary_response(db, run)

    prospect_ids: List[int] = [item.prospect_id for item in run.items]
    prospects: dict[int, ProspectDB] = {}
    demo_by_id: dict[int, DemoSite] = {}
    won_ids: set[int] = set()

    if prospect_ids:
        for prospect in (
            db.execute(select(ProspectDB).where(ProspectDB.id.in_(prospect_ids)))
            .scalars()
            .all()
        ):
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

    demo_ids: List[int] = [item.demo_site_id for item in run.items if item.demo_site_id]
    if demo_ids:
        for site in (
            db.execute(select(DemoSite).where(DemoSite.id.in_(demo_ids))).scalars().all()
        ):
            demo_by_id[site.id] = site

    items: List[SequenceItemResponse] = []
    for item in run.items:
        prospect: Optional[ProspectDB] = prospects.get(item.prospect_id)
        site: Optional[DemoSite] = (
            demo_by_id.get(item.demo_site_id) if item.demo_site_id else None
        )
        items.append(
            SequenceItemResponse(
                id=item.id,
                prospect_id=item.prospect_id,
                prospect_name=prospect.name if prospect else None,
                prospect_city=prospect.city if prospect else None,
                prospect_email=prospect.email if prospect else None,
                step=item.step,
                step_reason=item.step_reason,
                demo_site_id=item.demo_site_id,
                demo_slug=site.slug if site else None,
                demo_url=site.demo_url if site else None,
                demo_status=site.status if site else None,
                won=item.prospect_id in won_ids,
                updated_at=item.updated_at,
            )
        )

    return SequenceDetailResponse(**base.model_dump(), items=items)


def _get_or_404(db: Session, run_id: int, user_id: int) -> AcquisitionRun:
    """Fetch a sequence owned by the user or raise 404."""
    run = acquisition_service.get_for_user(db, user_id, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Séquence introuvable")
    return run


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=SequenceDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_sequence(
    payload: SequenceCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Create and start a sequence over the selected prospects."""
    org_id: Optional[int] = organization_service.user_org_id(db, current_user.id)
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
                SequenceFollowUp(template_id=fu.template_id, delay_days=fu.delay_days)
                for fu in payload.follow_ups
            ],
            max_credits=payload.max_credits,
            daily_email_cap=payload.daily_email_cap,
        ),
    )
    if not run.items:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Aucun prospect valide — vérifiez la sélection",
        )
    return _detail_response(db, run)


@router.get("", response_model=SequenceListResponse)
async def list_sequences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceListResponse:
    """List the user's sequences, newest first."""
    runs = acquisition_service.list_for_user(db, current_user.id)
    return SequenceListResponse(
        sequences=[_summary_response(db, run) for run in runs],
        total=len(runs),
    )


@router.get("/{run_id}", response_model=SequenceDetailResponse)
async def get_sequence(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Get a sequence with its per-prospect pipeline."""
    run = _get_or_404(db, run_id, current_user.id)
    return _detail_response(db, run)


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sequence(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a sequence and its items (prospects/sites are untouched)."""
    run = _get_or_404(db, run_id, current_user.id)
    acquisition_service.delete(db, run)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@router.post("/{run_id}/pause", response_model=SequenceDetailResponse)
async def pause_sequence(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Pause a running sequence."""
    run = _get_or_404(db, run_id, current_user.id)
    acquisition_service.pause(db, run)
    return _detail_response(db, run)


@router.post("/{run_id}/resume", response_model=SequenceDetailResponse)
async def resume_sequence(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Resume a paused sequence."""
    run = _get_or_404(db, run_id, current_user.id)
    acquisition_service.resume(db, run)
    return _detail_response(db, run)


@router.post("/{run_id}/cancel", response_model=SequenceDetailResponse)
async def cancel_sequence(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Cancel a sequence (non-destructive — stops the automation only)."""
    run = _get_or_404(db, run_id, current_user.id)
    acquisition_service.cancel(db, run)
    return _detail_response(db, run)


@router.post("/{run_id}/approve", response_model=SequenceDetailResponse)
async def approve_sequence(
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Approve the review gate — the machine may now campaign the generated sites."""
    run = _get_or_404(db, run_id, current_user.id)
    if run.status != "awaiting_review":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La séquence n'est pas en attente de validation",
        )
    acquisition_service.approve_review(db, run)
    return _detail_response(db, run)


@router.post("/{run_id}/items/{item_id}/reject", response_model=SequenceDetailResponse)
async def reject_sequence_item(
    run_id: int,
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SequenceDetailResponse:
    """Reject a single generated site during review (it won't be campaigned)."""
    run = _get_or_404(db, run_id, current_user.id)
    item = acquisition_service.reject_item(db, run, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect introuvable dans la séquence")
    db.refresh(run)
    return _detail_response(db, run)
