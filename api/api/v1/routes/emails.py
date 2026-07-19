"""
Email sending routes for sending individual and campaign emails.
"""
from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from core.database import get_db
from enums.email_status import EmailStatus
from models.email_log import EmailLog
from models.resend_config import ResendConfig
from models.user import User
from schemas.email_sending import (
    EmailLogListResponse,
    EmailLogResponse,
    EmailStatsResponse,
    SendEmailResponse,
)
from services.auth_service import get_current_user
from services.email_sending_service import EmailSendingService
from services.encryption_service import encryption_service

router = APIRouter(prefix="/emails", tags=["emails"])

# Resend GET /emails/{id} last_event values → our EmailStatus values.
_RESEND_EVENT_TO_STATUS: dict[str, str] = {
    "scheduled":        EmailStatus.SCHEDULED.value,
    "sent":             EmailStatus.SENT.value,
    "delivered":        EmailStatus.DELIVERED.value,
    "delivery_delayed": EmailStatus.DELIVERY_DELAYED.value,
    "opened":           EmailStatus.OPENED.value,
    "clicked":          EmailStatus.CLICKED.value,
    "bounced":          EmailStatus.BOUNCED.value,
    "complained":       EmailStatus.COMPLAINED.value,
    "failed":           EmailStatus.FAILED.value,
    "suppressed":       EmailStatus.SUPPRESSED.value,
}

# Statuses still eligible for further events.
# Scheduled/sent/delivered/opened/clicked can all receive later events.
_UNRESOLVED_STATUSES = (
    EmailStatus.PENDING.value,
    EmailStatus.SENDING.value,
    EmailStatus.SCHEDULED.value,
    EmailStatus.SENT.value,
    EmailStatus.DELIVERY_DELAYED.value,
    EmailStatus.DELIVERED.value,
    EmailStatus.OPENED.value,
    EmailStatus.CLICKED.value,
)

# When syncing from Resend's last_event, cascade-fill all timestamp columns
# implied by that state (e.g. if "opened", delivery must have happened too).
_CASCADE_TIMESTAMPS: dict[str, list[str]] = {
    EmailStatus.DELIVERED.value:        ["delivered_at"],
    EmailStatus.DELIVERY_DELAYED.value: [],
    EmailStatus.OPENED.value:           ["delivered_at", "opened_at"],
    EmailStatus.CLICKED.value:          ["delivered_at", "opened_at", "clicked_at"],
    EmailStatus.BOUNCED.value:          ["bounced_at"],
    EmailStatus.COMPLAINED.value:       ["complained_at"],
    EmailStatus.FAILED.value:           ["failed_at"],
    EmailStatus.SUPPRESSED.value:       ["suppressed_at"],
}


# ---------------------------------------------------------------------------
# Resend status sync (fallback for local dev without public webhook)
# ---------------------------------------------------------------------------

@router.post("/sync-resend-status")
async def sync_resend_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Poll the Resend API for the latest status of all unresolved emails.

    Designed as a fallback for local development where the webhook endpoint
    is not publicly reachable.  Fetches ``GET /emails/{id}`` for every
    EmailLog row whose status is still unresolved (sent / pending /
    delivery_delayed) and has a ``provider_message_id`` set.

    Returns a summary of how many rows were updated.
    """
    import aiohttp
    from datetime import datetime, timezone

    config: ResendConfig | None = db.execute(
        select(ResendConfig).where(ResendConfig.user_id == current_user.id)
    ).scalar_one_or_none()

    if config is None or not config.api_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resend non configuré",
        )

    api_key: str = encryption_service.decrypt(config.api_key)

    # Fetch all unresolved logs that have a Resend message ID
    logs: list[EmailLog] = db.execute(
        select(EmailLog).where(
            EmailLog.user_id == current_user.id,
            EmailLog.provider == "resend",
            EmailLog.provider_message_id.isnot(None),
            EmailLog.status.in_(_UNRESOLVED_STATUSES),
        )
    ).scalars().all()

    if not logs:
        return {"updated": 0, "checked": 0}

    updated: int = 0
    errors: list[str] = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    async with aiohttp.ClientSession() as session:
        for log in logs:
            try:
                async with session.get(
                    f"https://api.resend.com/emails/{log.provider_message_id}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status == 401:
                        body_text = await resp.text()
                        if "restricted_api_key" in body_text:
                            errors.append(
                                "restricted_api_key: la clé API Resend n'a pas la permission de lire "
                                "les emails (emails:read). Créez une clé Full Access dans le dashboard "
                                "Resend et mettez-la à jour dans Paramètres."
                            )
                        else:
                            errors.append(f"401 Unauthorized — vérifiez votre clé API Resend")
                        break  # même clé pour tous les emails, inutile de continuer
                    if resp.status != 200:
                        errors.append(
                            f"log={log.id} resend_id={log.provider_message_id} http={resp.status}"
                        )
                        continue
                    data: dict[str, Any] = await resp.json(content_type=None)

                last_event: str = data.get("last_event", "")
                new_status: str | None = _RESEND_EVENT_TO_STATUS.get(last_event)

                if new_status and new_status != log.status:
                    log.status = new_status
                    # Fill in all timestamps implied by this event (cascade).
                    for ts_col in _CASCADE_TIMESTAMPS.get(new_status, []):
                        if not getattr(log, ts_col):
                            setattr(log, ts_col, now)
                    updated += 1

            except Exception as exc:  # noqa: BLE001
                errors.append(f"log={log.id} error={exc!r}")
                continue

    if updated:
        db.commit()

    return {"updated": updated, "checked": len(logs), "errors": errors}


# ---------------------------------------------------------------------------
# Quick-send schema (no email_account_id — uses resend_config directly)
# ---------------------------------------------------------------------------

class QuickSendRequest(BaseModel):
    """Payload for the /emails/quick-send endpoint."""
    recipient_email: str
    recipient_name: Optional[str] = None
    subject: str
    body_html: str
    prospect_id: Optional[str] = None
    campaign_id: Optional[str] = None


@router.post("/quick-send", response_model=SendEmailResponse)
async def quick_send_email(
    payload: QuickSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Send a one-off email using the current user's active sending identity.

    Resolves the sender + provider automatically from ``users.sending_provider``
    (Resend or Gmail) — no ``email_account_id`` required.
    """
    from services.unsubscribe_service import unsubscribe_service
    from services.sending_identity import resolve_sending_identity, SendingNotConfiguredError

    # Fail fast with friendly codes (the shared send path would surface a 500 here).
    try:
        resolve_sending_identity(db, current_user.id)
    except SendingNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    if unsubscribe_service.is_unsubscribed(db, payload.recipient_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{payload.recipient_email} s'est désabonné",
        )

    # Route through the shared send path so DEV_EMAIL_REDIRECT (dev safety), the RGPD
    # unsubscribe footer and the EmailLog are all applied. NEVER call the provider
    # directly here — a direct send would bypass the dev-email redirect and could reach
    # a real prospect in development.
    sending = EmailSendingService(db)
    return await sending.send_via_user_identity(
        user_id=current_user.id,
        recipient_email=payload.recipient_email,
        subject=payload.subject,
        body_html=payload.body_html,
        recipient_name=payload.recipient_name,
        prospect_id=payload.prospect_id,
        campaign_id=payload.campaign_id,
    )




