"""Launching a campaign: the checks, the activation and the first sends put in the queue.

The « Lancer » button and a scheduled launch both go through here, so a campaign the launch
loop starts gets the same refusals and the same queue as one started by hand.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from models.campaign import Campaign, CampaignStatus
from models.resend_config import ResendConfig
from services.campaign_offers import CampaignOffers
from services.campaign_queue_service import CampaignQueueService, EnqueueResult
from services.product_module_service import product_module_service
from services.sms_config_service import sms_config_service

_SMS_CHANNEL: str = "sms"


class CampaignLaunchRefusal(ValueError):
    """A launch the campaign's setup cannot carry out (message shown to the user as is)."""


@dataclass(frozen=True)
class CampaignLaunchOverrides:
    """What a manual launch may set on an email campaign as it starts; a scheduled launch sets nothing."""

    template_id: int | None = None
    ab_template_id_b: int | None = None
    follow_up_template_id: int | None = None
    follow_up_delay_days: int = 5
    send_delay_minutes: int | None = None


@dataclass(frozen=True)
class CampaignLaunchOutcome:
    """What a launch put in the send queue, and the sentence that sums it up."""

    enqueue_result: EnqueueResult
    message: str


class CampaignLaunchService:
    """Checks that a campaign can start, then starts it: the single path of every launch."""

    @staticmethod
    def has_resend_config(db: Session, user_id: int) -> bool:
        """Whether the user has a Resend API key, the sender of every email campaign."""
        config: ResendConfig | None = db.execute(
            select(ResendConfig).where(ResendConfig.user_id == user_id)
        ).scalar_one_or_none()
        return config is not None and bool(config.api_key)

    def refusal(self, db: Session, campaign: Campaign, overrides: CampaignLaunchOverrides | None = None) -> str | None:
        """
        Why the campaign cannot be launched as it is set up.

        Args:
            db: Active database session.
            campaign: The campaign to launch.
            overrides: What a manual launch sets as it starts, when any.

        Returns:
            The reason shown to the user, or ``None`` when the campaign can start.
        """
        if campaign.channel == _SMS_CHANNEL:
            sms_config = sms_config_service.get(db, campaign.user_id)
            if sms_config is None or not sms_config.sender:
                return "Expéditeur SMS manquant — Paramètres → Relance SMS"
            return None
        if not self.has_resend_config(db, campaign.user_id):
            return "Configuration Resend manquante — Paramètres → Configuration Resend"
        chosen_template_id: int | None = (overrides.template_id if overrides else None) or campaign.template_id
        if not chosen_template_id:
            return "template_id requis — sélectionnez un template J1"
        return None

    def launch(
        self, db: Session, campaign: Campaign, overrides: CampaignLaunchOverrides | None = None
    ) -> CampaignLaunchOutcome:
        """
        Activate the campaign and put its first sends on the next slots of the send policy.

        The guards of the queue (unsubscribed, « ne plus contacter », missing demo…) decide who
        is left out, exactly as for any enqueue.

        Args:
            db: Active database session.
            campaign: The campaign to launch.
            overrides: What a manual launch sets as it starts, when any.

        Returns:
            What was put in the queue and the sentence that sums it up.

        Raises:
            CampaignLaunchRefusal: The sender or the first template is missing.
        """
        refusal: str | None = self.refusal(db, campaign, overrides)
        if refusal is not None:
            raise CampaignLaunchRefusal(refusal)
        if campaign.channel == _SMS_CHANNEL:
            return self._launch_sms(db, campaign)
        return self._launch_email(db, campaign, overrides or CampaignLaunchOverrides())

    def _launch_sms(self, db: Session, campaign: Campaign) -> CampaignLaunchOutcome:
        """Activate an SMS campaign and queue its first SMS."""
        self._activate(db, campaign)
        result: EnqueueResult = CampaignQueueService(db).enqueue_campaign(campaign)
        message: str = f"{result.enqueued} SMS mis en file"
        if result.skipped_no_demo:
            message += f" · {len(result.skipped_no_demo)} prospect(s) ignoré(s) faute de site de démo"
        message += self._offer_skip_message(db, result)
        if result.skipped_locked:
            message += f" · {len(result.skipped_locked)} prospect(s) réservé(s) par un autre module"
        return CampaignLaunchOutcome(enqueue_result=result, message=message)

    def _launch_email(
        self, db: Session, campaign: Campaign, overrides: CampaignLaunchOverrides
    ) -> CampaignLaunchOutcome:
        """Save what the launch sets on an email campaign, activate it and queue its first emails."""
        template_id: int | None = overrides.template_id or campaign.template_id
        ab_template_id_b: int | None = overrides.ab_template_id_b or campaign.ab_template_id_b

        campaign.template_id = template_id
        if ab_template_id_b:
            campaign.ab_template_id_b = ab_template_id_b
        if overrides.send_delay_minutes is not None:
            campaign.send_delay_minutes = overrides.send_delay_minutes
        if overrides.follow_up_template_id:
            campaign.follow_up_template_id = overrides.follow_up_template_id
            campaign.follow_up_delay_days = overrides.follow_up_delay_days
        self._activate(db, campaign)

        result: EnqueueResult = CampaignQueueService(db).enqueue_campaign(
            campaign,
            template_id=template_id,
            ab_template_id_b=ab_template_id_b,
        )

        ab_info: str = " (A/B 50/50)" if ab_template_id_b else ""
        message: str = (
            f"{result.enqueued} email(s) mis en file{ab_info} — 1 toutes les {campaign.send_delay_minutes} min"
        )
        if result.skipped_no_demo:
            message += f" · {len(result.skipped_no_demo)} prospect(s) ignoré(s) faute de site de démo"
        if result.skipped_no_video:
            message += f" · {len(result.skipped_no_video)} prospect(s) ignoré(s) faute de vidéo de prospection"
        message += self._offer_skip_message(db, result)
        if result.skipped_locked:
            message += f" · {len(result.skipped_locked)} prospect(s) réservé(s) par un autre module"
        return CampaignLaunchOutcome(enqueue_result=result, message=message)

    @staticmethod
    def _activate(db: Session, campaign: Campaign) -> None:
        """Mark the campaign running from now on."""
        # The enum member, not its value: SQLite stores the string as given and cannot read « active » back.
        campaign.status = CampaignStatus.ACTIVE
        campaign.started_at = naive_utc_now()
        db.commit()

    @staticmethod
    def _offer_skip_message(db: Session, result: EnqueueResult) -> str:
        """The end of the launch message for the prospects the product modules' offers left out."""
        offers = {offer.module_key: offer for offer in CampaignOffers.installed()}
        message: str = ""
        for module_key, entries in result.skipped_without_offer.items():
            offer = offers.get(module_key)
            if offer is not None and product_module_service.is_enabled(db, module_key):
                reason: str = offer.missing_offer_launch_summary
            else:
                label: str = CampaignOffers.module_label(offer) if offer is not None else module_key
                reason = f"car le module « {label} » est désactivé"
            message += f" · {len(entries)} prospect(s) ignoré(s) {reason}"
        return message


campaign_launch_service = CampaignLaunchService()
