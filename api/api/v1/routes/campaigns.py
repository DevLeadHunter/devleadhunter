"""
Campaign routes for API v1.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from core.database import get_db
from models.campaign import CampaignStatus
from models.campaign_follow_up import CampaignFollowUp
from models.email_queue import EmailQueue
from models.user import User
from schemas.campaign import (
    CampaignCreate,
    CampaignDetailResponse,
    CampaignFollowUpCreate,
    CampaignFollowUpResponse,
    CampaignFollowUpUpdate,
    CampaignListResponse,
    CampaignProspectAdd,
    CampaignProspectResponse,
    CampaignResponse,
    CampaignSettingsUpdate,
    CampaignStats,
    CampaignUpdate,
)
from services.auth_service import get_current_user
from services.campaign_queue_service import CampaignQueueService
from services.campaign_service import campaign_service

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class LaunchCampaignRequest(BaseModel):
    """Payload for POST /campaigns/{id}/launch."""
    template_id: Optional[int] = None
    ab_template_id_b: Optional[int] = None
    follow_up_template_id: Optional[int] = None
    follow_up_delay_days: int = 5
    send_delay_minutes: int = 20


class SendNowRequest(BaseModel):
    """Payload for POST /campaigns/{id}/send-now."""
    prospect_id: int
    template_id: int


def _has_resend_config(db: Session, user_id: int) -> bool:
    """Return True when the user has a Resend API key configured."""
    from models.resend_config import ResendConfig
    config = db.execute(
        select(ResendConfig).where(ResendConfig.user_id == user_id)
    ).scalar_one_or_none()
    return config is not None and bool(config.api_key)


def _detail_response(campaign) -> CampaignDetailResponse:
    """Build a CampaignDetailResponse from a Campaign ORM object."""
    return CampaignDetailResponse(
        id=campaign.id,
        user_id=campaign.user_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        template_id=campaign.template_id,
        ab_template_id_b=campaign.ab_template_id_b,
        send_delay_minutes=campaign.send_delay_minutes,
        follow_up_delay_days=campaign.follow_up_delay_days,
        started_at=campaign.started_at,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        prospects_count=len(campaign.prospects),
        prospects=[
            CampaignProspectResponse(
                id=p.id,
                name=p.name,
                email=p.email,
                phone=p.phone,
                city=p.city,
                category=p.category,
                source=p.source,
                confidence=p.confidence,
            )
            for p in campaign.prospects
        ],
        follow_ups=[
            CampaignFollowUpResponse(
                id=fu.id,
                campaign_id=fu.campaign_id,
                template_id=fu.template_id,
                template_name=fu.template.name if fu.template else None,
                template_subject=fu.template.subject if fu.template else None,
                delay_days=fu.delay_days,
                position=fu.position,
                created_at=fu.created_at,
            )
            for fu in sorted(campaign.follow_ups, key=lambda x: x.position)
        ],
    )


def _get_or_404(db: Session, campaign_id: int, user_id: int):
    """Fetch campaign or raise 404."""
    campaign = campaign_service.get_campaign(db, campaign_id, user_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


@router.post("", response_model=CampaignDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_data: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new email campaign."""
    campaign = campaign_service.create_campaign(db, current_user.id, campaign_data)
    return _detail_response(campaign)


