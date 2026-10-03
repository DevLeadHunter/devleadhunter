"""SMS orchestration — normalise, guard, send, log.

Sends ONE prospecting SMS (first contact or relance) to a prospect: refuse a country closed to
cold SMS, normalise the number in the prospect's own numbering, verify it is a mobile, honour
the per-user STOP suppression list and the « one first contact, one relance » rule, send through
the configured provider, and log the outcome with its cost. The legal send window is enforced by
the caller (the queue) and re-checked here in the prospect's timezone as a hard backstop. The
body carries the plain demo URL (never a shortened link — French operators filter those); the
opt-out mention is appended by smsmode itself (``body.stop``), in the shape the destination
country expects, so we only reserve its characters in the segment budget.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.config import settings
from enums.sms_message_kind import SmsMessageKind
from enums.sms_status import SmsStatus
from models.ai_assistant import AiAssistant
from models.prospect_db import ProspectDB
from models.sms_config import SmsConfig
from models.sms_message import SmsMessage
from models.sms_reply import SmsReply
from models.sms_suppression import SmsSuppression
from services.activity_log_service import CATEGORY_SMS, STATUS_WARNING, activity_log_service
from services.ai_assistant.assistant_service import ai_assistant_service
from services.country_profiles import DEFAULT_COUNTRY_CODE, CountryProfiles
from services.email_variables import EmailVariables
from services.notification_service import notification_service
from services.pricing_service import PricingService
from services.prospect_phones import first_mobile_e164, sync_prospect_phones
from services.sms.gsm_segments import is_gsm7, segment_count_with_reserve, to_gsm7
from services.sms.opt_out_mention import SmsOptOutMention
from services.sms.phone_normalizer import PhoneNumberPlans, to_e164_fr
from services.sms.pricing import SmsPricing
from services.sms.send_window import SmsSendWindow
from services.sms.sms_provider import SmsProvider, SmsSendResult
from services.sms.smsmode_provider import smsmode_provider
from services.sms.templates import (
    DEFAULT_FIRST_CONTACT_KEY,
    DEFAULT_FOLLOW_UP_KEY,
    SmsTemplate,
    find_sms_template,
    render_sms_template,
    resolve_sms_template,
)
from services.sms_prospecting_rules import SmsProspectingRules
from services.sms_variables import SmsVariables

logger = logging.getLogger(__name__)

MARKETING_SMS_MAXIMUM_SEGMENTS: int = 2
SERVICE_SMS_MAXIMUM_SEGMENTS: int = 1
CONTACT_PHONE_VARIABLE: str = "telephone"
CONTACT_PHONE_MISSING_REFUSAL: str = "Renseignez votre téléphone de contact dans votre profil"
# The receptionist's pages in a body: its demo (/ia/…) or its video (/va/…), the short links (/s/ia/…) included.
_ASSISTANT_PAGE_LINK: re.Pattern[str] = re.compile(r"/(?:s/)?(?:ia|va)/[\w-]+")


@dataclass(frozen=True)
class ComposedSmsSegments:
    """What a typed SMS bills once smsmode appends the opt-out mention of its recipient's country."""

    characters: int
    segments: int
    maximum_segments: int
    is_unicode: bool


class SmsSendOutcome:
    """Result of a prospect-level send attempt (thin wrapper for the route).

    Attributes:
        sent: Whether smsmode accepted the message.
        reason: Why it did not leave, when it did not.
        message: The SMS row, once one was written.
        provider_text: The body smsmode acknowledged, its opt-out mention included, when returned.
        provider_segments: The segments smsmode bills, when returned.
    """

    def __init__(
        self,
        *,
        sent: bool,
        reason: str | None = None,
        message: SmsMessage | None = None,
        provider_text: str | None = None,
        provider_segments: int | None = None,
    ) -> None:
        self.sent = sent
        self.reason = reason
        self.message = message
        self.provider_text = provider_text
        self.provider_segments = provider_segments


