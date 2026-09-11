"""
Email sending routes for sending individual and campaign emails.
"""

from __future__ import annotations

import logging
from datetime import UTC
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.database import get_db
from enums.email_status import EmailStatus
from models.email_log import EmailLog
from models.user import User
from schemas.email_sending import (
    ConversationResponse,
    EmailLogListResponse,
    EmailLogResponse,
    EmailStatsResponse,
    PendingRepliesResponse,
    ReplySendRequest,
    SendEmailResponse,
)
from services.auth_service import get_current_user
from services.campaign_queue_service import CampaignQueueService
from services.conversation_service import conversation_service
from services.email_log_stats import aggregate_email_log_counts, compute_engagement_rates
from services.email_sending_service import EmailSendingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/emails", tags=["emails"])

# Resend GET /emails/{id} last_event values → our EmailStatus values.
_RESEND_EVENT_TO_STATUS: dict[str, str] = {
    "scheduled": EmailStatus.SCHEDULED.value,
    "sent": EmailStatus.SENT.value,
    "delivered": EmailStatus.DELIVERED.value,
    "delivery_delayed": EmailStatus.DELIVERY_DELAYED.value,
    "opened": EmailStatus.OPENED.value,
    "clicked": EmailStatus.CLICKED.value,
    "bounced": EmailStatus.BOUNCED.value,
    "complained": EmailStatus.COMPLAINED.value,
    "failed": EmailStatus.FAILED.value,
    "suppressed": EmailStatus.SUPPRESSED.value,
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
    EmailStatus.DELIVERED.value: ["delivered_at"],
    EmailStatus.DELIVERY_DELAYED.value: [],
    EmailStatus.OPENED.value: ["delivered_at", "opened_at"],
    EmailStatus.CLICKED.value: ["delivered_at", "opened_at", "clicked_at"],
    EmailStatus.BOUNCED.value: ["bounced_at"],
    EmailStatus.COMPLAINED.value: ["complained_at"],
    EmailStatus.FAILED.value: ["failed_at"],
    EmailStatus.SUPPRESSED.value: ["suppressed_at"],
}


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
    from datetime import datetime

    import aiohttp

    from services.sending_identity import get_resend_api_key

    api_key: str | None = get_resend_api_key(db, current_user.id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resend non configuré",
        )

    # Fetch all unresolved logs that have a Resend message ID
    logs: list[EmailLog] = (
        db.execute(
            select(EmailLog).where(
                EmailLog.user_id == current_user.id,
                EmailLog.provider == "resend",
                EmailLog.provider_message_id.isnot(None),
                EmailLog.status.in_(_UNRESOLVED_STATUSES),
            )
        )
        .scalars()
        .all()
    )

    if not logs:
        return {"updated": 0, "checked": 0}

    updated: int = 0
    errors: list[str] = []
    now = datetime.now(UTC).replace(tzinfo=None)

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
                            errors.append("401 Unauthorized — vérifiez votre clé API Resend")
                        break  # même clé pour tous les emails, inutile de continuer
                    if resp.status != 200:
                        errors.append(f"log={log.id} resend_id={log.provider_message_id} http={resp.status}")
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

            except Exception as exc:
                errors.append(f"log={log.id} error={exc!r}")
                continue

    if updated:
        db.commit()

    return {"updated": updated, "checked": len(logs), "errors": errors}


class QuickSendRequest(BaseModel):
    """Payload for the /emails/quick-send endpoint."""

    recipient_email: str
    recipient_name: str | None = None
    subject: str
    body_html: str
    prospect_id: str | None = None
    campaign_id: str | None = None
    signature_id: int | None = None


class ResendEmailLogRequest(BaseModel):
    """Payload for POST /emails/logs/{log_id}/resend — optional address to send to instead."""

    email: str | None = None


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
    from services.sending_identity import SendingNotConfiguredError, resolve_sending_identity
    from services.unsubscribe_service import unsubscribe_service

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
    # Append the chosen signature (if any) before the shared send path.
    from services.email_signatures import render_signature_html

    body_html = payload.body_html + render_signature_html(db, payload.signature_id, user_id=current_user.id)

    sending = EmailSendingService(db)
    result = await sending.send_via_user_identity(
        user_id=current_user.id,
        recipient_email=payload.recipient_email,
        subject=payload.subject,
        body_html=body_html,
        recipient_name=payload.recipient_name,
        prospect_id=payload.prospect_id,
        campaign_id=payload.campaign_id,
    )
    # A manual contact supersedes the campaigns: hold back every pending send of this prospect.
    if result.get("success") and payload.prospect_id:
        try:
            CampaignQueueService(db).skip_pending_for_prospect(
                int(payload.prospect_id), label="Contacté manuellement (email)"
            )
        except Exception:
            logger.warning("Could not hold back campaign sends for prospect %s", payload.prospect_id, exc_info=True)
    return result