@router.get("", response_model=CampaignListResponse)
async def list_campaigns(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all campaigns for the current user."""
    campaigns, total = campaign_service.list_campaigns(db, current_user.id, skip, limit, status)
    return CampaignListResponse(
        campaigns=[
            CampaignResponse(
                id=c.id,
                user_id=c.user_id,
                name=c.name,
                description=c.description,
                status=c.status,
                template_id=c.template_id,
                ab_template_id_b=c.ab_template_id_b,
                send_delay_minutes=c.send_delay_minutes,
                follow_up_delay_days=c.follow_up_delay_days,
                started_at=c.started_at,
                created_at=c.created_at,
                updated_at=c.updated_at,
                prospects_count=len(c.prospects),
            )
            for c in campaigns
        ],
        total=total,
    )


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
async def get_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a campaign with its prospects and follow-up sequence."""
    campaign = _get_or_404(db, campaign_id, current_user.id)
    return _detail_response(campaign)


@router.patch("/{campaign_id}", response_model=CampaignDetailResponse)
async def update_campaign(
    campaign_id: int,
    campaign_data: CampaignUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a campaign's name, description, or status."""
    campaign = campaign_service.update_campaign(db, campaign_id, current_user.id, campaign_data)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return _detail_response(campaign)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently delete a campaign and its queue items."""
    deleted = campaign_service.delete_campaign(db, campaign_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")


@router.patch("/{campaign_id}/settings", response_model=CampaignDetailResponse)
async def update_campaign_settings(
    campaign_id: int,
    settings: CampaignSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CampaignDetailResponse:
    """
    Update campaign send configuration.

    All fields are optional — only supplied values are changed.
    When ``follow_ups`` is provided it fully **replaces** the existing sequence.
    This endpoint is safe to call on active campaigns: changes apply to all
    queue items that have not been dispatched yet.
    """
    campaign = _get_or_404(db, campaign_id, current_user.id)

    if settings.template_id is not None:
        campaign.template_id = settings.template_id
    if settings.disable_ab:
        campaign.ab_template_id_b = None
    elif settings.ab_template_id_b is not None:
        campaign.ab_template_id_b = settings.ab_template_id_b
    if settings.send_delay_minutes is not None:
        campaign.send_delay_minutes = settings.send_delay_minutes
    if settings.behavior_personalized_followups is not None:
        campaign.behavior_personalized_followups = settings.behavior_personalized_followups

    if settings.follow_ups is not None:
        # Replace the entire follow-up sequence.
        db.execute(
            delete(CampaignFollowUp).where(CampaignFollowUp.campaign_id == campaign_id)
        )
        for i, fu in enumerate(settings.follow_ups, start=1):
            db.add(CampaignFollowUp(
                campaign_id=campaign_id,
                template_id=fu.template_id,
                delay_days=fu.delay_days,
                position=i,
            ))

    db.commit()
    db.refresh(campaign)
    return _detail_response(campaign)


@router.post("/{campaign_id}/prospects", response_model=CampaignDetailResponse)
async def add_prospects_to_campaign(
    campaign_id: int,
    data: CampaignProspectAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add prospects to a campaign."""
    campaign = campaign_service.add_prospects_to_campaign(
        db, campaign_id, current_user.id, data.prospect_ids
    )
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return _detail_response(campaign)


@router.delete("/{campaign_id}/prospects/{prospect_id}", response_model=CampaignDetailResponse)
async def remove_prospect_from_campaign(
    campaign_id: int,
    prospect_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a prospect from a campaign."""
    campaign = campaign_service.remove_prospect_from_campaign(
        db, campaign_id, current_user.id, prospect_id
    )
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return _detail_response(campaign)


@router.post("/{campaign_id}/follow-ups", response_model=CampaignFollowUpResponse)
async def add_follow_up(
    campaign_id: int,
    data: CampaignFollowUpCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CampaignFollowUpResponse:
    """Append a follow-up step to the campaign sequence."""
    _get_or_404(db, campaign_id, current_user.id)

    # Auto-set position to last + 1 if not supplied or already taken.
    max_pos: int = db.execute(
        select(func.max(CampaignFollowUp.position)).where(
            CampaignFollowUp.campaign_id == campaign_id
        )
    ).scalar() or 0

    fu = CampaignFollowUp(
        campaign_id=campaign_id,
        template_id=data.template_id,
        delay_days=data.delay_days,
        position=max_pos + 1,
    )
    db.add(fu)
    db.commit()
    db.refresh(fu)

    return CampaignFollowUpResponse(
        id=fu.id,
        campaign_id=fu.campaign_id,
        template_id=fu.template_id,
        template_name=fu.template.name if fu.template else None,
        template_subject=fu.template.subject if fu.template else None,
        delay_days=fu.delay_days,
        position=fu.position,
        created_at=fu.created_at,
    )


@router.patch("/{campaign_id}/follow-ups/{followup_id}", response_model=CampaignFollowUpResponse)
async def update_follow_up(
    campaign_id: int,
    followup_id: int,
    data: CampaignFollowUpUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CampaignFollowUpResponse:
    """Update a follow-up step (template, delay, or position)."""
    _get_or_404(db, campaign_id, current_user.id)
    fu: CampaignFollowUp | None = db.get(CampaignFollowUp, followup_id)
    if not fu or fu.campaign_id != campaign_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")

    if data.template_id is not None:
        fu.template_id = data.template_id
    if data.delay_days is not None:
        fu.delay_days = data.delay_days
    if data.position is not None:
        fu.position = data.position

    db.commit()
    db.refresh(fu)

    return CampaignFollowUpResponse(
        id=fu.id,
        campaign_id=fu.campaign_id,
        template_id=fu.template_id,
        template_name=fu.template.name if fu.template else None,
        template_subject=fu.template.subject if fu.template else None,
        delay_days=fu.delay_days,
        position=fu.position,
        created_at=fu.created_at,
    )


@router.delete("/{campaign_id}/follow-ups/{followup_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_follow_up(
    campaign_id: int,
    followup_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a follow-up step from the campaign sequence."""
    _get_or_404(db, campaign_id, current_user.id)
    fu: CampaignFollowUp | None = db.get(CampaignFollowUp, followup_id)
    if not fu or fu.campaign_id != campaign_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Follow-up not found")
    db.delete(fu)
    db.commit()


@router.post("/{campaign_id}/launch")
async def launch_campaign(
    campaign_id: int,
    launch_data: LaunchCampaignRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Activate a campaign and populate the send queue.

    Uses the campaign's stored ``template_id`` when not overridden in the
    request body.  Emails are sent via the user's Resend configuration — no
    account selection.  The queue dispatches one email every
    ``send_delay_minutes`` minutes.  A/B testing is enabled automatically when
    the campaign (or the request) provides ``ab_template_id_b``.
    """
    campaign = _get_or_404(db, campaign_id, current_user.id)

    if not _has_resend_config(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Configuration Resend manquante — Paramètres → Configuration Resend",
        )

    # Resolve template: prefer request override, fall back to stored.
    template_id = launch_data.template_id or campaign.template_id
    ab_template_id_b = launch_data.ab_template_id_b or campaign.ab_template_id_b

    if not template_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="template_id requis — sélectionnez un template J1",
        )

    # Persist any runtime overrides on the campaign.
    campaign.template_id = template_id
    if ab_template_id_b:
        campaign.ab_template_id_b = ab_template_id_b
    campaign.send_delay_minutes = launch_data.send_delay_minutes
    if launch_data.follow_up_template_id:
        campaign.follow_up_template_id = launch_data.follow_up_template_id
        campaign.follow_up_delay_days = launch_data.follow_up_delay_days
    campaign.status = CampaignStatus.ACTIVE.value
    campaign.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    queue_service = CampaignQueueService(db)
    result = queue_service.enqueue_campaign(
        campaign,
        template_id=template_id,
        ab_template_id_b=ab_template_id_b,
    )

    ab_info = " (A/B 50/50)" if ab_template_id_b else ""
    message = f"{result.enqueued} email(s) mis en file{ab_info} — 1 toutes les {campaign.send_delay_minutes} min"
    if result.skipped_no_demo:
        message += f" · {len(result.skipped_no_demo)} prospect(s) ignoré(s) faute de site de démo"
    if result.skipped_no_video:
        message += f" · {len(result.skipped_no_video)} prospect(s) ignoré(s) faute de vidéo de prospection"
    return {
        "success": True,
        "enqueued": result.enqueued,
        "skipped_no_demo": result.skipped_no_demo,
        "skipped_no_video": result.skipped_no_video,
        "message": message,
    }


@router.post("/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Pause a running campaign — pending emails are cancelled."""
    campaign = _get_or_404(db, campaign_id, current_user.id)
    campaign.status = CampaignStatus.PAUSED.value
    db.commit()

    queue_service = CampaignQueueService(db)
    cancelled = queue_service.cancel_campaign_queue(campaign_id)
    return {"success": True, "cancelled": cancelled}


@router.post("/{campaign_id}/resume")
async def resume_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Resume a paused campaign.

    Re-enqueues prospects that haven't been sent a J1 yet.
    Prospects who already have a sent/skipped item are not re-added.
    """
    campaign = _get_or_404(db, campaign_id, current_user.id)

    if campaign.status not in (CampaignStatus.PAUSED.value, CampaignStatus.DRAFT.value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Seules les campagnes en pause ou brouillon peuvent être relancées",
        )
    if not campaign.template_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Configurez un template J1 avant de reprendre",
        )
    if not _has_resend_config(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Configuration Resend manquante — Paramètres → Configuration Resend",
        )

    campaign.status = CampaignStatus.ACTIVE.value
    db.commit()

    queue_service = CampaignQueueService(db)
    result = queue_service.enqueue_campaign(
        campaign,
        template_id=campaign.template_id,
        ab_template_id_b=campaign.ab_template_id_b,
    )
    return {
        "success": True,
        "enqueued": result.enqueued,
        "skipped_no_demo": result.skipped_no_demo,
        "skipped_no_video": result.skipped_no_video,
    }


@router.post("/{campaign_id}/send-now")
async def send_now(
    campaign_id: int,
    data: SendNowRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Immediately dispatch a follow-up email to a specific prospect,
    bypassing the scheduled queue.
    """
    campaign = _get_or_404(db, campaign_id, current_user.id)
    if not _has_resend_config(db, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Configuration Resend manquante — Paramètres → Configuration Resend",
        )

    queue_service = CampaignQueueService(db)
    result = await queue_service.send_followup_now(
        campaign=campaign,
        prospect_id=data.prospect_id,
        template_id=data.template_id,
    )
    return result


@router.get("/{campaign_id}/queue")
async def get_campaign_queue(
    campaign_id: int,
    queue_status: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return queue items for a campaign ordered by scheduled_at."""
    campaign = _get_or_404(db, campaign_id, current_user.id)

    queue_service = CampaignQueueService(db)
    items = queue_service.get_queue_items(campaign_id, status=queue_status, limit=limit, offset=offset)
    pending = queue_service.get_pending_count(campaign_id)

    return {
        "pending_count": pending,
        "items": [
            {
                "id":               i.id,
                "queue_type":       i.queue_type,
                "status":           i.status,
                "scheduled_at":     i.scheduled_at.isoformat(),
                "prospect_id":      i.prospect_id,
                "prospect_name":    i.prospect.name if i.prospect else None,
                "prospect_email":   i.prospect.email if i.prospect else None,
                "ab_variant":       i.ab_variant,
                "follow_up_index":  i.follow_up_index,
                "email_log_id":     i.email_log_id,
            }
            for i in items
        ],
    }


@router.get("/{campaign_id}/stats", response_model=CampaignStats)
async def get_campaign_stats(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get delivery, open, click rates and optional A/B breakdown."""
    stats = campaign_service.get_campaign_stats(db, campaign_id, current_user.id)
    if not stats:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return stats
