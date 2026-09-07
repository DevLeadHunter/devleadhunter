"""
Campaign service for managing email campaigns.
"""

from fastapi import HTTPException, status
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session, joinedload

from models.campaign import Campaign, CampaignStatus, campaign_prospects
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from schemas.campaign import (
    CampaignCreate,
    CampaignStats,
    CampaignUpdate,
    CampaignVariantStats,
)
from services.activity_log_service import CATEGORY_CAMPAIGN, STATUS_INFO, activity_log_service
from services.email_log_stats import aggregate_email_log_counts, compute_engagement_rates

# Campaign status → French verb for the activity feed.
_CAMPAIGN_STATUS_VERBS: dict[str, str] = {
    CampaignStatus.ACTIVE.value: "activée",
    CampaignStatus.PAUSED.value: "mise en pause",
    CampaignStatus.COMPLETED.value: "terminée",
    CampaignStatus.CANCELLED.value: "annulée",
    CampaignStatus.DRAFT.value: "repassée en brouillon",
}


def _is_active(campaign: Campaign) -> bool:
    """Return True when the campaign is running (SQLEnum may load a member, so compare on the value)."""
    return getattr(campaign.status, "value", campaign.status) == CampaignStatus.ACTIVE.value


class CampaignService:
    """Service for campaign management."""

    def create_campaign(self, db: Session, user_id: int, campaign_data: CampaignCreate) -> Campaign:
        """
        Create a new campaign.

        Args:
            db: Database session
            user_id: ID of the user creating the campaign
            campaign_data: Campaign creation data

        Returns:
            Created campaign
        """
        # Create campaign
        campaign = Campaign(
            user_id=user_id,
            name=campaign_data.name,
            description=campaign_data.description,
            status=campaign_data.status or CampaignStatus.DRAFT.value,
            channel=campaign_data.channel,
            sms_template_key=campaign_data.sms_template_key,
            template_id=campaign_data.template_id,
            ab_template_id_b=campaign_data.ab_template_id_b,
            send_delay_minutes=campaign_data.send_delay_minutes,
            max_emails_per_day=campaign_data.max_emails_per_day,
        )
        db.add(campaign)

        # Add prospects, preserving the request order as an explicit ``position`` so the send queue
        # dispatches them in that order (1 métier/jour with max_emails_per_day=1). Bulk inserts share
        # one ``added_at`` second, so only ``position`` gives a stable, operator-controlled order.
        if campaign_data.prospect_ids:
            owned: set[int] = {
                row[0]
                for row in db.query(ProspectDB.id)
                .filter(ProspectDB.id.in_(campaign_data.prospect_ids), ProspectDB.user_id == user_id)
                .all()
            }
            seen: set[int] = set()
            ordered_ids: list[int] = []
            for pid in campaign_data.prospect_ids:
                if pid in owned and pid not in seen:
                    seen.add(pid)
                    ordered_ids.append(pid)
            db.flush()  # assign campaign.id
            for position, pid in enumerate(ordered_ids):
                db.execute(
                    campaign_prospects.insert().values(campaign_id=campaign.id, prospect_id=pid, position=position)
                )

        db.commit()
        db.refresh(campaign)

        activity_log_service.record(
            category=CATEGORY_CAMPAIGN,
            action="campaign_created",
            status=STATUS_INFO,
            title=f"Campagne créée · {campaign.name}",
            user_id=user_id,
            entity_type="campaign",
            entity_id=campaign.id,
        )

        return campaign

    def get_campaign(self, db: Session, campaign_id: int, user_id: int) -> Campaign | None:
        """
        Get a campaign by ID.

        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user requesting the campaign

        Returns:
            Campaign if found and owned by user, None otherwise
        """
        campaign = (
            db.query(Campaign)
            .options(
                joinedload(Campaign.prospects),
                joinedload(Campaign.follow_ups),
            )
            .filter(Campaign.id == campaign_id, Campaign.user_id == user_id)
            .first()
        )

        return campaign

    def list_campaigns(
        self, db: Session, user_id: int, skip: int = 0, limit: int = 100, status: str | None = None
    ) -> tuple[list[Campaign], int]:
        """
        List campaigns for a user.

        Args:
            db: Database session
            user_id: ID of the user
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status (optional)

        Returns:
            Tuple of (campaigns list, total count)
        """
        query = db.query(Campaign).filter(Campaign.user_id == user_id)

        if status:
            query = query.filter(Campaign.status == status)

        total = query.count()
        campaigns = query.order_by(Campaign.created_at.desc()).offset(skip).limit(limit).all()

        return campaigns, total

    def update_campaign(
        self, db: Session, campaign_id: int, user_id: int, campaign_data: CampaignUpdate
    ) -> Campaign | None:
        """
        Update a campaign.

        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user updating the campaign
            campaign_data: Campaign update data

        Returns:
            Updated campaign if found and owned by user, None otherwise
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return None

        # Update fields
        previous_status = campaign.status
        update_data = campaign_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(campaign, field, value)

        db.commit()
        db.refresh(campaign)

        if campaign.status != previous_status:
            verb = _CAMPAIGN_STATUS_VERBS.get(campaign.status, campaign.status)
            activity_log_service.record(
                category=CATEGORY_CAMPAIGN,
                action="campaign_status_changed",
                status=STATUS_INFO,
                title=f"Campagne {verb} · {campaign.name}",
                user_id=user_id,
                entity_type="campaign",
                entity_id=campaign.id,
            )

        return campaign

    def delete_campaign(self, db: Session, campaign_id: int, user_id: int) -> bool:
        """
        Delete a campaign.

        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user deleting the campaign

        Returns:
            True if deleted, False if not found
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return False

        campaign_name = campaign.name
        deleted_id = campaign.id
        db.delete(campaign)
        db.commit()

        activity_log_service.record(
            category=CATEGORY_CAMPAIGN,
            action="campaign_deleted",
            status=STATUS_INFO,
            title=f"Campagne supprimée · {campaign_name}",
            user_id=user_id,
            entity_type="campaign",
            entity_id=deleted_id,
        )

        return True

    def add_prospects_to_campaign(
        self, db: Session, campaign_id: int, user_id: int, prospect_ids: list[int]
    ) -> Campaign | None:
        """
        Add prospects to a campaign.

        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user
            prospect_ids: List of prospect IDs to add

        Returns:
            Updated campaign if found, None otherwise

        Raises:
            HTTPException: If prospects not found or not owned by user
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return None

        # Get prospects
        prospects = db.query(ProspectDB).filter(ProspectDB.id.in_(prospect_ids), ProspectDB.user_id == user_id).all()

        if len(prospects) != len(prospect_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Some prospects not found or not owned by user"
            )

        # Get existing prospect IDs
        existing_ids = {p.id for p in campaign.prospects}

        # Append new prospects after the current max position, preserving the request order, so they
        # keep the "one group per day" sequence going after those already queued.
        max_pos = (
            db.query(sa_func.max(campaign_prospects.c.position))
            .filter(campaign_prospects.c.campaign_id == campaign.id)
            .scalar()
        )
        next_pos = (max_pos + 1) if max_pos is not None else 0
        seen: set[int] = set()
        for pid in prospect_ids:  # request order, not the query's id order
            if pid in existing_ids or pid in seen:
                continue
            seen.add(pid)
            db.execute(campaign_prospects.insert().values(campaign_id=campaign.id, prospect_id=pid, position=next_pos))
            next_pos += 1

        db.commit()
        db.refresh(campaign)

        # On a launched campaign, materialise the new prospects into the send queue so they actually
        # go out; enqueue is re-entrant (already-queued prospects are skipped) and appends them after
        # the current pending slots, i.e. last — matching their position.
        if _is_active(campaign) and (campaign.channel == "sms" or campaign.template_id is not None):
            from services.campaign_queue_service import CampaignQueueService

            CampaignQueueService(db).enqueue_campaign(
                campaign,
                template_id=campaign.template_id,
                ab_template_id_b=campaign.ab_template_id_b,
            )
            db.refresh(campaign)

        return campaign

    def remove_prospect_from_campaign(
        self, db: Session, campaign_id: int, user_id: int, prospect_id: int
    ) -> Campaign | None:
        """
        Remove a prospect from a campaign.

        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user
            prospect_id: Prospect ID to remove

        Returns:
            Updated campaign if found, None otherwise
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return None

        from services.campaign_queue_service import CampaignQueueService

        queue_service = CampaignQueueService(db)
        active: bool = _is_active(campaign)
        # On a launched campaign, cancel the prospect's pending send first so it never goes out.
        if active:
            queue_service.cancel_prospect_pending(campaign_id, prospect_id, "Retiré de la campagne")

        # Find and remove prospect
        for i, prospect in enumerate(campaign.prospects):
            if prospect.id == prospect_id:
                campaign.prospects.pop(i)
                break

        db.commit()
        db.refresh(campaign)

        # Re-date the remaining pending sends so the freed day is filled (the group after moves up).
        if active:
            queue_service.reschedule_pending_initial(campaign)
            db.refresh(campaign)

        return campaign

    def reorder_prospects(
        self, db: Session, campaign_id: int, user_id: int, ordered_prospect_ids: list[int]
    ) -> Campaign | None:
        """
        Set the campaign's prospect send order, then re-date the pending queue to match.

        ``ordered_prospect_ids`` must be exactly the campaign's current prospects, in their new order
        (as produced by the drag & drop table). Positions are rewritten 0-based in that order; on a
        launched campaign the pending J1s are re-paired to the send slots so the order drives the day.

        Args:
            db: Database session.
            campaign_id: Campaign to reorder.
            user_id: Owner of the campaign.
            ordered_prospect_ids: The campaign's prospect ids in their new send order.

        Returns:
            The updated campaign, or None when it is not found.

        Raises:
            HTTPException: 422 when the ids don't match the campaign's prospects exactly.
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return None

        current_ids: set[int] = {prospect.id for prospect in campaign.prospects}
        if len(ordered_prospect_ids) != len(current_ids) or set(ordered_prospect_ids) != current_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="L'ordre fourni ne correspond pas aux prospects de la campagne",
            )

        for position, prospect_id in enumerate(ordered_prospect_ids):
            db.execute(
                campaign_prospects.update()
                .where(
                    campaign_prospects.c.campaign_id == campaign_id,
                    campaign_prospects.c.prospect_id == prospect_id,
                )
                .values(position=position)
            )
        db.commit()
        db.refresh(campaign)

        if _is_active(campaign):
            from services.campaign_queue_service import CampaignQueueService

            CampaignQueueService(db).reschedule_pending_initial(campaign)
            db.refresh(campaign)

        return campaign

    def get_prospect_campaign_memberships(self, db: Session, user_id: int) -> dict[int, list[dict[str, object]]]:
        """
        Map each of the user's prospects to the campaigns it already belongs to (id + name).

        Feeds the "already in a campaign" badges of the add-prospects picker. One join over
        ``campaign_prospects`` × ``campaigns``, scoped to the user; a prospect in no campaign is
        simply absent from the map.

        Args:
            db: Database session.
            user_id: Owner of the campaigns.

        Returns:
            ``{prospect_id: [{"id": campaign_id, "name": campaign_name}, …]}``.
        """
        rows = (
            db.query(campaign_prospects.c.prospect_id, Campaign.id, Campaign.name)
            .join(Campaign, Campaign.id == campaign_prospects.c.campaign_id)
            .filter(Campaign.user_id == user_id)
            .order_by(campaign_prospects.c.prospect_id, Campaign.name)
            .all()
        )
        memberships: dict[int, list[dict[str, object]]] = {}
        for prospect_id, campaign_id, campaign_name in rows:
            memberships.setdefault(prospect_id, []).append({"id": campaign_id, "name": campaign_name})
        return memberships

    def get_campaign_stats(self, db: Session, campaign_id: int, user_id: int) -> CampaignStats | None:
        """
        Get statistics for a campaign.

        Args:
            db: Database session
            campaign_id: Campaign ID
            user_id: ID of the user

        Returns:
            Campaign statistics if campaign found, None otherwise
        """
        campaign = self.get_campaign(db, campaign_id, user_id)
        if not campaign:
            return None

        # Count prospects
        total_prospects = len(campaign.prospects)

        counts = aggregate_email_log_counts(
            db,
            EmailLog.campaign_id == campaign_id,
            EmailLog.user_id == user_id,
        )
        rates = compute_engagement_rates(counts)

        # A/B breakdown (only when campaign has a B variant)
        ab_stats: list[CampaignVariantStats] | None = None
        if campaign.ab_template_id_b:
            ab_stats = []
            for variant in ("A", "B"):
                variant_counts = aggregate_email_log_counts(
                    db,
                    EmailLog.campaign_id == campaign_id,
                    EmailLog.user_id == user_id,
                    EmailLog.ab_variant == variant,
                )
                variant_rates = compute_engagement_rates(variant_counts)
                ab_stats.append(
                    CampaignVariantStats(
                        variant=variant,
                        sent=variant_counts.sent,
                        delivered=variant_counts.delivered,
                        opened=variant_counts.opened,
                        clicked=variant_counts.clicked,
                        replied=variant_counts.replied,
                        open_rate=variant_rates.open_rate,
                        click_rate=variant_rates.click_rate,
                        reply_rate=variant_rates.reply_rate,
                    )
                )

        return CampaignStats(
            campaign_id=campaign_id,
            total_prospects=total_prospects,
            total_emails_sent=counts.sent,
            emails_delivered=counts.delivered,
            emails_opened=counts.opened,
            emails_clicked=counts.clicked,
            emails_replied=counts.replied,
            emails_bounced=counts.bounced,
            emails_failed=counts.failed,
            delivery_rate=rates.delivery_rate,
            open_rate=rates.open_rate,
            click_rate=rates.click_rate,
            reply_rate=rates.reply_rate,
            ab_stats=ab_stats,
        )


# Singleton instance
campaign_service = CampaignService()
