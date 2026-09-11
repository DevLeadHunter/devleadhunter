"""
SMS routes — sender config, relance candidates + send, provider callbacks.

The SMS channel re-contacts prospects who ignored the cold email, pushing them
back to their demo. Sender config is per user (Paramètres → SMS) ; the smsmode
account is a single platform account. The DLR and STOP callbacks are public
(called by smsmode) — like the demo-events and Storyblok webhooks.
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from enums.sms_status import SmsStatus
from enums.sms_template_category import SmsTemplateCategory
from models.prospect_db import ProspectDB
from models.sms_config import SmsConfig
from models.sms_message import SmsMessage
from models.user import User
from schemas.sms import (
    SmsAutomationUpdate,
    SmsBulkSendResponse,
    SmsConfigResponse,
    SmsConfigUpdate,
    SmsCreditResponse,
    SmsManualSendRequest,
    SmsMessageResponse,
    SmsMessagesResponse,
    SmsRelanceCandidateResponse,
    SmsReplyCreateRequest,
    SmsReplyResponse,
    SmsSendResponse,
    SmsStatsResponse,
    SmsTemplatePreviewResponse,
    SmsTemplateResponse,
    SmsThreadItemResponse,
    SmsThreadResponse,
)
from services.auth_service import get_current_user, require_admin
from services.demo_site_service import demo_site_service
from services.demo_video_service import has_ready_video, video_page_url
from services.notification_service import notification_service
from services.pricing_service import PricingService
from services.sms.dlr import (
    classify_dlr,
    dlr_message_id,
    dlr_ref_client,
    dlr_status_detail,
    dlr_status_value,
)
from services.sms.gsm_segments import segment_count
from services.sms.mo import mo_is_stop, mo_origin_message_id, mo_ref_client, mo_sender_number
from services.sms.phone_normalizer import to_e164_fr
from services.sms.smsmode_provider import smsmode_provider
from services.sms.templates import (
    DEFAULT_FIRST_CONTACT_KEY,
    DEFAULT_FOLLOW_UP_KEY,
    find_sms_template,
    list_sms_templates,
)
from services.sms_config_service import sms_config_service
from services.sms_relance_service import sms_relance_service
from services.sms_service import sms_service
from services.sms_variables import SmsVariables
from services.tracking_links import sms_tracked_link

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sms", tags=["sms"])


def _config_response(config: SmsConfig | None) -> SmsConfigResponse:
    """Serialize a user's SMS config (sender + automation opt-ins), defaults when unset.

    Args:
        config: The user's config row, or ``None`` when never set.

    Returns:
        The response carrying the sender, provider readiness and automation flags.
    """
    return SmsConfigResponse(
        sender=config.sender if config else "",
        provider_ready=bool(settings.smsmode_api_key),
        cold_sms_enabled=bool(config.cold_sms_enabled) if config else False,
        auto_relance_enabled=bool(config.auto_relance_enabled) if config else False,
        auto_relance_after_days=config.auto_relance_after_days if config else 30,
        relance_template_key=config.relance_template_key if config else DEFAULT_FOLLOW_UP_KEY,
    )


@router.get("/config", response_model=SmsConfigResponse)
async def get_sms_config(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> SmsConfigResponse:
    """Return the current user's SMS sender + automation configuration."""
    return _config_response(sms_config_service.get(db, current_user.id))


