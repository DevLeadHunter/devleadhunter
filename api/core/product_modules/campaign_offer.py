"""
What a product module sells through the campaigns.

The core sends the campaigns; a module only says which template variables point at its demo (the receptionist's
``{lien_assistant}``, the loyalty card's ``{lien_carte}``), whether a prospect has that demo, and what the variables
render to. The core then applies the same guards to every module: a template that links a demo the prospect lacks
is never sent, and a module switched off sells nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from models.prospect_db import ProspectDB
    from models.sms_message import SmsMessage
    from services.sms.templates import SmsTemplate


@dataclass(frozen=True)
class OfferLifetime:
    """
    How long the demo a follow-up links stays online.

    Attributes:
        has_offer: Whether the prospect has the demo at all.
        expires_at: When it goes offline (naive UTC); None with ``has_offer`` means its countdown has not started,
            so it is alive for any follow-up.
    """

    has_offer: bool
    expires_at: datetime | None


@dataclass(frozen=True)
class PreviewThumbnail:
    """A video thumbnail variable of the template preview, with the link it opens and what the image shows."""

    thumbnail_variable: str
    link_variable: str
    alt_text: str


class CampaignOffer:
    """
    One module's offer, as the campaign engine sees it.

    The variable names of a module are its own; the core never names them.

    Attributes:
        module_key: The module of :class:`core.product_modules.contract.ProductModule`, under which the cross-module
            contact lock is stored.
        is_sellable: False while the module cannot link a demo for any prospect: its templates are refused outright,
            with ``missing_offer_skip_reason``.
        offer_label: How the logs name the offer (« AI assistant »).
        expired_offer_skip_reason: Why a follow-up stops once the offer expired.
        email_link_variables: The email variables that render only when the prospect has the offer (its link, its
            video, its thumbnail).
        email_video_variables: The offer's video variables: a template using them without
            ``email_primary_link_variable`` is video-only.
        email_primary_link_variable: The variable of the offer's demo link.
        email_offer_variables: Every email variable of the offer, price and wording included: any of them makes a
            template this module's offer.
        sms_link_variables: The SMS variables that render only when the prospect has the offer.
        sms_video_variables: The offer's SMS video variables: a template using one falls back to its sibling while the
            video is missing.
        sms_offer_variables: Every SMS variable of the offer.
        preview_link_variables: The link variables the template preview renders as anchors.
        preview_thumbnails: The offer's video thumbnails in the template preview.
        email_price_variables: The offer's prices, which the dressed email layouts set in ink and put in their offer
            table.
        missing_offer_skip_reason: Why a send stops when the prospect lacks the offer.
        missing_video_skip_reason: Why a video-only template's send stops when the offer's video is missing.
        missing_offer_launch_summary: The end of the launch summary, « N prospect(s) ignoré(s) <this> ».
    """

    module_key: ClassVar[str]
    is_sellable: ClassVar[bool] = True
    offer_label: ClassVar[str]
    expired_offer_skip_reason: ClassVar[str]

    email_link_variables: ClassVar[tuple[str, ...]] = ()
    email_video_variables: ClassVar[tuple[str, ...]] = ()
    email_primary_link_variable: ClassVar[str | None] = None
    email_offer_variables: ClassVar[tuple[str, ...]] = ()
    sms_link_variables: ClassVar[tuple[str, ...]] = ()
    sms_video_variables: ClassVar[tuple[str, ...]] = ()
    sms_offer_variables: ClassVar[tuple[str, ...]] = ()
    preview_link_variables: ClassVar[tuple[str, ...]] = ()
    preview_thumbnails: ClassVar[tuple[PreviewThumbnail, ...]] = ()
    email_price_variables: ClassVar[tuple[str, ...]] = ()

    missing_offer_skip_reason: ClassVar[str]
    missing_video_skip_reason: ClassVar[str] = ""
    missing_offer_launch_summary: ClassVar[str]

    def has_active_offer(self, db: Session, *, prospect_id: int, user_id: int) -> bool:
        """
        Whether the prospect has this offer's demo, from this user, ready to be linked.

        Args:
            db: Active database session.
            prospect_id: The prospect.
            user_id: The sending user.

        Returns:
            True when a send may link it.
        """
        return False

    def has_ready_video(self, db: Session, *, prospect_id: int, user_id: int) -> bool:
        """
        Whether the offer's prospection video for this prospect is ready.

        Args:
            db: Active database session.
            prospect_id: The prospect.
            user_id: The sending user.

        Returns:
            True when a video-only template has something to show.
        """
        return False

    def offer_lifetime(self, db: Session, *, prospect_id: int, user_id: int) -> OfferLifetime:
        """
        How long the prospect's demo of this offer stays online, for the follow-ups that link it.

        Args:
            db: Active database session.
            prospect_id: The prospect.
            user_id: The sending user.

        Returns:
            The lifetime; the default says the prospect has no demo, so a follow-up linking it is refused.
        """
        return OfferLifetime(has_offer=False, expires_at=None)

    def email_variables(
        self, db: Session, prospect: ProspectDB, *, user_id: int, include_video: bool, variant: str | None
    ) -> dict[str, str]:
        """
        The values of the offer's email variables for one prospect.

        Args:
            db: Active database session.
            prospect: The prospect being emailed.
            user_id: The sending user.
            include_video: The campaign's video switch.
            variant: The send's A/B variant, to stamp on the offer's links.

        Returns:
            The value of each of ``email_offer_variables`` (empty strings without an offer).
        """
        return {}

    def expiry_date_without_demo_link(self, db: Session, prospect: ProspectDB, *, user_id: int) -> str | None:
        """
        ``{date_expiration}`` of an email that links this offer and no demo site.

        Args:
            db: Active database session.
            prospect: The prospect being emailed.
            user_id: The sending user.

        Returns:
            The French date (« 12 octobre »), or None when the prospect has no demo of this offer.
        """
        return None

    def email_button_labels(self, variables: dict[str, str]) -> dict[str, str]:
        """
        The wording of the button the dressed email layouts draw under each of the offer's links.

        Args:
            variables: The rendered variables of the send (a wording may name the receptionist).

        Returns:
            The button wording by link variable; an empty wording draws no button (a video thumbnail is its own).
        """
        return {}

    def sms_variables(self, db: Session, prospect: ProspectDB, *, user_id: int) -> dict[str, str]:
        """
        The values of the offer's SMS variables for one prospect.

        Args:
            db: Active database session.
            prospect: The prospect being texted.
            user_id: The sending user.

        Returns:
            The value of each of ``sms_offer_variables``.
        """
        return {}

    def record_message_sent(self, db: Session, *, prospect_id: int, user_id: int, sent_at: datetime, body: str) -> None:
        """
        React to an outreach email or SMS that left with this body (start the demo's countdown when it links it).

        Args:
            db: Active database session.
            prospect_id: The recipient prospect.
            user_id: The sending user.
            sent_at: When it left (naive UTC).
            body: The rendered body (HTML for an email).
        """

    def sms_templates(self) -> list[SmsTemplate]:
        """
        The SMS templates of the offer, added to the core's library.

        Returns:
            The templates, in display order.
        """
        return []

    def owns_sms_message(self, message: SmsMessage) -> bool:
        """
        Whether a sent SMS belongs to this module (its links, its service messages), for the SMS log and the pushes.

        Args:
            message: A logged SMS.

        Returns:
            True when the SMS is this module's.
        """
        return False
