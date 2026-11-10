"""
The offers of the installed product modules, as the campaign engine applies them.

The websites module (the demo site and its video) stays the engine's own. Every other module brings a
:class:`CampaignOffer`; this class turns those offers into the engine's questions: which module a template sells,
whether it may leave for a prospect, and what the module variables render to. A module switched off sells nothing:
any template using one of its variables is held back.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from core.product_modules.campaign_offer import CampaignOffer, OfferLifetime, PreviewThumbnail
from core.product_modules.contract import ProductModule
from core.product_modules.registry import product_module_registry
from models.email_template import EmailTemplate
from models.prospect_db import ProspectDB
from models.sms_message import SmsMessage
from services.product_module_service import product_module_service

if TYPE_CHECKING:
    from services.sms.templates import SmsTemplate

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OfferRefusal:
    """
    Why a message may not leave for a prospect, on account of a module's offer.

    Attributes:
        offer: The offer that refuses.
        reason: The skip reason stored on the queue row.
        is_missing_video: True when only the offer's video is missing (counted with the missing videos at launch).
    """

    offer: CampaignOffer
    reason: str
    is_missing_video: bool = False


class CampaignOffers:
    """Static entry point of the campaign engine into the modules' offers, in the order of the module keys."""

    @staticmethod
    def installed() -> list[CampaignOffer]:
        """
        The offers of every installed module, switched on or off (a switched-off offer still guards its variables).

        Returns:
            The offers, in the order of the module keys.
        """
        offers: list[CampaignOffer] = []
        for module in product_module_registry.installed():
            offer: CampaignOffer | None = module.campaign_offer()
            if offer is not None:
                offers.append(offer)
        return offers

    @staticmethod
    def module_label(offer: CampaignOffer) -> str:
        """
        The name the operator knows the offer's module by.

        Args:
            offer: An installed offer.

        Returns:
            The module label (« Réceptionniste IA »), or its key when the module is gone.
        """
        module: ProductModule | None = product_module_registry.get(offer.module_key)
        return module.label if module is not None else offer.module_key

    @classmethod
    def disabled_module_reason(cls, offer: CampaignOffer) -> str:
        """
        The skip reason of a message held back because its module is switched off.

        Args:
            offer: The offer of the switched-off module.

        Returns:
            The French reason shown on the campaign page.
        """
        return f"Module « {cls.module_label(offer)} » désactivé"

    @classmethod
    def email_link_variables(cls) -> tuple[str, ...]:
        """
        Every email variable that links a module's demo (the receptionist, the loyalty card…).

        Returns:
            The variable names, in module order.
        """
        return tuple(name for offer in cls.installed() for name in offer.email_link_variables)

    @classmethod
    def email_offer_of(cls, template: EmailTemplate | None) -> CampaignOffer | None:
        """
        The module offer an email template sells: the first whose variables it uses (price and wording included).

        Args:
            template: The template, or None.

        Returns:
            The offer, or None for a websites template.
        """
        return next((offer for offer in cls.installed() if cls._email_uses_offer(template, offer)), None)

    @classmethod
    def email_link_offer_of(cls, template: EmailTemplate | None) -> CampaignOffer | None:
        """
        The module offer whose demo an email template links (its link, video or thumbnail).

        Args:
            template: The template, or None.

        Returns:
            The offer, or None when the template links no module demo.
        """
        return next((offer for offer in cls.installed() if cls.email_uses(template, offer.email_link_variables)), None)

    @classmethod
    def sms_offer_of(cls, sms_template: SmsTemplate | None) -> CampaignOffer | None:
        """
        The module offer an SMS template sells: the first whose variables it uses.

        Args:
            sms_template: The SMS template, or None when its key is unknown.

        Returns:
            The offer, or None for a websites SMS.
        """
        return next((offer for offer in cls.installed() if cls._sms_uses_offer(sms_template, offer)), None)

    @classmethod
    def sms_link_offer_of(cls, sms_template: SmsTemplate | None) -> CampaignOffer | None:
        """
        The module offer whose demo an SMS template links.

        Args:
            sms_template: The SMS template, or None.

        Returns:
            The offer, or None when the SMS links no module demo.
        """
        return next((offer for offer in cls.installed() if cls.sms_uses(sms_template, offer.sms_link_variables)), None)

    @classmethod
    def email_send_refusal(
        cls, db: Session, template: EmailTemplate | None, *, prospect_id: int, user_id: int, include_video: bool
    ) -> OfferRefusal | None:
        """
        Why an email template may not leave for a prospect, on account of the module offers it uses.

        For each offer the template uses, in order: its module must be switched on; a template linking the offer
        needs the prospect's demo of it; a template whose only door is the offer's video needs that video, with the
        campaign's video switch on.

        Args:
            db: Active database session.
            template: The template to send.
            prospect_id: The recipient prospect.
            user_id: The sending user.
            include_video: The campaign's video switch.

        Returns:
            The first refusal, or None when no offer holds the email back.
        """
        for offer in cls.installed():
            if not cls._email_uses_offer(template, offer):
                continue
            if not product_module_service.is_enabled(db, offer.module_key):
                return OfferRefusal(offer=offer, reason=cls.disabled_module_reason(offer))
            if cls.email_uses(template, offer.email_link_variables) and not offer.has_active_offer(
                db, prospect_id=prospect_id, user_id=user_id
            ):
                return OfferRefusal(offer=offer, reason=offer.missing_offer_skip_reason)
            if cls._is_video_only(template, offer) and not (
                include_video and offer.has_ready_video(db, prospect_id=prospect_id, user_id=user_id)
            ):
                return OfferRefusal(offer=offer, reason=offer.missing_video_skip_reason, is_missing_video=True)
        return None

    @classmethod
    def sms_send_refusal(
        cls, db: Session, sms_template: SmsTemplate | None, *, prospect_id: int, user_id: int
    ) -> OfferRefusal | None:
        """
        Why an SMS may not leave for a prospect, on account of the module offers it uses.

        Args:
            db: Active database session.
            sms_template: The SMS template to send.
            prospect_id: The recipient prospect.
            user_id: The sending user.

        Returns:
            The first refusal (module off, or no demo of an offer it links), or None.
        """
        for offer in cls.installed():
            if not cls._sms_uses_offer(sms_template, offer):
                continue
            if not product_module_service.is_enabled(db, offer.module_key):
                return OfferRefusal(offer=offer, reason=cls.disabled_module_reason(offer))
            if cls.sms_uses(sms_template, offer.sms_link_variables) and not offer.has_active_offer(
                db, prospect_id=prospect_id, user_id=user_id
            ):
                return OfferRefusal(offer=offer, reason=offer.missing_offer_skip_reason)
        return None

    @classmethod
    def sms_enqueue_refusal(
        cls, db: Session, sms_template: SmsTemplate | None, *, prospect_id: int, user_id: int
    ) -> OfferRefusal | None:
        """
        Why a prospect may not join a module's SMS campaign: an SMS selling an offer needs the prospect's demo of it.

        Unlike a send, an SMS campaign is decided by what it sells: a receptionist SMS without its link still needs
        the prospect's receptionist.

        Args:
            db: Active database session.
            sms_template: The campaign's first-contact SMS template.
            prospect_id: The prospect.
            user_id: The campaign owner.

        Returns:
            The first refusal, or None.
        """
        for offer in cls.installed():
            if not cls._sms_uses_offer(sms_template, offer):
                continue
            if not product_module_service.is_enabled(db, offer.module_key):
                return OfferRefusal(offer=offer, reason=cls.disabled_module_reason(offer))
            if not offer.has_active_offer(db, prospect_id=prospect_id, user_id=user_id):
                return OfferRefusal(offer=offer, reason=offer.missing_offer_skip_reason)
        return None

    @classmethod
    def sms_missing_video_refusal(
        cls, db: Session, sms_template: SmsTemplate, *, prospect_id: int, user_id: int
    ) -> OfferRefusal | None:
        """
        The module video an SMS links and the prospect does not have yet (it then falls back to its sibling).

        Args:
            db: Active database session.
            sms_template: The SMS template picked.
            prospect_id: The prospect.
            user_id: The sending user.

        Returns:
            The refusal of the first offer whose video is missing, or None.
        """
        for offer in cls.installed():
            if cls.sms_uses(sms_template, offer.sms_video_variables) and not offer.has_ready_video(
                db, prospect_id=prospect_id, user_id=user_id
            ):
                return OfferRefusal(offer=offer, reason=offer.missing_video_skip_reason, is_missing_video=True)
        return None

    @classmethod
    def notification_tag_of(cls, module_key: str | None) -> str:
        """
        The push prefix of a module, so a phone tells the modules apart.

        Args:
            module_key: The module, or None for the websites module.

        Returns:
            The module's tag (« 🤖 Assistant IA »), or "" for the websites module or a module without one.
        """
        if module_key is None:
            return ""
        module: ProductModule | None = product_module_registry.get(module_key)
        return module.notification_tag if module is not None else ""

    @classmethod
    def offer_lifetime(cls, db: Session, offer: CampaignOffer, *, prospect_id: int, user_id: int) -> OfferLifetime:
        """
        How long a prospect's demo of an offer stays online; a switched-off module's demo is gone.

        Args:
            db: Active database session.
            offer: The offer a follow-up links.
            prospect_id: The prospect.
            user_id: The campaign owner.

        Returns:
            The lifetime.
        """
        if not product_module_service.is_enabled(db, offer.module_key):
            return OfferLifetime(has_offer=False, expires_at=None)
        return offer.offer_lifetime(db, prospect_id=prospect_id, user_id=user_id)

    @classmethod
    def email_variables(
        cls, db: Session, prospect: ProspectDB, *, user_id: int, include_video: bool, variant: str | None
    ) -> dict[str, str]:
        """
        The module variables of a prospect's email; a switched-off module's variables render empty.

        Args:
            db: Active database session.
            prospect: The prospect being emailed.
            user_id: The sending user.
            include_video: The campaign's video switch.
            variant: The send's A/B variant.

        Returns:
            The value of every module variable.
        """
        values: dict[str, str] = {}
        for offer in cls.installed():
            if product_module_service.is_enabled(db, offer.module_key):
                values.update(
                    offer.email_variables(db, prospect, user_id=user_id, include_video=include_video, variant=variant)
                )
            else:
                values.update(dict.fromkeys(offer.email_offer_variables, ""))
        return values

    @classmethod
    def expiry_date_without_demo_link(cls, db: Session, prospect: ProspectDB, *, user_id: int) -> str:
        """
        ``{date_expiration}`` of an email without a demo site link: the date of the first module demo it can find.

        Args:
            db: Active database session.
            prospect: The prospect being emailed.
            user_id: The sending user.

        Returns:
            The French date, or "" when the prospect has no module demo either.
        """
        for offer in cls.installed():
            if not product_module_service.is_enabled(db, offer.module_key):
                continue
            expiry_date: str | None = offer.expiry_date_without_demo_link(db, prospect, user_id=user_id)
            if expiry_date is not None:
                return expiry_date
        return ""

    @classmethod
    def sms_variables(cls, db: Session, prospect: ProspectDB, *, user_id: int) -> dict[str, str]:
        """
        The module variables of a prospect's SMS; a switched-off module's variables render empty.

        Args:
            db: Active database session.
            prospect: The prospect being texted.
            user_id: The sending user.

        Returns:
            The value of every module variable.
        """
        values: dict[str, str] = {}
        for offer in cls.installed():
            if product_module_service.is_enabled(db, offer.module_key):
                values.update(offer.sms_variables(db, prospect, user_id=user_id))
            else:
                values.update(dict.fromkeys(offer.sms_offer_variables, ""))
        return values

    @classmethod
    def record_message_sent(cls, db: Session, *, prospect_id: int, user_id: int, sent_at: datetime, body: str) -> None:
        """
        Tell every switched-on module an outreach email or SMS left (it starts the countdown of the demo it links).

        Never raises: a module failing here must not turn a sent message into a failed one.

        Args:
            db: Active database session.
            prospect_id: The recipient prospect.
            user_id: The sending user.
            sent_at: When it left (naive UTC).
            body: The rendered body.
        """
        for offer in cls.installed():
            try:
                if product_module_service.is_enabled(db, offer.module_key):
                    offer.record_message_sent(db, prospect_id=prospect_id, user_id=user_id, sent_at=sent_at, body=body)
            except Exception:
                logger.warning(
                    "[CampaignOffers] %s could not record the message sent to prospect %s",
                    offer.module_key,
                    prospect_id,
                    exc_info=True,
                )

    @classmethod
    def sms_templates(cls) -> list[SmsTemplate]:
        """
        The SMS templates the installed modules add to the library.

        Returns:
            The templates, module after module.
        """
        return [template for offer in cls.installed() for template in offer.sms_templates()]

    @classmethod
    def module_key_of_sms(cls, message: SmsMessage) -> str | None:
        """
        The module a logged SMS belongs to.

        Args:
            message: A logged SMS.

        Returns:
            The module key, or None for a websites SMS.
        """
        return next((offer.module_key for offer in cls.installed() if offer.owns_sms_message(message)), None)

    @classmethod
    def preview_link_variables(cls) -> tuple[str, ...]:
        """
        The module link variables a template preview renders as anchors.

        Returns:
            The variable names.
        """
        return tuple(name for offer in cls.installed() for name in offer.preview_link_variables)

    @classmethod
    def preview_thumbnails(cls) -> tuple[PreviewThumbnail, ...]:
        """
        The module video thumbnails of a template preview.

        Returns:
            One entry per thumbnail variable.
        """
        return tuple(thumbnail for offer in cls.installed() for thumbnail in offer.preview_thumbnails)

    @staticmethod
    def email_uses(template: EmailTemplate | None, variables: tuple[str, ...]) -> bool:
        """
        Whether an email template's subject or body references any of these variables.

        Args:
            template: The template, or None.
            variables: Variable names, without braces.

        Returns:
            True on the first one found.
        """
        if template is None or not variables:
            return False
        haystack: str = f"{template.subject or ''} {template.body_html or ''}"
        return any(f"{{{name}}}" in haystack for name in variables)

    @staticmethod
    def sms_uses(sms_template: SmsTemplate | None, variables: tuple[str, ...]) -> bool:
        """
        Whether an SMS template references any of these variables.

        Args:
            sms_template: The template, or None.
            variables: Variable names, without braces.

        Returns:
            True on the first one found.
        """
        return sms_template is not None and any(sms_template.uses(name) for name in variables)

    @classmethod
    def _email_uses_offer(cls, template: EmailTemplate | None, offer: CampaignOffer) -> bool:
        return cls.email_uses(template, (*offer.email_link_variables, *offer.email_offer_variables))

    @classmethod
    def _sms_uses_offer(cls, sms_template: SmsTemplate | None, offer: CampaignOffer) -> bool:
        return cls.sms_uses(sms_template, (*offer.sms_link_variables, *offer.sms_offer_variables))

    @classmethod
    def _is_video_only(cls, template: EmailTemplate | None, offer: CampaignOffer) -> bool:
        if not cls.email_uses(template, offer.email_video_variables):
            return False
        primary: str | None = offer.email_primary_link_variable
        return primary is None or not cls.email_uses(template, (primary,))