@router.put("/config", response_model=SmsConfigResponse)
async def update_sms_config(
    payload: SmsConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmsConfigResponse:
    """Set the current user's SMS sender (a configured sender turns the channel on)."""
    try:
        config = sms_config_service.upsert(db, current_user.id, sender=payload.sender)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _config_response(config)


@router.put("/config/automation", response_model=SmsConfigResponse)
async def update_sms_automation(
    payload: SmsAutomationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmsConfigResponse:
    """Toggle the current user's SMS automations (cold-SMS + auto-relance) and pick the relance template."""
    try:
        config = sms_config_service.set_automation(
            db,
            current_user.id,
            cold_sms_enabled=payload.cold_sms_enabled,
            auto_relance_enabled=payload.auto_relance_enabled,
            auto_relance_after_days=payload.auto_relance_after_days,
            relance_template_key=payload.relance_template_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _config_response(config)


@router.get("/relance-candidates", response_model=list[SmsRelanceCandidateResponse])
async def list_relance_candidates(
    after_days: int = 30,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SmsRelanceCandidateResponse]:
    """List prospects eligible for an SMS relance (unanswered email + mobile + live demo)."""
    candidates = sms_relance_service.find_candidates(db, current_user.id, after_days=after_days, limit=limit)
    return [
        SmsRelanceCandidateResponse(
            prospect_id=candidate.prospect.id,
            name=candidate.prospect.name,
            city=candidate.prospect.city,
            phone=candidate.prospect.phone,
            demo_url=candidate.demo_url,
            emailed_at=candidate.emailed_at,
        )
        for candidate in candidates
    ]


@router.post("/relance/{prospect_id}", response_model=SmsSendResponse)
async def send_relance(
    prospect_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmsSendResponse:
    """Send a relance SMS to one eligible prospect."""
    refusal = sms_service.legal_window_refusal()
    if refusal:
        sms_service.log_window_block(current_user.id, prospect_id=prospect_id, detail=refusal)
        return SmsSendResponse(sent=False, reason=refusal)
    candidates = sms_relance_service.find_candidates(db, current_user.id, limit=200)
    candidate = next((c for c in candidates if c.prospect.id == prospect_id), None)
    if candidate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prospect non éligible à une relance SMS (déjà relancé, pas de mobile, ou pas de démo active).",
        )
    sent = await sms_relance_service.send_relance(db, current_user.id, candidate)
    return SmsSendResponse(sent=sent, reason=None if sent else "Envoi refusé par le provider")


@router.post("/relance", response_model=SmsBulkSendResponse)
async def send_relance_bulk(
    limit: int = 20,
    after_days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmsBulkSendResponse:
    """Send relance SMS to the eligible prospects, up to *limit*."""
    candidates = sms_relance_service.find_candidates(db, current_user.id, after_days=after_days, limit=limit)
    refusal = sms_service.legal_window_refusal()
    if refusal is not None:
        sms_service.log_window_block(current_user.id, detail=refusal)
        return SmsBulkSendResponse(sent=0, skipped=len(candidates))
    sent = 0
    for candidate in candidates:
        if await sms_relance_service.send_relance(db, current_user.id, candidate):
            sent += 1
    return SmsBulkSendResponse(sent=sent, skipped=len(candidates) - sent)


@router.get("/messages", response_model=SmsMessagesResponse)
async def list_messages(
    limit: int = 500,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmsMessagesResponse:
    """Return the current user's sent SMS (newest first) — the « Suivi des SMS » history."""
    rows = sms_service.list_messages(db, current_user.id, limit=limit)
    messages = [
        SmsMessageResponse(
            id=message.id,
            prospect_id=message.prospect_id,
            recipient_name=prospect_name or message.recipient_name,
            to_e164=message.to_e164,
            sender=message.sender,
            body=message.body,
            status=message.status,
            status_detail=message.status_detail,
            segments=message.segments,
            price_cents=message.price_cents,
            error=message.error,
            created_at=message.created_at,
            delivered_at=message.delivered_at,
        )
        for message, prospect_name in rows
    ]
    return SmsMessagesResponse(total=len(messages), messages=messages)


@router.post("/replies", response_model=SmsReplyResponse, status_code=status.HTTP_201_CREATED)
async def create_sms_reply(
    payload: SmsReplyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmsReplyResponse:
    """Consign an SMS reply received on the operator's phone (manual entry — the sender is one-way)."""
    try:
        reply = sms_service.record_reply(
            db,
            user_id=current_user.id,
            prospect_id=payload.prospect_id,
            from_raw=payload.from_number,
            body=payload.body,
            received_at=payload.received_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SmsReplyResponse(
        id=reply.id,
        prospect_id=reply.prospect_id,
        from_number=reply.from_number,
        body=reply.body,
        received_at=reply.received_at,
        created_at=reply.created_at,
    )


@router.delete("/replies/{reply_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sms_reply(
    reply_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete one consigned reply (typo repair)."""
    if not sms_service.delete_reply(db, current_user.id, reply_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réponse introuvable.")


@router.get("/thread/{prospect_id}", response_model=SmsThreadResponse)
async def get_sms_thread(
    prospect_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmsThreadResponse:
    """Return a prospect's SMS conversation — sent SMS and consigned replies, oldest first."""
    sent, replies = sms_service.list_thread(db, current_user.id, prospect_id)
    items = [
        SmsThreadItemResponse(
            kind="sent",
            id=message.id,
            body=message.body,
            at=message.created_at,
            number=message.to_e164,
            status=message.status,
            status_detail=message.status_detail,
        )
        for message in sent
    ] + [
        SmsThreadItemResponse(
            kind="received",
            id=reply.id,
            body=reply.body,
            at=reply.received_at,
            number=reply.from_number,
        )
        for reply in replies
    ]
    items.sort(key=lambda item: item.at)
    return SmsThreadResponse(prospect_id=prospect_id, items=items)


@router.get("/stats", response_model=SmsStatsResponse)
async def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SmsStatsResponse:
    """Return aggregate counters of the current user's SMS channel."""
    return SmsStatsResponse(**sms_service.stats(db, current_user.id))


@router.get("/credit", response_model=SmsCreditResponse)
async def get_credit(_admin: User = Depends(require_admin)) -> SmsCreditResponse:
    """Return the platform smsmode account's remaining credit balance.

    Account-level (single shared smsmode account), so restricted to admins. Never
    raises: an unreadable balance comes back as ``credits=null``.
    """
    configured = smsmode_provider.is_configured
    credits = await smsmode_provider.get_credit_balance() if configured else None
    return SmsCreditResponse(configured=configured, credits=credits)


@router.get("/templates", response_model=list[SmsTemplateResponse])
async def list_templates(
    category: SmsTemplateCategory | None = None,
    current_user: User = Depends(get_current_user),
) -> list[SmsTemplateResponse]:
    """Return the SMS template library, optionally narrowed to one touch (first contact / follow-up)."""
    return [
        SmsTemplateResponse(
            key=template.key,
            name=template.name,
            category=template.category.value,
            body=template.body,
            variables=template.variables,
            is_default=template.key == DEFAULT_FIRST_CONTACT_KEY,
        )
        for template in list_sms_templates(category)
    ]


@router.get("/templates/{key}/preview", response_model=SmsTemplatePreviewResponse)
async def preview_template(
    key: str,
    prospect_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmsTemplatePreviewResponse:
    """Render a library template for one prospect — the text the composer starts from."""
    template = find_sms_template(key)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modèle SMS introuvable.")
    prospect = db.query(ProspectDB).filter(ProspectDB.id == prospect_id, ProspectDB.user_id == current_user.id).first()
    if prospect is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prospect introuvable.")

    needs_site = template.uses(SmsVariables.DEMO_LINK) or template.uses(SmsVariables.VIDEO_LINK)
    site = sms_relance_service.demo_for_prospect(db, current_user.id, prospect.id)
    if needs_site and site is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Ce prospect n'a pas de site démo à envoyer."
        )
    if needs_site and site is not None and site.status == DemoSiteStatus.EXPIRED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La démo de ce prospect est en veille : passez par la relance SMS, qui la réveille.",
        )
    if template.uses(SmsVariables.VIDEO_LINK) and (site is None or not has_ready_video(site)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Ce prospect n'a pas de vidéo de prospection générée."
        )
    if template.uses(SmsVariables.OLD_WEBSITE) and not prospect.website:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ce prospect n'a pas d'ancien site connu.")

    demo_url = ""
    video_url = ""
    if site is not None:
        demo_url = sms_tracked_link(demo_site_service.demo_url_for_slug(site.slug))
        if template.uses(SmsVariables.VIDEO_LINK):
            video_url = sms_tracked_link(video_page_url(site.slug))
    variables = SmsVariables.build_for_prospect(
        db,
        user_id=current_user.id,
        prospect=prospect,
        demo_url=demo_url,
        video_url=video_url,
        sale_price_cents=PricingService.sale_price_cents(db, current_user.id),
    )
    body = sms_service.render_template_body(template, variables)
    return SmsTemplatePreviewResponse(
        key=template.key, body=body, segments=segment_count(sms_service.compose_manual_body(body))
    )


@router.post("/send", response_model=SmsSendResponse)
async def send_manual_sms(
    payload: SmsManualSendRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SmsSendResponse:
    """Send one free-text SMS to a number (manual composer / self-test)."""
    config = sms_config_service.get(db, current_user.id)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configurez d'abord votre expéditeur dans Paramètres → Relance SMS.",
        )
    outcome = await sms_service.send_manual(
        db,
        user_id=current_user.id,
        config=config,
        to_raw=payload.to,
        text=payload.text,
        prospect_id=payload.prospect_id,
        recipient_name=payload.recipient_name,
    )
    return SmsSendResponse(sent=outcome.sent, reason=outcome.reason)


@router.post("/callbacks/dlr", status_code=status.HTTP_200_OK)
async def receive_dlr_callback(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    """Delivery-receipt callback from smsmode (public).

    Matches by ``messageId`` and updates the SMS status. Always answers 200 —
    even for an unknown id — so the provider does not retry in a loop.
    """
    try:
        payload = await request.json()
    except ValueError:
        return {"status": "ignored"}
    if not isinstance(payload, dict):
        return {"status": "ignored"}
    message = _match_dlr_message(db, payload)
    if message is None:
        logger.info("SMS DLR unmatched: %s", str(payload)[:300])
        return {"status": "ok"}

    new_status = classify_dlr(dlr_status_value(payload))
    detail = dlr_status_detail(payload)
    previous_status = message.status
    if new_status == SmsStatus.DELIVERED.value:
        message.status = SmsStatus.DELIVERED.value
        message.delivered_at = datetime.utcnow()
    elif new_status == SmsStatus.FAILED.value:
        message.status = SmsStatus.FAILED.value
        message.error = detail or dlr_status_value(payload) or "Non délivré"
    if detail:
        message.status_detail = detail
    db.commit()
    # Notify only on a real transition, so a provider re-sending the same DLR never double-pings.
    if message.status != previous_status and message.status in {SmsStatus.DELIVERED.value, SmsStatus.FAILED.value}:
        await notification_service.notify_sms_event(
            db,
            user_id=message.user_id,
            event_name="sms_delivered" if message.status == SmsStatus.DELIVERED.value else "sms_failed",
            prospect_id=message.prospect_id,
            fallback_name=message.recipient_name or message.to_e164,
            detail=detail if message.status == SmsStatus.FAILED.value else None,
        )
    return {"status": "ok"}


def _match_dlr_message(db: Session, payload: dict[str, object]) -> SmsMessage | None:
    """Find the SMS a DLR refers to, by provider id then by our ``dlh-<id>`` ref.

    Args:
        db: Active database session.
        payload: The DLR JSON body.

    Returns:
        The matching SMS row, or ``None`` when neither key resolves.
    """
    message_id = dlr_message_id(payload)
    if message_id:
        matched = db.query(SmsMessage).filter(SmsMessage.provider_message_id == message_id).first()
        if matched is not None:
            return matched
    ref = dlr_ref_client(payload)
    if ref.startswith("dlh-"):
        try:
            row_id = int(ref[len("dlh-") :])
        except ValueError:
            return None
        return db.query(SmsMessage).filter(SmsMessage.id == row_id).first()
    return None


@router.post("/callbacks/stop", status_code=status.HTTP_200_OK)
async def receive_stop_callback(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    """Incoming-message (MO) callback from smsmode — the STOP opt-out (public).

    smsmode POSTs every reply here (the ``callbackUrlMo`` we set on each send). We
    act only on a STOP (``body.stop`` or a STOP keyword): the number is suppressed
    for its sender so no further SMS goes out, and the owner is notified. The sent
    SMS is resolved by ``originMessageId`` / ``refClient`` first (precise), the
    number last. Always answers 200 so smsmode never retries in a loop.
    """
    try:
        payload = await request.json()
    except ValueError:
        return {"status": "ignored"}
    if not isinstance(payload, dict):
        return {"status": "ignored"}
    if not mo_is_stop(payload):
        # A non-STOP reply (rare with a one-way alphanumeric sender) — nothing to suppress.
        return {"status": "ok"}
    message = _match_stop_message(db, payload)
    if message is None:
        logger.info("SMS STOP unmatched: %s", str(payload)[:300])
        return {"status": "ok"}
    # Notify only on a NEW opt-out, so a re-sent STOP webhook never double-pings.
    already_suppressed = sms_service.is_suppressed(db, message.user_id, message.to_e164)
    sms_service.suppress(db, message.user_id, message.to_e164, reason="stop")
    if not already_suppressed:
        await notification_service.notify_sms_event(
            db,
            user_id=message.user_id,
            event_name="sms_stop",
            prospect_id=message.prospect_id,
            fallback_name=message.recipient_name or message.to_e164,
        )
    return {"status": "ok"}


def _match_stop_message(db: Session, payload: dict[str, object]) -> SmsMessage | None:
    """Find the sent SMS a STOP refers to, by origin id then our ``dlh-<id>`` ref, then the number.

    Args:
        db: Active database session.
        payload: The MO callback JSON body.

    Returns:
        The matching sent SMS row, or ``None`` when nothing resolves.
    """
    origin_id = mo_origin_message_id(payload)
    if origin_id:
        matched = db.query(SmsMessage).filter(SmsMessage.provider_message_id == origin_id).first()
        if matched is not None:
            return matched
    ref = mo_ref_client(payload)
    if ref.startswith("dlh-"):
        try:
            row_id = int(ref[len("dlh-") :])
        except ValueError:
            row_id = None
        if row_id is not None:
            matched = db.query(SmsMessage).filter(SmsMessage.id == row_id).first()
            if matched is not None:
                return matched
    number = mo_sender_number(payload)
    phone_e164 = to_e164_fr(number) or (number if number.startswith("+") else None)
    if phone_e164:
        return (
            db.query(SmsMessage).filter(SmsMessage.to_e164 == phone_e164).order_by(SmsMessage.created_at.desc()).first()
        )
    return None
