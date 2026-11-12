"""Scheduled launches: a draft campaign starts by itself at the date and time its owner chose.

The launch is the manual one (``campaign_launch_service``): same refusals, same guards when the
sends are queued, same slots of the send policy. This service keeps the scheduled time, takes a
due launch once, and leaves the campaign a draft with its reason when the launch cannot start.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import ColumnElement, func, select, update
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from core.database import SessionLocal
from models.campaign import Campaign, CampaignStatus
from models.email_queue import EmailQueue
from services.activity_log_service import CATEGORY_CAMPAIGN, STATUS_SUCCESS, activity_log_service
from services.campaign_launch_service import CampaignLaunchOutcome, CampaignLaunchRefusal, campaign_launch_service
from services.campaign_queue_service import EnqueueResult
from services.notification_service import notification_service

logger = logging.getLogger(__name__)

_MINIMUM_DELAY: timedelta = timedelta(minutes=1)
_MAXIMUM_DELAY: timedelta = timedelta(days=90)
_LOOP_INTERVAL_SECONDS: int = 30
_STALE_CLAIM_AFTER: timedelta = timedelta(minutes=10)
_ERROR_MAX_LENGTH: int = 500


class CampaignScheduledLaunchError(ValueError):
    """A scheduling request the user must correct (message shown as is)."""


class CampaignLaunchUnderwayError(CampaignScheduledLaunchError):
    """The launch loop is starting the campaign right now: its scheduled time can no longer change."""


class CampaignScheduledLaunchService:
    """Schedules, moves, cancels and carries out the launch of a draft campaign at a chosen time."""

    def schedule(self, db: Session, campaign: Campaign, scheduled_at: datetime) -> None:
        """
        Schedule the launch of a draft, or move a launch already scheduled.

        Args:
            db: Active database session.
            campaign: The user's campaign.
            scheduled_at: When to launch; a naive value is read as UTC.

        Raises:
            CampaignScheduledLaunchError: Not a draft, a time in the past or too far away, or a
                campaign the launch would refuse (missing sender or first template).
            CampaignLaunchUnderwayError: The launch loop is starting the campaign.
        """
        if self._status_of(campaign) != CampaignStatus.DRAFT.value:
            raise CampaignScheduledLaunchError("Seule une campagne en brouillon peut être programmée.")
        moment: datetime = self._validated_moment(scheduled_at)
        refusal: str | None = campaign_launch_service.refusal(db, campaign)
        if refusal is not None:
            raise CampaignScheduledLaunchError(refusal)
        self._write_scheduled_time(db, campaign, moment)

    def cancel(self, db: Session, campaign: Campaign) -> None:
        """
        Drop the scheduled launch and the reason of a missed one.

        A manual launch calls it first, so a campaign started by hand is never started again by the loop.

        Args:
            db: Active database session.
            campaign: The user's campaign.

        Raises:
            CampaignLaunchUnderwayError: The launch loop is starting the campaign.
        """
        has_nothing_scheduled: bool = (
            campaign.scheduled_launch_at is None
            and campaign.scheduled_launch_claimed_at is None
            and campaign.scheduled_launch_error is None
        )
        if has_nothing_scheduled:
            return
        self._write_scheduled_time(db, campaign, None)

    async def launch_due(self) -> int:
        """
        Launch every draft whose scheduled time has come.

        Returns:
            The number of launches attempted.
        """
        db: Session = SessionLocal()
        attempted: int = 0
        try:
            due_ids: list[int] = list(
                db.execute(select(Campaign.id).where(*self._due_conditions(naive_utc_now()))).scalars()
            )
            for campaign_id in due_ids:
                if not self._claim(db, campaign_id):
                    continue
                await self._launch_claimed(db, campaign_id)
                attempted += 1
        finally:
            db.close()
        return attempted

    async def resume_interrupted(self, *, claimed_before: datetime | None = None) -> int:
        """
        Finish the launches cut short, without ever queueing a campaign twice.

        A campaign whose sends were queued before the cut is launched: only its scheduled
        time is cleared. The others start again, their claim still held.

        Args:
            claimed_before: Only the launches taken before this time; ``None`` for every claim,
                which is right at startup only (one process runs the loop, so nothing is in flight).

        Returns:
            The number of interrupted launches found.
        """
        db: Session = SessionLocal()
        try:
            interrupted = select(Campaign.id).where(Campaign.scheduled_launch_claimed_at.is_not(None))
            if claimed_before is not None:
                interrupted = interrupted.where(Campaign.scheduled_launch_claimed_at < claimed_before)
            interrupted_ids: list[int] = list(db.execute(interrupted).scalars())
            for campaign_id in interrupted_ids:
                campaign: Campaign | None = db.get(Campaign, campaign_id)
                if campaign is None:
                    continue
                if self._queued_since_claim(db, campaign):
                    self._settle_launched(db, campaign, detail="Lancement repris après une interruption")
                else:
                    await self._launch_claimed(db, campaign_id)
            return len(interrupted_ids)
        finally:
            db.close()

    async def run_loop(self) -> None:
        """Worker: finish the launches a restart cut short, then launch the due campaigns forever."""
        try:
            interrupted: int = await self.resume_interrupted()
            if interrupted:
                logger.warning("[ScheduledLaunch] %d interrupted launch(es) resumed", interrupted)
        except Exception:
            logger.exception("[ScheduledLaunch] recovery of interrupted launches failed")
        while True:
            try:
                await self.resume_interrupted(claimed_before=naive_utc_now() - _STALE_CLAIM_AFTER)
                await self.launch_due()
            except Exception:
                logger.exception("[ScheduledLaunch] launch tick failed")
            await asyncio.sleep(_LOOP_INTERVAL_SECONDS)

    @staticmethod
    def _status_of(campaign: Campaign) -> str:
        """The campaign's status as its string value (the column loads an enum member, a fresh write may hold a string)."""
        return getattr(campaign.status, "value", campaign.status)

    @staticmethod
    def _validated_moment(scheduled_at: datetime) -> datetime:
        """The scheduled time as naive UTC, refused when in the past or too far away."""
        moment: datetime = (
            scheduled_at if scheduled_at.tzinfo is None else scheduled_at.astimezone(UTC).replace(tzinfo=None)
        )
        now: datetime = naive_utc_now()
        if moment < now + _MINIMUM_DELAY:
            raise CampaignScheduledLaunchError("Choisissez une date et une heure dans le futur.")
        if moment > now + _MAXIMUM_DELAY:
            raise CampaignScheduledLaunchError("Programmation limitée à 90 jours.")
        return moment

    @staticmethod
    def _write_scheduled_time(db: Session, campaign: Campaign, scheduled_at: datetime | None) -> None:
        """Set or clear the scheduled time, unless the launch loop holds the campaign."""
        result = db.execute(
            update(Campaign)
            .where(Campaign.id == campaign.id, Campaign.scheduled_launch_claimed_at.is_(None))
            .values(scheduled_launch_at=scheduled_at, scheduled_launch_error=None)
        )
        db.commit()
        if result.rowcount != 1:
            raise CampaignLaunchUnderwayError("Le lancement programmé est en cours : la campagne démarre.")
        db.refresh(campaign)

    @staticmethod
    def _due_conditions(now: datetime) -> tuple[ColumnElement[bool], ...]:
        """What makes a scheduled launch due: a draft, its time reached, not taken, not already missed."""
        return (
            Campaign.status == CampaignStatus.DRAFT,
            Campaign.scheduled_launch_at <= now,
            Campaign.scheduled_launch_claimed_at.is_(None),
            Campaign.scheduled_launch_error.is_(None),
        )

    def _claim(self, db: Session, campaign_id: int) -> bool:
        """Atomically take a due launch; ``False`` when it moved, was cancelled or was taken first."""
        now: datetime = naive_utc_now()
        result = db.execute(
            update(Campaign)
            .where(Campaign.id == campaign_id, *self._due_conditions(now))
            # Whole seconds: MySQL rounds a DATETIME, and the queue rows of this launch must never read as older.
            .values(scheduled_launch_claimed_at=now.replace(microsecond=0))
        )
        db.commit()
        return result.rowcount == 1

    async def _launch_claimed(self, db: Session, campaign_id: int) -> None:
        """Launch a claimed campaign through the manual path and record how it ended."""
        campaign: Campaign | None = db.get(Campaign, campaign_id)
        if campaign is None:
            return
        db.refresh(campaign)
        started_at_before: datetime | None = campaign.started_at
        try:
            outcome: CampaignLaunchOutcome = campaign_launch_service.launch(db, campaign)
        except CampaignLaunchRefusal as refusal:
            await self._settle_failed(db, campaign_id, str(refusal), started_at_before)
            return
        except Exception as error:
            logger.exception("[ScheduledLaunch] launch of campaign %d crashed", campaign_id)
            db.rollback()
            crashed: Campaign | None = db.get(Campaign, campaign_id)
            if crashed is not None and self._queued_since_claim(db, crashed):
                self._settle_launched(db, crashed, detail="Lancée, avec une erreur après la mise en file")
                return
            await self._settle_failed(db, campaign_id, f"Erreur pendant le lancement : {error}", started_at_before)
            return

        if outcome.enqueue_result.enqueued == 0:
            reason: str = self._empty_queue_reason(outcome.enqueue_result)
            await self._settle_failed(db, campaign_id, reason, started_at_before)
            return
        self._settle_launched(db, campaign, detail=outcome.message)

    @staticmethod
    def _queued_since_claim(db: Session, campaign: Campaign) -> bool:
        """Whether the claimed launch already wrote its sends to the queue."""
        if campaign.scheduled_launch_claimed_at is None:
            return False
        queued: int = db.execute(
            select(func.count())
            .select_from(EmailQueue)
            .where(
                EmailQueue.campaign_id == campaign.id,
                EmailQueue.created_at >= campaign.scheduled_launch_claimed_at,
            )
        ).scalar_one()
        return queued > 0

    @staticmethod
    def _settle_launched(db: Session, campaign: Campaign, *, detail: str) -> None:
        """Clear the scheduled launch of a campaign that is now running and record the launch in the activity feed."""
        campaign.scheduled_launch_at = None
        campaign.scheduled_launch_claimed_at = None
        campaign.scheduled_launch_error = None
        db.commit()
        activity_log_service.record(
            category=CATEGORY_CAMPAIGN,
            action="campaign_scheduled_launch",
            status=STATUS_SUCCESS,
            title=f"Campagne lancée à l'heure programmée · {campaign.name}",
            detail=detail,
            user_id=campaign.user_id,
            entity_type="campaign",
            entity_id=campaign.id,
        )

    @staticmethod
    async def _settle_failed(db: Session, campaign_id: int, reason: str, started_at_before: datetime | None) -> None:
        """Put the campaign back to draft with the reason kept, and notify the admins."""
        campaign: Campaign | None = db.get(Campaign, campaign_id)
        if campaign is None:
            return
        campaign.status = CampaignStatus.DRAFT
        campaign.started_at = started_at_before
        campaign.scheduled_launch_claimed_at = None
        campaign.scheduled_launch_error = reason[:_ERROR_MAX_LENGTH]
        db.commit()
        logger.error("[ScheduledLaunch] campaign %d not launched: %s", campaign_id, reason)
        try:
            await notification_service.notify_error(
                context=f"Lancement programmé · {campaign.name}",
                message=reason,
                tag=f"campaign-scheduled-launch-{campaign_id}",
            )
        except Exception:
            logger.warning("[ScheduledLaunch] failure notification for campaign %d not sent", campaign_id)

    @staticmethod
    def _empty_queue_reason(result: EnqueueResult) -> str:
        """Why a launch that queued nothing is a missed launch, with what the guards left out."""
        left_out: list[str] = []
        if result.skipped_no_demo:
            left_out.append(f"{len(result.skipped_no_demo)} sans site de démo")
        if result.skipped_no_video:
            left_out.append(f"{len(result.skipped_no_video)} sans vidéo de prospection")
        offer_skipped: int = sum(len(entries) for entries in result.skipped_without_offer.values())
        if offer_skipped:
            left_out.append(f"{offer_skipped} sans l'offre du module")
        if result.skipped_locked:
            left_out.append(f"{len(result.skipped_locked)} réservé(s) par un autre module")
        if left_out:
            return "Aucun envoi mis en file : " + ", ".join(left_out) + "."
        return (
            "Aucun envoi mis en file : aucun prospect joignable (désinscrit, « ne plus contacter », sans coordonnées)."
        )


campaign_scheduled_launch_service = CampaignScheduledLaunchService()