@router.get("/logs", response_model=EmailLogListResponse)
async def get_email_logs(
    campaign_id: str = Query(None, description="Filter by campaign ID"),
    prospect_id: str = Query(None, description="Filter by prospect ID"),
    status_filter: EmailStatus = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=1000, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get email logs for the current user.
    """
    # Build query
    stmt = select(EmailLog).where(
        EmailLog.user_id == current_user.id
    )
    
    if campaign_id:
        stmt = stmt.where(EmailLog.campaign_id == campaign_id)
    if prospect_id:
        stmt = stmt.where(EmailLog.prospect_id == prospect_id)
    if status_filter:
        stmt = stmt.where(EmailLog.status == status_filter.value)
    
    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar()
    
    # Get logs with pagination
    stmt = stmt.order_by(EmailLog.created_at.desc()).limit(limit).offset(offset)
    result = db.execute(stmt)
    logs = result.scalars().all()
    
    return EmailLogListResponse(
        total=total,
        logs=logs
    )


@router.get("/logs/{log_id}", response_model=EmailLogResponse)
async def get_email_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific email log by ID.
    """
    stmt = select(EmailLog).where(
        EmailLog.id == log_id,
        EmailLog.user_id == current_user.id
    )
    
    result = db.execute(stmt)
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email log not found"
        )
    
    return log


@router.get("/stats", response_model=EmailStatsResponse)
async def get_email_stats(
    campaign_id: str = Query(None, description="Filter by campaign ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get email statistics for the current user.
    """
    # Build base query
    base_stmt = select(EmailLog).where(
        EmailLog.user_id == current_user.id
    )
    
    if campaign_id:
        base_stmt = base_stmt.where(EmailLog.campaign_id == campaign_id)
    
    # Count by status
    total_sent = db.execute(
        select(func.count()).select_from(
            base_stmt.where(EmailLog.status == EmailStatus.SENT.value).subquery()
        )
    ).scalar()
    
    total_delivered = db.execute(
        select(func.count()).select_from(
            base_stmt.where(EmailLog.status == EmailStatus.DELIVERED.value).subquery()
        )
    ).scalar()
    
    total_opened = db.execute(
        select(func.count()).select_from(
            base_stmt.where(EmailLog.status == EmailStatus.OPENED.value).subquery()
        )
    ).scalar()
    
    total_clicked = db.execute(
        select(func.count()).select_from(
            base_stmt.where(EmailLog.status == EmailStatus.CLICKED.value).subquery()
        )
    ).scalar()
    
    total_bounced = db.execute(
        select(func.count()).select_from(
            base_stmt.where(EmailLog.status == EmailStatus.BOUNCED.value).subquery()
        )
    ).scalar()
    
    total_failed = db.execute(
        select(func.count()).select_from(
            base_stmt.where(EmailLog.status == EmailStatus.FAILED.value).subquery()
        )
    ).scalar()
    
    # Calculate rates
    delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0.0
    open_rate = (total_opened / total_delivered * 100) if total_delivered > 0 else 0.0
    click_rate = (total_clicked / total_opened * 100) if total_opened > 0 else 0.0
    
    return EmailStatsResponse(
        total_sent=total_sent,
        total_delivered=total_delivered,
        total_opened=total_opened,
        total_clicked=total_clicked,
        total_bounced=total_bounced,
        total_failed=total_failed,
        delivery_rate=round(delivery_rate, 2),
        open_rate=round(open_rate, 2),
        click_rate=round(click_rate, 2)
    )

