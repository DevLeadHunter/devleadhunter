"""Per-user « Relances SMS J+30 » system campaign.

A real campaign row (channel ``sms``) the product manages itself: the planner drops
every planned J+30 relance into it, so the operator gets the full campaign view —
prospect list, rendered SMS content, live queue — that updates on its own and never
completes. Its status mirrors the « Relance SMS automatique » toggle, and its
``sms_template_key`` is kept in sync with the Paramètres relance template.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.campaign import Campaign, CampaignStatus, campaign_prospects

SMS_AUTO_RELANCE_KIND = "sms_auto_relance"

_CAMPAIGN_NAME = "Relances SMS J+30"


class SmsAutoCampaignService:
    """Create, feed and keep in sync the per-user J+30 relance system campaign."""

    def get(self, db: Session, user_id: int) -> Campaign | None:
        """The user's J+30 system campaign, or ``None`` when never created.

        Args:
            db: Active database session.
            user_id: Owner.

        Returns:
            The system campaign row, or ``None``.
        """
        return (
            db.query(Campaign)
            .filter(Campaign.user_id == user_id, Campaign.system_kind == SMS_AUTO_RELANCE_KIND)
            .first()
        )

    def ensure(self, db: Session, user_id: int, *, enabled: bool, template_key: str | None) -> Campaign:
        """Get or create the user's J+30 system campaign, aligned on the automation state.

        Args:
            db: Active database session.
            user_id: Owner.
            enabled: Whether the auto-relance toggle is on (drives the campaign status).
            template_key: The relance template configured in Paramètres.

        Returns:
            The system campaign row.
        """
        campaign = self.get(db, user_id)
        if campaign is None:
            campaign = Campaign(
                user_id=user_id,
                name=_CAMPAIGN_NAME,
                channel="sms",
                status=CampaignStatus.ACTIVE.value if enabled else CampaignStatus.PAUSED.value,
                system_kind=SMS_AUTO_RELANCE_KIND,
                sms_template_key=template_key,
            )
            db.add(campaign)
            db.commit()
            db.refresh(campaign)
        return campaign

    def attach_prospect(self, db: Session, campaign: Campaign, prospect_id: int) -> None:
        """Add a prospect to the system campaign (append position), once — no commit.

        Args:
            db: Active database session.
            campaign: The system campaign.
            prospect_id: The prospect being planned.
        """
        already_member = db.execute(
            campaign_prospects.select().where(
                campaign_prospects.c.campaign_id == campaign.id,
                campaign_prospects.c.prospect_id == prospect_id,
            )
        ).first()
        if already_member:
            return
        max_position = (
            db.query(func.max(campaign_prospects.c.position))
            .filter(campaign_prospects.c.campaign_id == campaign.id)
            .scalar()
        )
        next_position = (max_position + 1) if max_position is not None else 0
        db.execute(
            campaign_prospects.insert().values(campaign_id=campaign.id, prospect_id=prospect_id, position=next_position)
        )

    def sync_automation(self, db: Session, user_id: int, *, enabled: bool, template_key: str | None) -> None:
        """Mirror the Paramètres automation state onto the system campaign, when it exists.

        Args:
            db: Active database session.
            user_id: Owner.
            enabled: Whether the auto-relance toggle is on.
            template_key: The relance template configured in Paramètres.
        """
        campaign = self.get(db, user_id)
        if campaign is None:
            return
        campaign.status = CampaignStatus.ACTIVE.value if enabled else CampaignStatus.PAUSED.value
        if template_key:
            campaign.sms_template_key = template_key
        db.commit()


sms_auto_campaign_service = SmsAutoCampaignService()