class SmsService:
    """Send prospecting SMS and manage the STOP suppression list."""

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

    def legal_window_refusal(self, country: str | None = None) -> str | None:
        """Refusal reason when the current local time of *country* is outside the legal SMS window.

        Marketing SMS is only legal Mon–Fri 8h–20h, Sat 10h–19h, never Sunday or a public holiday of
        the prospect's country — a HARD guardrail, whatever the user configured.

        Args:
            country: ISO code of the recipient's country; ``None`` reads the French window.

        Returns:
            A human refusal naming the next legal slot, or ``None`` when a send may go out now.
        """
        window = SmsSendWindow(country)
        now = window.now()
        if window.is_open(now):
            return None
        slot = window.next_open_slot(now)
        timezone_hint = "" if window.country == "FR" else f" (fuseau {window.timezone.key})"
        return (
            "Hors de la fenêtre légale d'envoi SMS (lun–ven 8h–20h, sam 10h–19h, jamais dimanche ni jour férié). "
            f"Prochain créneau : {slot.strftime('%d/%m à %Hh%M')}{timezone_hint}."
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
        """Render a library template as the editable text of the composer, the body smsmode receives.

        Args:
            template: The library template.
            variables: The prospect's substitution map (see :class:`SmsVariables`).

        Returns:
            The GSM-7 body; smsmode appends the opt-out mention after it at send time.
        """
        return to_gsm7(render_sms_template(template.body, variables))

    def compose_from_template(self, template: SmsTemplate, variables: dict[str, str]) -> str:
        """Render a library template into the body sent to the provider (no mention: smsmode appends its own).

        Args:
            template: The library template.
            variables: The prospect's substitution map.

        Returns:
            The full message body.
        """
        return self.render_template_body(template, variables)

    def to_gsm7_body(self, text: str) -> str:
        """Trim a typed body and transliterate it to GSM-7 — the text smsmode receives.

        Args:
            text: The body typed by the user.

        Returns:
            The sendable body, without any opt-out mention (smsmode appends its own).
        """
        return to_gsm7((text or "").strip())

    @staticmethod
    def contact_phone_refusal(template: SmsTemplate, variables: dict[str, str]) -> str | None:
        """Why a template giving the sender's phone (``{telephone}``) cannot leave: that phone is not set.

        Args:
            template: The library template about to be rendered.
            variables: The prospect's substitution map.

        Returns:
            The French refusal, or ``None`` when the template needs no phone or the phone is set.
        """
        if template.uses(CONTACT_PHONE_VARIABLE) and not (variables.get(CONTACT_PHONE_VARIABLE) or "").strip():
            return CONTACT_PHONE_MISSING_REFUSAL
        return None

    def marketing_segment_count(self, body: str, *, country: str | None) -> int:
        """Segments a marketing body bills once smsmode appends the opt-out mention of the destination country.

        Args:
            body: The body as we send it.
            country: ISO code of the destination country.

        Returns:
            The billed segment count.
        """
        return segment_count_with_reserve(body, SmsOptOutMention.reserved_characters_for_country(country))

    def count_composed_segments(
        self, db: Session, *, user_id: int, text: str, prospect_id: int | None
    ) -> ComposedSmsSegments:
        """Count what a message typed in the composer bills, with the same rule as :meth:`send_manual`.

        The characters reserved for the opt-out mention follow the recipient: the country of the user's
        prospect, France for a bare number.

        Args:
            db: Active database session.
            user_id: The user typing the message.
            text: The message as typed.
            prospect_id: The recipient prospect, ``None`` for a bare number.

        Returns:
            The characters smsmode receives, the billed segments, the most segments allowed and the encoding.
        """
        prospect = self._owned_prospect(db, user_id, prospect_id)
        country = SmsProspectingRules.country_of(prospect) if prospect is not None else DEFAULT_COUNTRY_CODE
        body = self.to_gsm7_body(text)
        return ComposedSmsSegments(
            characters=len(body),
            segments=self.marketing_segment_count(body, country=country),
            maximum_segments=MARKETING_SMS_MAXIMUM_SEGMENTS,
            is_unicode=not is_gsm7(body),
        )

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
        """Send one SMS (relance or first contact) to *prospect* from a library template, logging the outcome.

        The prospect's history decides the touch: his first contact when he was never contacted, his
        relance after a first contact (an email, or a first-contact SMS), nothing once the relance went.
        A relance asked for a prospect never contacted is refused. Without an explicit ``template_key``,
        a first contact renders the default first-contact template and a relance renders the template
        chosen in the user's SMS config. A message that does not fit two segments, even without the
        first name, is refused: it would be billed thrice.

        Args:
            db: Active database session.
            user_id: Sender.
            prospect: Recipient prospect.
            config: The user's SMS config (sender + relance template).
            demo_url: Full demo URL to push (rendered without scheme by the templates).
            cold: Whether the caller starts a first contact (cold SMS, SMS campaign) rather than a relance.
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
        country_refusal = SmsProspectingRules.country_refusal(prospect)
        if country_refusal:
            return SmsSendOutcome(sent=False, reason=country_refusal)
        country = SmsProspectingRules.country_of(prospect)
        window_refusal = self.legal_window_refusal(country)
        if window_refusal:
            self.log_window_block(user_id, prospect_id=prospect.id, detail=window_refusal)
            return SmsSendOutcome(sent=False, reason=window_refusal)

        to_e164 = first_mobile_e164(prospect)
        if not to_e164:
            return SmsSendOutcome(sent=False, reason="Pas de mobile pour ce prospect dans la numérotation de son pays")
        if self.is_suppressed(db, user_id, to_e164):
            return SmsSendOutcome(sent=False, reason="Numéro désinscrit (STOP)")
        touch = SmsProspectingRules.next_touch(db, user_id, prospect.id)
        if touch is None:
            return SmsSendOutcome(sent=False, reason=SmsProspectingRules.SEQUENCE_COMPLETE)
        if not cold and touch is SmsMessageKind.FIRST_CONTACT:
            return SmsSendOutcome(sent=False, reason=SmsProspectingRules.NO_FIRST_CONTACT_BEFORE_FOLLOW_UP)

        default_key = DEFAULT_FIRST_CONTACT_KEY if cold else (config.relance_template_key or DEFAULT_FOLLOW_UP_KEY)
        template = find_sms_template(template_key or default_key)
        if template is None:
            return SmsSendOutcome(sent=False, reason="Modèle SMS introuvable")
        assistant: AiAssistant | None = ai_assistant_service.get_active_for_prospect(
            db, prospect_id=prospect.id, user_id=user_id
        )
        # A video template with no generated video falls back to its demo-link sibling.
        template = resolve_sms_template(
            template,
            video_ready=bool(video_url),
            assistant_video_ready=bool(EmailVariables.assistant_video_urls(assistant)[0]),
        )
        # An assistant template needs the prospect's active assistant, or the SMS would ship a hole.
        needs_assistant: bool = any(
            template.uses(name)
            for name in (
                SmsVariables.ASSISTANT_LINK,
                SmsVariables.ASSISTANT_VIDEO_LINK,
                SmsVariables.RECEPTIONIST_FIRST_NAME,
                SmsVariables.RECEPTIONIST,
                SmsVariables.VIRTUAL_ASSISTANT,
            )
        )
        if needs_assistant and assistant is None:
            return SmsSendOutcome(sent=False, reason="Pas d'assistant IA actif pour ce prospect")
        variables = SmsVariables.build_for_prospect(
            db,
            user_id=user_id,
            prospect=prospect,
            assistant=assistant,
            demo_url=demo_url,
            video_url=video_url,
            sale_price_cents=PricingService.sale_price_cents(db, user_id),
        )
        phone_refusal = self.contact_phone_refusal(template, variables)
        if phone_refusal:
            return SmsSendOutcome(sent=False, reason=phone_refusal)
        body = self.compose_from_template(template, variables)
        if self.marketing_segment_count(body, country=country) > MARKETING_SMS_MAXIMUM_SEGMENTS:
            # Over the budget: dropping the first name is the cheapest cut that keeps the message whole.
            body = self.compose_from_template(template, {**variables, SmsVariables.SALUTATION: "Bonjour"})
        segments = self.marketing_segment_count(body, country=country)
        if segments > MARKETING_SMS_MAXIMUM_SEGMENTS:
            logger.warning(
                "SMS template %s would take %s segments for prospect %s", template.key, segments, prospect.id
            )
            return SmsSendOutcome(
                sent=False,
                reason=(
                    f"Modèle « {template.name} » trop long pour ce prospect : il partirait en {segments} SMS, "
                    f"la limite est de {MARKETING_SMS_MAXIMUM_SEGMENTS}"
                ),
            )
        message = SmsMessage(
            user_id=user_id,
            prospect_id=prospect.id,
            recipient_name=prospect.name,
            to_e164=to_e164,
            sender=config.sender,
            body=body,
            status=SmsStatus.PENDING.value,
            segments=segments,
            kind=touch.value,
        )
        outcome = await self._send_and_log(db, message=message, opt_out_mention=True)
        if outcome.sent:
            self._start_assistant_ttl(db, assistant, body=body)
        return outcome

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
        """Send one free-text SMS to a number (manual composer / self-test), smsmode's opt-out mention included.

        A saved prospect must be the user's own and goes through the country guard; his number is read in his
        country's numbering (a Swiss ``079`` is ``+4179…``, never ``+337…``). A bare number must be a French
        mobile. A manual SMS ends the prospect's automated sequence: nothing automated may text him after it.

        Args:
            db: Active database session.
            user_id: Sender.
            config: The user's SMS config (sender).
            to_raw: Recipient number as typed.
            text: Free-text body (smsmode appends the opt-out mention).
            prospect_id: Prospect id, when the number belongs to a saved prospect.
            recipient_name: Display label when there is no saved prospect.

        Returns:
            The send outcome (``sent`` + reason when skipped).
        """
        channel_refusal = self._channel_refusal(config)
        if channel_refusal:
            return SmsSendOutcome(sent=False, reason=channel_refusal)
        prospect = self._owned_prospect(db, user_id, prospect_id)
        if prospect_id is not None and prospect is None:
            return SmsSendOutcome(sent=False, reason="Prospect introuvable")
        country = SmsProspectingRules.country_of(prospect) if prospect is not None else DEFAULT_COUNTRY_CODE
        # The country guard and the legal window protect a saved prospect; a bare-number self-test stays free.
        if prospect is not None:
            country_refusal = SmsProspectingRules.country_refusal(prospect)
            if country_refusal:
                return SmsSendOutcome(sent=False, reason=country_refusal)
            window_refusal = self.legal_window_refusal(country)
            if window_refusal:
                self.log_window_block(user_id, prospect_id=prospect_id, detail=window_refusal)
                return SmsSendOutcome(sent=False, reason=window_refusal)

        to_e164 = PhoneNumberPlans.mobile_of_country(to_raw, country=country)
        if not to_e164:
            return SmsSendOutcome(sent=False, reason=self._invalid_mobile_reason(prospect))
        if self.is_suppressed(db, user_id, to_e164):
            return SmsSendOutcome(sent=False, reason="Numéro désinscrit (STOP)")
        reserved_characters = SmsOptOutMention.reserved_characters_for_number(to_e164)
        body = self.to_gsm7_body(text)
        body_refusal = self._segment_budget_refusal(
            body, reserved_characters=reserved_characters, maximum_segments=MARKETING_SMS_MAXIMUM_SEGMENTS
        )
        if body_refusal:
            return SmsSendOutcome(sent=False, reason=body_refusal)

        message = SmsMessage(
            user_id=user_id,
            prospect_id=prospect_id,
            recipient_name=recipient_name,
            to_e164=to_e164,
            sender=config.sender,
            body=body,
            status=SmsStatus.PENDING.value,
            segments=segment_count_with_reserve(body, reserved_characters),
            kind=SmsMessageKind.PROSPECTING.value,
        )
        outcome = await self._send_and_log(db, message=message, opt_out_mention=True)
        # A manual contact supersedes the campaigns: nothing automated may double it.
        if outcome.sent and prospect_id is not None:
            self._hold_back_campaign_sends(db, prospect_id, label="Contacté manuellement (SMS)")
            self._start_assistant_ttl_if_linked(db, user_id=user_id, prospect_id=prospect_id, body=body)
        return outcome

    async def send_service_message(
        self,
        db: Session,
        *,
        user_id: int,
        config: SmsConfig,
        to_e164: str,
        text: str,
        recipient_name: str,
    ) -> SmsSendOutcome:
        """Send a one-segment service SMS — an alert its recipient asked for, not marketing.

        No opt-out mention and no legal window (neither applies to a service message). The prospecting
        STOP list is not applied either: a STOP answered to a cold SMS must not silence the alerts a client
        pays for, nor the confirmation a visitor just asked for. Nothing is recorded against a prospect; the
        row is marked ``service``, so it stays out of the prospecting daily cap and recap, and only a failure
        raises a notification (an alert going out as planned is not news).

        Args:
            db: Active database session.
            user_id: Sender.
            config: The user's SMS config (sender).
            to_e164: Recipient number, already in E.164.
            text: Body, transliterated to GSM-7; refused beyond one segment.
            recipient_name: Recipient label in the SMS log.

        Returns:
            The send outcome (``sent`` + reason when skipped).
        """
        channel_refusal = self._channel_refusal(config)
        if channel_refusal:
            return SmsSendOutcome(sent=False, reason=channel_refusal)
        body = self.to_gsm7_body(text)
        body_refusal = self._segment_budget_refusal(
            body, reserved_characters=0, maximum_segments=SERVICE_SMS_MAXIMUM_SEGMENTS
        )
        if body_refusal:
            return SmsSendOutcome(sent=False, reason=body_refusal)
        message = SmsMessage(
            user_id=user_id,
            prospect_id=None,
            recipient_name=recipient_name,
            to_e164=to_e164,
            sender=config.sender,
            body=body,
            status=SmsStatus.PENDING.value,
            segments=segment_count_with_reserve(body, 0),
            kind=SmsMessageKind.SERVICE.value,
        )
        return await self._send_and_log(db, message=message, opt_out_mention=False)

    def _channel_refusal(self, config: SmsConfig) -> str | None:
        """
        Why no SMS can leave at all: no sender name (the channel's only switch), or no provider.

        Args:
            config: The user's SMS config.

        Returns:
            The refusal shown to the user, or ``None`` when the channel is ready.
        """
        if not config.sender:
            return "Renseignez un nom d'expéditeur dans Paramètres → Relance SMS"
        if not self._provider.is_configured:
            return "smsmode non configuré"
        return None

    @staticmethod
    def _owned_prospect(db: Session, user_id: int, prospect_id: int | None) -> ProspectDB | None:
        """The user's prospect *prospect_id*, ``None`` when there is none or it belongs to someone else.

        Args:
            db: Active database session.
            user_id: Owner.
            prospect_id: The prospect id sent by the dashboard, when there is one.

        Returns:
            The prospect row, or ``None``.
        """
        if prospect_id is None:
            return None
        return db.query(ProspectDB).filter(ProspectDB.id == prospect_id, ProspectDB.user_id == user_id).first()

    @staticmethod
    def _invalid_mobile_reason(prospect: ProspectDB | None) -> str:
        """The refusal for a typed number that is not a mobile we may text.

        Args:
            prospect: The saved prospect the number belongs to, ``None`` for a bare number.

        Returns:
            The French refusal, naming the prospect's country when there is one.
        """
        if prospect is None:
            return "Numéro invalide : un mobile français 06/07 est requis"
        label = CountryProfiles.get(SmsProspectingRules.country_of(prospect)).label
        return f"Numéro invalide : un mobile du pays du prospect ({label}) est requis"

    @staticmethod
    def _segment_budget_refusal(body: str, *, reserved_characters: int, maximum_segments: int) -> str | None:
        """
        Why a composed body cannot leave: empty, or long enough to be billed beyond its segment budget.

        Args:
            body: The final body, GSM-7 transliterated.
            reserved_characters: Characters the provider appends (the opt-out mention), counted in the budget.
            maximum_segments: Segments the body may bill at most.

        Returns:
            The refusal shown to the user, or ``None`` when the body fits.
        """
        segments = segment_count_with_reserve(body, reserved_characters)
        if segments == 0:
            return "Message vide"
        if segments > maximum_segments:
            limit = "1 seul" if maximum_segments == 1 else str(maximum_segments)
            return f"Message trop long : il partirait en {segments} SMS. Raccourcissez-le pour tenir en {limit}."
        return None

    @staticmethod
    def is_assistant_message(message: SmsMessage) -> bool:
        """
        Whether an SMS belongs to the receptionist module: a service message, or one linking its demo or video.

        Args:
            message: The SMS row.

        Returns:
            ``True`` for a receptionist SMS (its alerts, confirmations and reminders included).
        """
        return message.kind == SmsMessageKind.SERVICE.value or bool(_ASSISTANT_PAGE_LINK.search(message.body or ""))

    @classmethod
    def _start_assistant_ttl_if_linked(cls, db: Session, *, user_id: int, prospect_id: int, body: str) -> None:
        """Start the countdown of the prospect's active assistant when a sent SMS carries its link; never raises."""
        try:
            assistant = ai_assistant_service.get_active_for_prospect(db, prospect_id=prospect_id, user_id=user_id)
        except Exception:
            logger.warning("Failed to start assistant demo TTL after SMS to prospect %s", prospect_id, exc_info=True)
            return
        cls._start_assistant_ttl(db, assistant, body=body)

    @staticmethod
    def _start_assistant_ttl(db: Session, assistant: AiAssistant | None, *, body: str) -> None:
        """Start an assistant's demo countdown when a sent SMS carries its link (idempotent); never raises."""
        from services.ai_assistant.assistant_service import ai_assistant_service

        if assistant is None:
            return
        try:
            if ai_assistant_service.body_contains_assistant_link(assistant, body):
                ai_assistant_service.start_demo_ttl(db, assistant, datetime.now(UTC))
        except Exception:
            logger.warning(
                "Failed to start assistant demo TTL after SMS to prospect %s", assistant.prospect_id, exc_info=True
            )

    async def _send_and_log(self, db: Session, *, message: SmsMessage, opt_out_mention: bool) -> SmsSendOutcome:
        """Persist the row, hand it to the provider, record the outcome and its cost, notify.

        A service message only notifies on failure: an alert going out as planned is not news.

        Args:
            db: Active database session.
            message: A ready-to-send SMS row (recipient, sender, body set).
            opt_out_mention: Whether the provider appends its opt-out mention (every marketing SMS).

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
            opt_out_mention=opt_out_mention,
            # smsmode requires refClient to be 3–140 chars, so a bare id ("1") is rejected.
            ref_client=f"dlh-{message.id}",
            callback_url=callback_url,
            callback_url_mo=callback_url_mo,
        )
        if result.success:
            message.status = SmsStatus.SENT.value
            message.provider_message_id = result.provider_message_id
            message.segments = result.provider_segments or message.segments
            message.price_cents = (
                result.price_cents
                if result.price_cents is not None
                else SmsPricing.estimate_cents_for_number(message.segments, to_e164=message.to_e164)
            )
        else:
            message.status = SmsStatus.FAILED.value
            message.error = result.error
        db.commit()
        db.refresh(message)
        if result.success and message.prospect_id is not None:
            self._mark_prospect_contacted(db, message.prospect_id)
        if not result.success or message.kind != SmsMessageKind.SERVICE.value:
            await self._notify_send(db, message, success=result.success)
        return SmsSendOutcome(
            sent=result.success,
            reason=result.error,
            message=message,
            provider_text=result.provider_text,
            provider_segments=result.provider_segments,
        )

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
        """Raise the send/failure notification for a just-sent SMS, the cost of a sent one in its detail (best-effort).

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
            detail=self._segments_and_cost_label(message) if success else None,
            is_assistant_module=self.is_assistant_message(message),
        )

    @staticmethod
    def _segments_and_cost_label(message: SmsMessage) -> str:
        """The segments and cost of a sent SMS, as the activity feed shows them (« 2 SMS · ≈ 13 c »).

        Args:
            message: The sent SMS row, its price set.

        Returns:
            The one-line cost detail.
        """
        segments_label = "1 SMS" if message.segments == 1 else f"{message.segments} SMS"
        if message.price_cents is None:
            return segments_label
        return f"{segments_label} · ≈ {SmsPricing.french_amount_label(message.price_cents)}"

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
            from_raw: Number the prospect wrote from: national form of his country, or international.
            body: Message text as received.
            received_at: When the reply arrived (defaults to now, UTC).

        Returns:
            The persisted reply row.

        Raises:
            ValueError: On an unparseable number, an empty body, or an unknown prospect.
        """
        prospect = self._owned_prospect(db, user_id, prospect_id)
        if prospect_id is not None and prospect is None:
            raise ValueError("Prospect introuvable")
        country = SmsProspectingRules.country_of(prospect) if prospect is not None else DEFAULT_COUNTRY_CODE
        from_e164 = self._reply_number_to_e164(from_raw, country=country)
        if not from_e164:
            if country == DEFAULT_COUNTRY_CODE:
                raise ValueError("Numéro invalide : un numéro français est requis")
            raise ValueError(
                "Numéro invalide : un mobile du pays du prospect ou un numéro international (+…) est requis"
            )
        text = (body or "").strip()
        if not text:
            raise ValueError("Message vide")
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

    @staticmethod
    def _reply_number_to_e164(from_raw: str, *, country: str) -> str | None:
        """E.164 of the number a reply came from, read in the prospect's country.

        A French prospect's number may be any French number; another prospect's must be a mobile of his
        country, or a number typed in international form (``+…`` or ``00…``), never a French reading of it.

        Args:
            from_raw: The number as typed by the operator.
            country: ISO code of the prospect's country, France for a bare number.

        Returns:
            The number as ``+…``, or ``None`` when it does not parse.
        """
        if country == DEFAULT_COUNTRY_CODE:
            return to_e164_fr(from_raw)
        typed = (from_raw or "").strip()
        international = PhoneNumberPlans.international_to_e164(typed) if typed.startswith(("+", "00")) else None
        return PhoneNumberPlans.mobile_of_country(typed, country=country) or international

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