@router.get("/logs", response_model=EmailLogListResponse)
async def get_email_logs(
    campaign_id: str = Query(None, description="Filter by campaign ID"),
    prospect_id: str = Query(None, description="Filter by prospect ID"),
    status_filter: EmailStatus = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(50, ge=1, le=1000, description="Number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get email logs for the current user.
    """
    # Build query
    stmt = select(EmailLog).where(EmailLog.user_id == current_user.id)

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

    return EmailLogListResponse(total=total, logs=logs)


@router.get("/logs/{log_id}", response_model=EmailLogResponse)
async def get_email_log(log_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get a specific email log by ID.
    """
    stmt = select(EmailLog).where(EmailLog.id == log_id, EmailLog.user_id == current_user.id)

    result = db.execute(stmt)
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email log not found")

    return log


@router.post("/logs/{log_id}/resend", response_model=SendEmailResponse)
async def resend_email_log(
    log_id: int,
    payload: ResendEmailLogRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Re-send an existing email log's message, optionally to a corrected address.

    The target defaults to the prospect's current primary address (falling back to the address the
    log was sent to). A different address is folded into the prospect as its new primary, so the
    prospect — and any pending follow-up that reads it at dispatch — reaches the working address.
    """
    from models.prospect_db import ProspectDB
    from services.prospect_emails import sync_prospect_emails
    from services.sending_identity import SendingNotConfiguredError, resolve_sending_identity
    from services.unsubscribe_service import unsubscribe_service

    log: EmailLog | None = db.execute(
        select(EmailLog).where(EmailLog.id == log_id, EmailLog.user_id == current_user.id)
    ).scalar_one_or_none()
    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email log not found")

    prospect: ProspectDB | None = db.get(ProspectDB, log.prospect_id) if log.prospect_id else None
    target_email: str = (payload.email or "").strip() or (prospect.email if prospect else None) or log.recipient_email
    if not target_email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Aucune adresse e-mail cible")

    try:
        resolve_sending_identity(db, current_user.id)
    except SendingNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if unsubscribe_service.is_unsubscribed(db, target_email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{target_email} s'est désabonné")

    # A corrected address becomes the prospect's primary, so the pending follow-up reaches it too.
    if prospect is not None and target_email.lower() != (prospect.email or "").lower():
        sync_prospect_emails(prospect, primary=target_email)
        db.add(prospect)
        db.commit()

    # The stored body already carries a footer for the old recipient — strip it so the shared send
    # path adds a fresh, correct one for the target address.
    body_html: str = unsubscribe_service.strip_unsubscribe_footer(log.body_html or "")

    sending = EmailSendingService(db)
    return await sending.send_via_user_identity(
        user_id=current_user.id,
        recipient_email=target_email,
        subject=log.subject,
        body_html=body_html,
        recipient_name=log.recipient_name,
        prospect_id=str(log.prospect_id) if log.prospect_id else None,
        campaign_id=str(log.campaign_id) if log.campaign_id else None,
    )


@router.get("/logs/{log_id}/conversation", response_model=ConversationResponse)
async def get_conversation(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """
    Return the full user↔prospect exchange around a send, oldest first.

    Inbound bodies are plain text only — the untrusted HTML is stripped
    server-side, never shipped to the UI.
    """
    # Classify replies captured before the intent feature (persisted → converges
    # to zero LLM calls; identical content reuses stored verdicts).
    await conversation_service.backfill_intents(db, current_user.id, log_id)
    items = conversation_service.get_conversation(db, current_user.id, log_id)
    if items is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email introuvable")
    return ConversationResponse(items=items)


@router.get("/replies/pending", response_model=PendingRepliesResponse)
async def get_pending_replies(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PendingRepliesResponse:
    """The « à traiter » queue: human replies not yet answered, newest first."""
    items = conversation_service.pending_replies(db, current_user.id)
    return PendingRepliesResponse(count=len(items), items=items)


@router.post("/replies/{reply_id}/handled", status_code=status.HTTP_204_NO_CONTENT)
async def mark_reply_handled(
    reply_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Mark a reply as dealt with (e.g. answered from the user's own mailbox)."""
    if not conversation_service.mark_handled(db, current_user.id, reply_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réponse introuvable")


@router.post("/replies/{reply_id}/unsubscribe", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_from_reply(
    reply_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """
    Honour an unsubscribe request expressed in a reply (user-validated, one click).

    Adds the sender to the unsubscribe list — no further outreach will reach
    them — and marks the reply handled. Never triggered automatically by the
    LLM verdict: the user clicks.
    """
    from models.email_reply import EmailReply
    from services.unsubscribe_service import unsubscribe_service

    reply: EmailReply | None = db.get(EmailReply, reply_id)
    if reply is None or reply.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réponse introuvable")
    unsubscribe_service.unsubscribe(
        db,
        reply.from_email,
        prospect_id=reply.prospect_id,
        user_id=current_user.id,
        reason="Demande exprimée dans une réponse email",
    )
    conversation_service.mark_handled(db, current_user.id, reply_id)


@router.post("/replies/{reply_id}/reply")
async def reply_to_prospect(
    reply_id: int,
    payload: ReplySendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Answer a prospect's reply from the app (threaded via In-Reply-To/References).

    Sent through the user's active identity, without the outreach unsubscribe
    footer, and excluded from the outreach funnel stats. Marks every pending
    reply from that sender as handled on success.
    """
    body_html = (payload.body_html or "").strip()
    if not body_html:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Message vide")
    result = await conversation_service.send_reply(db, current_user.id, reply_id, body_html)
    if result.get("error") == "not_found":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réponse introuvable")
    return result


@router.get("/stats", response_model=EmailStatsResponse)
async def get_email_stats(
    campaign_id: str = Query(None, description="Filter by campaign ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get email statistics for the current user.
    """
    filters: list[object] = [EmailLog.user_id == current_user.id]
    if campaign_id:
        filters.append(EmailLog.campaign_id == campaign_id)

    counts = aggregate_email_log_counts(db, *filters)
    rates = compute_engagement_rates(counts)

    return EmailStatsResponse(
        total_sent=counts.sent,
        total_delivered=counts.delivered,
        total_opened=counts.opened,
        total_clicked=counts.clicked,
        total_replied=counts.replied,
        total_bounced=counts.bounced,
        total_failed=counts.failed,
        delivery_rate=rates.delivery_rate,
        open_rate=rates.open_rate,
        click_rate=rates.click_rate,
        reply_rate=rates.reply_rate,
    )
