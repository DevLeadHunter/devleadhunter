"""SMS orchestration — normalise, guard, send, log.

Sends ONE relance SMS to a prospect: normalise the number to E.164, verify it is
a mobile, honour the per-user STOP suppression list, send through the configured
provider, and log the outcome. The legal send window is enforced by the caller
(the queue) and re-checked here as a hard backstop. The body carries the plain
demo URL (never a shortened link — French operators filter those) and always the
mandatory « STOP au 36180 » opt-out mention.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.config import settings
from enums.sms_status import SmsStatus
from models.prospect_db import ProspectDB
from models.sms_config import SmsConfig
from models.sms_message import SmsMessage
from models.sms_reply import SmsReply
from models.sms_suppression import SmsSuppression
from services.activity_log_service import CATEGORY_SMS, STATUS_WARNING, activity_log_service
from services.notification_service import notification_service
from services.pricing_service import PricingService
from services.prospect_phones import sync_prospect_phones
from services.sms.gsm_segments import segment_count, to_gsm7
from services.sms.phone_normalizer import is_mobile_fr, to_e164_fr
from services.sms.pricing import estimate_price_cents
from services.sms.send_window import is_within_window, next_send_slot, now_in_paris
from services.sms.sms_provider import SmsProvider, SmsSendResult
from services.sms.smsmode_provider import smsmode_provider
from services.sms.templates import (
    DEFAULT_FIRST_CONTACT_KEY,
    DEFAULT_FOLLOW_UP_KEY,
    SmsTemplate,
    find_sms_template,
    render_sms_template,
)
from services.sms_variables import SmsVariables

logger = logging.getLogger(__name__)

# Mandatory opt-out mention appended to every marketing SMS (36180 = the free
# French STOP short code operators route back to the provider).
_STOP_MENTION: str = " STOP au 36180"


class SmsSendOutcome:
    """Result of a prospect-level send attempt (thin wrapper for the route)."""

    def __init__(self, *, sent: bool, reason: str | None = None, message: SmsMessage | None = None) -> None:
        self.sent = sent
        self.reason = reason
        self.message = message


class SmsService:
    """Send relance SMS and manage the STOP suppression list."""

    def __init__(self, provider: SmsProvider | None = None) -> None:
        """Bind the SMS provider (defaults to smsmode)."""
        self._provider: SmsProvider = provider or smsmode_provider

    def is_suppressed(self, db: Session, user_id: int, phone_e164: str) -> bool:
        """Whether *phone_e164* opted out of this user's SMS.

        Args:
            db: Active database session.
            user_id: Sender.
            phone_e164: Normalised number.

        Returns:
            ``True`` when the number is on the user's STOP list.
        """
        return (
            db.query(SmsSuppression.id)
            .filter(SmsSuppression.user_id == user_id, SmsSuppression.phone_e164 == phone_e164)
            .first()
            is not None
        )

    def suppress(self, db: Session, user_id: int, phone_e164: str, *, reason: str = "stop") -> None:
        """Add a number to the user's STOP list (idempotent).

        Args:
            db: Active database session.
            user_id: Sender.
            phone_e164: Normalised number to suppress.
            reason: ``stop`` (opt-out reply) or ``manual``.
        """
        if not phone_e164 or self.is_suppressed(db, user_id, phone_e164):
            return
        db.add(SmsSuppression(user_id=user_id, phone_e164=phone_e164, reason=reason))
        db.commit()
        logger.info("SMS suppression added for user %s (%s)", user_id, reason)

    def legal_window_refusal(self) -> str | None:
        """Refusal reason when the current Paris time is outside the legal SMS window.

        Marketing SMS is only legal Mon–Fri 8h–20h, Sat 10h–19h, never Sunday or a
        French public holiday — a HARD guardrail, whatever the user configured.

        Returns:
            A human refusal naming the next legal slot, or ``None`` when a send may go out now.
        """
        now = now_in_paris()
        if is_within_window(now):
            return None
        slot = next_send_slot(now)
        return (
            "Hors de la fenêtre légale d'envoi SMS (lun–ven 8h–20h, sam 10h–19h, jamais dimanche ni jour férié). "
            f"Prochain créneau : {slot.strftime('%d/%m à %Hh%M')}."
        )

    def log_window_block(self, user_id: int, *, prospect_id: int | None = None, detail: str | None = None) -> None:
        """Record in the activity feed that a relance was blocked by the legal window.

        Args:
            user_id: Owner of the blocked send.
            prospect_id: Prospect the relance targeted, when known.
            detail: The refusal reason (names the next legal slot).
        """
        activity_log_service.record(
            category=CATEGORY_SMS,
            action="sms_window_blocked",
            status=STATUS_WARNING,
            title="Relance SMS bloquée · hors fenêtre légale d'envoi",
            detail=detail,
            user_id=user_id,
            entity_type="prospect" if prospect_id else None,
            entity_id=prospect_id,
        )

    def render_template_body(self, template: SmsTemplate, variables: dict[str, str]) -> str:
        """Render a library template as the editable text of the composer (STOP mention excluded).

        Args:
            template: The library template.
            variables: The prospect's substitution map (see :class:`SmsVariables`).

        Returns:
            The GSM-7 body, without the STOP mention the send appends.
        """
        return to_gsm7(render_sms_template(template.body, variables))

    def compose_from_template(self, template: SmsTemplate, variables: dict[str, str]) -> str:
        """Render a library template into a ready-to-send body, STOP mention included.

        Args:
            template: The library template.
            variables: The prospect's substitution map.

        Returns:
            The full message body.
        """
        return self.compose_manual_body(self.render_template_body(template, variables))

    async def send_to_prospect(
        self,
        db: Session,
        *,
        user_id: int,
        prospect: ProspectDB,
        config: SmsConfig,
        demo_url: str,
        cold: bool = False,
        template_key: str | None = None,
        video_url: str = "",
    ) -> SmsSendOutcome:
        """Send one SMS (J+30 relance or first contact) to *prospect* from a library template, logging the outcome.

        Without an explicit ``template_key``, a first contact renders the default first-contact
        template and a relance renders the template chosen in the user's SMS config.

        Args:
            db: Active database session.
            user_id: Sender.
            prospect: Recipient prospect.
            config: The user's SMS config (sender + relance template).
            demo_url: Full demo URL to push (rendered without scheme by the templates).
            cold: Whether this is a cold first contact rather than a relance.
            template_key: Library template to render instead of the configured one.
            video_url: Full URL of the prospect's video page, for the templates that link it.

        Returns:
            The send outcome (``sent`` + reason when skipped).
        """
        # A configured sender is the single switch: no separate « enabled » flag.
        if not config.sender:
            return SmsSendOutcome(sent=False, reason="Expéditeur SMS non configuré")
        if not self._provider.is_configured:
            return SmsSendOutcome(sent=False, reason="smsmode non configuré")
        refusal = self.legal_window_refusal()
        if refusal:
            self.log_window_block(user_id, prospect_id=prospect.id, detail=refusal)
            return SmsSendOutcome(sent=False, reason=refusal)

        to_e164 = to_e164_fr(prospect.phone)
        if not to_e164 or not is_mobile_fr(prospect.phone):
            return SmsSendOutcome(sent=False, reason="Pas de mobile 06/07 pour ce prospect")
        if self.is_suppressed(db, user_id, to_e164):
            return SmsSendOutcome(sent=False, reason="Numéro désinscrit (STOP)")

        default_key = DEFAULT_FIRST_CONTACT_KEY if cold else (config.relance_template_key or DEFAULT_FOLLOW_UP_KEY)
        template = find_sms_template(template_key or default_key)
        if template is None:
            return SmsSendOutcome(sent=False, reason="Modèle SMS introuvable")
        variables = SmsVariables.build_for_prospect(
            db,
            user_id=user_id,
            prospect=prospect,
            demo_url=demo_url,
            video_url=video_url,
            sale_price_cents=PricingService.sale_price_cents(db, user_id),
        )
        body = self.compose_from_template(template, variables)
        if segment_count(body) > 1:
            # Over one segment: dropping the first name is the cheapest cut that keeps the message whole.
            body = self.compose_from_template(template, {**variables, SmsVariables.SALUTATION: "Bonjour"})
        message = SmsMessage(
            user_id=user_id,
            prospect_id=prospect.id,
            recipient_name=prospect.name,
            to_e164=to_e164,
            sender=config.sender,
            body=body,
            status=SmsStatus.PENDING.value,
            segments=segment_count(body),
        )
        return await self._send_and_log(db, message=message)

    def compose_manual_body(self, text: str) -> str:
        """Append the mandatory STOP mention to a free-text manual SMS (idempotent).

        Args:
            text: The body typed by the user.

        Returns:
            The body with the ``STOP au 36180`` mention appended once.
        """
        cleaned = to_gsm7((text or "").strip())
        if "36180" in cleaned:
            return cleaned
        return cleaned + _STOP_MENTION

    async def send_manual(
        self,
        db: Session,
        *,
        user_id: int,
        config: SmsConfig,
        to_raw: str,
        text: str,
        prospect_id: int | None = None,
        recipient_name: str | None = None,
    ) -> SmsSendOutcome:
        """Send one free-text SMS to a bare number (manual composer / self-test).

        Args:
            db: Active database session.
            user_id: Sender.
            config: The user's SMS config (sender).
            to_raw: Recipient number as typed (any French format).
            text: Free-text body (the STOP mention is appended automatically).
            prospect_id: Prospect id, when the number belongs to a saved prospect.
            recipient_name: Display label when there is no saved prospect.

        Returns:
            The send outcome (``sent`` + reason when skipped).
        """
        # A configured sender is the channel's only switch.
        if not config.sender:
            return SmsSendOutcome(sent=False, reason="Renseignez un nom d'expéditeur dans Paramètres → Relance SMS")
        if not self._provider.is_configured:
            return SmsSendOutcome(sent=False, reason="smsmode non configuré")
        # The legal window guards marketing to a saved prospect; a bare-number self-test stays free.
        if prospect_id is not None:
            refusal = self.legal_window_refusal()
            if refusal:
                self.log_window_block(user_id, prospect_id=prospect_id, detail=refusal)
                return SmsSendOutcome(sent=False, reason=refusal)

        to_e164 = to_e164_fr(to_raw)
        if not to_e164 or not is_mobile_fr(to_raw):
            return SmsSendOutcome(sent=False, reason="Numéro invalide : un mobile français 06/07 est requis")
        if self.is_suppressed(db, user_id, to_e164):
            return SmsSendOutcome(sent=False, reason="Numéro désinscrit (STOP)")
        body = self.compose_manual_body(text)
        if not body:
            return SmsSendOutcome(sent=False, reason="Message vide")
        # Hard cap at one segment: a longer body would silently bill (and send) several SMS.
        segments = segment_count(body)
        if segments > 1:
            return SmsSendOutcome(
                sent=False,
                reason=f"Message trop long : il partirait en {segments} SMS. Raccourcissez-le pour tenir en 1 seul.",
            )

        message = SmsMessage(
            user_id=user_id,
            prospect_id=prospect_id,
            recipient_name=recipient_name,
            to_e164=to_e164,
            sender=config.sender,
            body=body,
            status=SmsStatus.PENDING.value,
            segments=segments,
        )
        outcome = await self._send_and_log(db, message=message)
        # A manual contact supersedes the campaigns: nothing automated may double it.
        if outcome.sent and prospect_id is not None:
            self._hold_back_campaign_sends(db, prospect_id, label="Contacté manuellement (SMS)")
        return outcome

    async def _send_and_log(self, db: Session, *, message: SmsMessage) -> SmsSendOutcome:
        """Persist the row, hand it to the provider, record the outcome, notify.

        Args:
            db: Active database session.
            message: A ready-to-send SMS row (recipient, sender, body set).

        Returns:
            The send outcome.
        """
        db.add(message)
        db.commit()
        db.refresh(message)

        base_url = settings.api_base_url
        callback_url = f"{base_url}/api/v1/sms/callbacks/dlr" if base_url else None
        # Tell smsmode where to POST an incoming reply (STOP opt-out), so désinscriptions reach us.
        callback_url_mo = f"{base_url}/api/v1/sms/callbacks/stop" if base_url else None
        result: SmsSendResult = await self._provider.send(
            to_e164=message.to_e164,
            sender=message.sender,
            text=message.body,
            # smsmode requires refClient to be 3–140 chars, so a bare id ("1") is rejected.
            ref_client=f"dlh-{message.id}",
            callback_url=callback_url,
            callback_url_mo=callback_url_mo,
        )
        if result.success:
            message.status = SmsStatus.SENT.value
            message.provider_message_id = result.provider_message_id
            # smsmode returns no price for our account, so fall back to a segment-based estimate.
            message.price_cents = (
                result.price_cents if result.price_cents is not None else estimate_price_cents(message.segments)
            )
        else:
            message.status = SmsStatus.FAILED.value
            message.error = result.error
        db.commit()
        db.refresh(message)
        if result.success and message.prospect_id is not None:
            self._mark_prospect_contacted(db, message.prospect_id)
        await self._notify_send(db, message, success=result.success)
        return SmsSendOutcome(sent=result.success, reason=result.error, message=message)

    def _mark_prospect_contacted(self, db: Session, prospect_id: int) -> None:
        """Flag the prospect as contacted after a successful send — mirrors the email path (best-effort).

        Args:
            db: Active database session.
            prospect_id: The prospect who just received an SMS.
        """
        try:
            prospect = db.query(ProspectDB).filter(ProspectDB.id == prospect_id).first()
            if prospect is not None and not prospect.contacted:
                prospect.contacted = True
                db.commit()
        except Exception as exc:
            logger.warning("Could not mark prospect %s as contacted: %s", prospect_id, exc)

    def _hold_back_campaign_sends(self, db: Session, prospect_id: int, *, label: str) -> None:
        """Skip the prospect's pending campaign sends (initials + follow-ups) after a manual contact (best-effort).

        Args:
            db: Active database session.
            prospect_id: The prospect whose queued sends must not double the manual one.
            label: Skip reason shown on the campaign queue tab.
        """
        try:
            # Local import: campaign_queue_service dispatches through this service (cycle otherwise).
            from services.campaign_queue_service import CampaignQueueService

            CampaignQueueService(db).skip_pending_for_prospect(prospect_id, label=label)
        except Exception as exc:
            logger.warning("Could not hold back campaign sends for prospect %s: %s", prospect_id, exc)

    async def _notify_send(self, db: Session, message: SmsMessage, *, success: bool) -> None:
        """Raise the send/failure notification for a just-sent SMS (best-effort).

        Args:
            db: Active database session.
            message: The persisted SMS row.
            success: Whether the provider accepted the send.
        """
        await notification_service.notify_sms_event(
            db,
            user_id=message.user_id,
            event_name="sms_sent" if success else "sms_failed",
            prospect_id=message.prospect_id,
            fallback_name=message.recipient_name or message.to_e164,
        )

    def record_reply(
        self,
        db: Session,
        *,
        user_id: int,
        prospect_id: int | None,
        from_raw: str,
        body: str,
        received_at: datetime | None = None,
    ) -> SmsReply:
        """Consign an SMS reply received on the operator's own phone (the sender is one-way).

        A reply is a definitive human signal: the prospect becomes contacted, his pending
        campaign sends are held back, and an unknown number is folded into his phone list
        (after the existing ones — never promoted to primary).

        Args:
            db: Active database session.
            user_id: Owner consigning the reply.
            prospect_id: Prospect the reply belongs to (``None`` for a bare number).
            from_raw: Number the prospect wrote from, any French format.
            body: Message text as received.
            received_at: When the reply arrived (defaults to now, UTC).

        Returns:
            The persisted reply row.

        Raises:
            ValueError: On an unparseable number, an empty body, or an unknown prospect.
        """
        from_e164 = to_e164_fr(from_raw)
        if not from_e164:
            raise ValueError("Numéro invalide : un numéro français est requis")
        text = (body or "").strip()
        if not text:
            raise ValueError("Message vide")
        prospect: ProspectDB | None = None
        if prospect_id is not None:
            prospect = db.query(ProspectDB).filter(ProspectDB.id == prospect_id, ProspectDB.user_id == user_id).first()
            if prospect is None:
                raise ValueError("Prospect introuvable")
        reply = SmsReply(
            user_id=user_id,
            prospect_id=prospect_id,
            from_number=from_e164,
            body=text,
            received_at=received_at or datetime.utcnow(),
        )
        db.add(reply)
        if prospect is not None:
            prospect.contacted = True
            sync_prospect_phones(prospect, add=[from_e164])
        db.commit()
        db.refresh(reply)
        if prospect_id is not None:
            self._hold_back_campaign_sends(db, prospect_id, label="Le prospect a répondu (SMS)")
        return reply

    def list_thread(self, db: Session, user_id: int, prospect_id: int) -> tuple[list[SmsMessage], list[SmsReply]]:
        """Return a prospect's SMS thread material — sent messages and consigned replies, oldest first.

        Args:
            db: Active database session.
            user_id: Owner.
            prospect_id: The prospect whose thread is displayed.

        Returns:
            ``(sent, replies)`` lists, each ordered oldest-first.
        """
        sent = (
            db.query(SmsMessage)
            .filter(SmsMessage.user_id == user_id, SmsMessage.prospect_id == prospect_id)
            .order_by(SmsMessage.created_at.asc())
            .all()
        )
        replies = (
            db.query(SmsReply)
            .filter(SmsReply.user_id == user_id, SmsReply.prospect_id == prospect_id)
            .order_by(SmsReply.received_at.asc())
            .all()
        )
        return sent, replies

    def delete_reply(self, db: Session, user_id: int, reply_id: int) -> bool:
        """Delete one consigned reply (typo repair).

        Args:
            db: Active database session.
            user_id: Owner.
            reply_id: The reply row to delete.

        Returns:
            ``True`` when a row was deleted, ``False`` when none matched.
        """
        reply = db.query(SmsReply).filter(SmsReply.id == reply_id, SmsReply.user_id == user_id).first()
        if reply is None:
            return False
        db.delete(reply)
        db.commit()
        return True

    def list_messages(self, db: Session, user_id: int, *, limit: int = 500) -> list[tuple[SmsMessage, str | None]]:
        """Return the user's sent SMS (newest first) with the prospect name resolved.

        Args:
            db: Active database session.
            user_id: Owner.
            limit: Max rows to return.

        Returns:
            ``(message, prospect_name)`` pairs; the name is ``None`` for a manual send.
        """
        rows = db.execute(
            select(SmsMessage, ProspectDB.name)
            .join(ProspectDB, ProspectDB.id == SmsMessage.prospect_id, isouter=True)
            .where(SmsMessage.user_id == user_id)
            .order_by(SmsMessage.created_at.desc())
            .limit(limit)
        ).all()
        return [(row[0], row[1]) for row in rows]

    def stats(self, db: Session, user_id: int) -> dict[str, int]:
        """Aggregate counts + total cost of the user's SMS.

        Args:
            db: Active database session.
            user_id: Owner.

        Returns:
            Totals keyed by ``total``, ``sent``, ``delivered``, ``failed``, ``pending``, ``cost_cents``.
        """
        counts = dict(
            db.execute(
                select(SmsMessage.status, func.count()).where(SmsMessage.user_id == user_id).group_by(SmsMessage.status)
            ).all()
        )
        cost = db.execute(
            select(func.coalesce(func.sum(SmsMessage.price_cents), 0)).where(SmsMessage.user_id == user_id)
        ).scalar_one()
        sent = int(counts.get(SmsStatus.SENT.value, 0))
        delivered = int(counts.get(SmsStatus.DELIVERED.value, 0))
        # « Envoyés » counts everything that reached the provider (sent + later delivered).
        return {
            "total": sum(int(v) for v in counts.values()),
            "sent": sent + delivered,
            "delivered": delivered,
            "failed": int(counts.get(SmsStatus.FAILED.value, 0)),
            "pending": int(counts.get(SmsStatus.PENDING.value, 0)),
            "cost_cents": int(cost or 0),
        }


sms_service = SmsService()
