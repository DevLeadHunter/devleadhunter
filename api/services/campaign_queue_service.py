"""
Campaign queue service — manages the cold-email send queue.

Responsibilities:
  - Enqueue initial (J1) and follow-up (J+N) emails when a campaign is launched.
  - A/B testing: split prospects 50/50 between variant A (campaign.template_id)
    and variant B (campaign.ab_template_id_b) at enqueue time.
  - Multiple follow-ups: after a J1 send, schedule all steps from
    ``campaign_follow_ups`` in order.  Falls back to the legacy
    ``follow_up_template_id`` if no ``campaign_follow_ups`` rows exist.
  - Skip sending to prospects who have unsubscribed.
  - Manual queue control: cancel a pending item, or re-queue a skipped one so
    the worker sends it on its next tick.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, joinedload

from enums.demo_site_status import DemoSiteStatus
from models.campaign import Campaign, CampaignStatus, campaign_prospects
from models.campaign_follow_up import CampaignFollowUp
from models.demo_site import DemoSite
from models.email_log import EmailLog
from models.email_queue import EmailQueue
from models.email_template import EmailTemplate
from models.prospect_db import ProspectDB
from services.activity_log_service import CATEGORY_CAMPAIGN, STATUS_INFO, activity_log_service
from services.email_sending_service import EmailSendingService
from services.email_variables import EmailVariables
from services.pricing_service import PricingService
from services.tracking_links import CHANNEL_EMAIL, append_query_param, sms_tracked_link
from services.unsubscribe_service import unsubscribe_service

logger = logging.getLogger(__name__)

# Queue item status values
_STATUS_PENDING = "pending"
_STATUS_SENDING = "sending"
_STATUS_SENT = "sent"
_STATUS_SKIPPED = "skipped"
_STATUS_FAILED = "failed"

# Reason stamped on a row the operator cancels by hand (shown on the campaign page).
_MANUAL_CANCEL_REASON = "Annulé manuellement"

# Reason stamped on a row held back because the prospect was marked « ne plus contacter ».
_DO_NOT_CONTACT_SKIP_REASON = "Ne plus contacter"


@dataclass
class EnqueueResult:
    """
    Outcome of enqueuing a campaign.

    Attributes:
        enqueued:         Number of J1 queue items added.
        skipped_no_demo:  Prospects skipped because their template uses
                          ``{lien_demo}`` but they have no active demo site.
                          Each entry is ``{"id": int, "name": str}``.
        skipped_no_video: Prospects skipped because their template uses
                          ``{lien_video}``/``{vignette_video}`` but their demo
                          has no generated prospection video.
    """

    enqueued: int = 0
    skipped_no_demo: list[dict[str, object]] = field(default_factory=list)
    skipped_no_video: list[dict[str, object]] = field(default_factory=list)


def _utcnow() -> datetime:
    """Return the current UTC time as a timezone-naive datetime (DB-compatible)."""
    return datetime.now(UTC).replace(tzinfo=None)


class CampaignQueueService:
    """Manages the ``email_queue`` table for rate-limited cold outreach."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _purge_skipped_initial_items(self, campaign_id: int) -> int:
        """Delete initial queue items a pause cancelled (pending → skipped) so a resume re-enqueues them.

        A pause marks every pending send ``skipped`` (``cancel_campaign_queue``); those prospects were
        never emailed, yet ``already_queued`` would treat the leftover row as handled and drop them
        forever. Removing the stale rows lets the (re)launch rebuild a clean queue. Returns the count.
        """
        rows: list[EmailQueue] = list(
            self.db.execute(
                select(EmailQueue).where(
                    EmailQueue.campaign_id == campaign_id,
                    EmailQueue.queue_type == "initial",
                    EmailQueue.status == _STATUS_SKIPPED,
                )
            ).scalars()
        )
        for row in rows:
            self.db.delete(row)
        self.db.flush()
        return len(rows)

    def enqueue_campaign(
        self,
        campaign: Campaign,
        template_id: int | None = None,
        ab_template_id_b: int | None = None,
    ) -> EnqueueResult:
        """
        Populate the queue with J1 items for all prospects in the campaign.

        When ``ab_template_id_b`` is provided (A/B test mode), prospects are
        split 50/50: even-indexed prospects get variant A, odd-indexed get B.

        Each item is spaced ``campaign.send_delay_minutes`` apart so the worker
        can dispatch them without extra rate-limiting logic.  Emails are sent
        via the user's ResendConfig — no EmailAccount selection.

        Guard: a prospect is **not** enqueued when its assigned template uses the
        ``{lien_demo}`` placeholder but the prospect has no active demo site.
        This prevents sending a cold email with an empty demo link; such
        prospects are returned in ``skipped_no_demo`` so the operator can
        generate their sites and re-launch.

        Args:
            campaign:         The campaign whose prospects should be enqueued.
            template_id:      J1 template (variant A when A/B testing).
            ab_template_id_b: J1 template for variant B (A/B testing only).

        Returns:
            An :class:`EnqueueResult` with the enqueued count and the list of
            prospects skipped for lacking a demo site.
        """
        # SMS campaigns reuse the whole queue/worker/SendPolicy engine but carry no email template
        # and compose their body at dispatch — handled by a dedicated, isolated path.
        if campaign.channel == "sms":
            return self._enqueue_sms(campaign)

        now = _utcnow()
        is_ab = ab_template_id_b is not None

        # Pre-load templates once to know whether each variant needs a demo link.
        template_a: EmailTemplate | None = self.db.get(EmailTemplate, template_id)
        template_b: EmailTemplate | None = self.db.get(EmailTemplate, ab_template_id_b) if ab_template_id_b else None
        uses_demo_a: bool = self._template_uses_demo_link(template_a)
        uses_demo_b: bool = self._template_uses_demo_link(template_b)
        uses_video_a: bool = self._template_uses_video(template_a)
        uses_video_b: bool = self._template_uses_video(template_b)

        # Append after the last pending slot so re-launching is safe.
        latest: datetime | None = self.db.execute(
            select(func.max(EmailQueue.scheduled_at)).where(
                EmailQueue.campaign_id == campaign.id,
                EmailQueue.status == _STATUS_PENDING,
            )
        ).scalar()

        # Drop initial items a pause cancelled (pending → skipped) so this (re)launch re-enqueues them.
        self._purge_skipped_initial_items(campaign.id)

        # Prospects with a live or sent initial item are never re-added.
        already_queued: set[int] = {
            row[0]
            for row in self.db.execute(
                select(EmailQueue.prospect_id).where(
                    EmailQueue.campaign_id == campaign.id,
                    EmailQueue.queue_type == "initial",
                )
            ).all()
        }

        result = EnqueueResult()

        # --- Pass 1: decide who gets enqueued (skip filters) -----------------
        to_enqueue: list[tuple[int, int, str | None]] = []  # (prospect_id, tpl_id, variant)
        for idx, prospect in enumerate(campaign.prospects):
            if prospect.id in already_queued:
                continue
            if unsubscribe_service.is_unsubscribed(self.db, prospect.email or ""):
                logger.debug("[Queue] Skipping unsubscribed prospect %d", prospect.id)
                continue
            if prospect.do_not_contact:
                logger.debug("[Queue] Skipping do-not-contact prospect %d", prospect.id)
                continue

            if is_ab:
                variant = "A" if idx % 2 == 0 else "B"
                tpl_id = template_id if variant == "A" else ab_template_id_b
                uses_demo = uses_demo_a if variant == "A" else uses_demo_b
                uses_video = uses_video_a if variant == "A" else uses_video_b
            else:
                variant = None
                tpl_id = template_id
                uses_demo = uses_demo_a
                uses_video = uses_video_a

            # Guards: no empty {lien_demo}, and no video-only template without a ready video.
            skip_kind = self._send_guard_skip(
                prospect.id, campaign.user_id, variant, uses_demo, uses_video, campaign.include_video
            )
            if skip_kind == "demo":
                logger.info("[Queue] Skipping prospect %d — no active demo site for {lien_demo}", prospect.id)
                result.skipped_no_demo.append({"id": prospect.id, "name": prospect.name or ""})
                continue
            if skip_kind == "video":
                logger.info("[Queue] Skipping prospect %d — video-only template, no video ready", prospect.id)
                result.skipped_no_video.append({"id": prospect.id, "name": prospect.name or ""})
                continue

            to_enqueue.append((prospect.id, tpl_id, variant))

        # --- Compute send slots (global send policy, or legacy spacing) ------
        slots: list[datetime] = self._schedule_slots(campaign, len(to_enqueue), now, latest)

        # --- Pass 2: create the queue rows ----------------------------------
        for (prospect_id, tpl_id, variant), slot in zip(to_enqueue, slots):
            self.db.add(
                EmailQueue(
                    user_id=campaign.user_id,
                    campaign_id=campaign.id,
                    prospect_id=prospect_id,
                    template_id=tpl_id,
                    email_account_id=None,
                    queue_type="initial",
                    ab_variant=variant,
                    follow_up_index=0,
                    scheduled_at=slot,
                    status=_STATUS_PENDING,
                )
            )
            result.enqueued += 1

        self.db.commit()
        logger.info(
            "[Queue] Enqueued %d J1 items for campaign %d (A/B=%s, %d skipped no-demo)",
            result.enqueued,
            campaign.id,
            is_ab,
            len(result.skipped_no_demo),
        )
        return result

    def enqueue_ready_prospect(self, prospect_id: int, user_id: int) -> int:
        """
        Add a now-sendable prospect to the send queue of each ACTIVE campaign it belongs to.

        The queue is built once, at launch: a prospect skipped then for lacking a demo site or a
        prospection video gets **no** queue row, and nothing reconsiders it. Called when that
        prospect's prospection video becomes ready, this re-applies the launch guards (demo link and
        video) for this one prospect and appends a J1 send wherever it now qualifies. A prospect that
        already has an initial row (of any status) is left untouched — a sent, pending, failed or
        manually cancelled send is never resurrected — and other prospects are not re-evaluated.

        Args:
            prospect_id: The prospect that just became sendable.
            user_id: Owner of the prospect and its campaigns.

        Returns:
            The number of J1 items added across the prospect's active campaigns.
        """
        campaigns: list[Campaign] = list(
            self.db.execute(
                select(Campaign)
                .join(campaign_prospects, campaign_prospects.c.campaign_id == Campaign.id)
                .where(
                    campaign_prospects.c.prospect_id == prospect_id,
                    Campaign.user_id == user_id,
                    Campaign.status == CampaignStatus.ACTIVE.value,
                )
            )
            .scalars()
            .all()
        )
        added: int = 0
        for campaign in campaigns:
            if self._enqueue_single_ready_prospect(campaign, prospect_id):
                added += 1
        return added

    def backfill_ready_prospects(self, campaign: Campaign) -> int:
        """
        Enqueue every now-ready prospect of one campaign that has no send yet — the manual backfill.

        The manual counterpart to the video-ready auto-enqueue: for a launched campaign, adds a J1 for
        each prospect whose demo/video is ready but who was skipped at launch (or added afterwards). It
        reuses the same per-prospect guard, so a prospect already sent, pending, failed or manually
        cancelled is left untouched, and prospects still lacking a demo/video are skipped again.

        Args:
            campaign: The campaign whose ready prospects should be pulled into the queue.

        Returns:
            The number of J1 items added.
        """
        added: int = 0
        for prospect in campaign.prospects:
            if self._enqueue_single_ready_prospect(campaign, prospect.id):
                added += 1
        return added

    def supports_ready_backfill(self, campaign: Campaign) -> bool:
        """
        Whether the ready-prospect backfill can add sends to this campaign.

        True only for an email campaign whose J1 template ships ``{lien_demo}`` or
        ``{lien_video}``/``{vignette_video}`` — the only case a prospect can be left out of the queue
        at launch for a missing demo/video. Drives the "add ready prospects" button, hidden on SMS or
        plain-text campaigns it cannot affect.

        Args:
            campaign: The campaign to inspect.

        Returns:
            True when the campaign's templates use a demo/video link.
        """
        if campaign.channel != "email":
            return False
        template_a: EmailTemplate | None = (
            self.db.get(EmailTemplate, campaign.template_id) if campaign.template_id else None
        )
        template_b: EmailTemplate | None = (
            self.db.get(EmailTemplate, campaign.ab_template_id_b) if campaign.ab_template_id_b else None
        )
        return any(
            self._template_uses_demo_link(template) or self._template_uses_video(template)
            for template in (template_a, template_b)
        )

    def _enqueue_single_ready_prospect(self, campaign: Campaign, prospect_id: int) -> bool:
        """
        Append one pending J1 send for a now-ready prospect in one active campaign, if it qualifies.

        No-op (returns False) when: the campaign is SMS (its queue lifecycle is demo-based, filled at
        launch/resume, not video-driven); the prospect already has an initial row in this campaign
        (any status); it is not part of the campaign; it unsubscribed or is « ne plus contacter »; the
        A/B template is missing; or it still fails the demo/video guard. The A/B variant is taken from
        the prospect's position, exactly as at launch, so the split stays consistent. The send takes
        the next available slot after the last pending J1 (never behind a scheduled follow-up),
        honouring the send policy.

        Args:
            campaign: An active campaign the prospect belongs to.
            prospect_id: The prospect to (maybe) enqueue.

        Returns:
            True when a pending J1 row was created.
        """
        if campaign.channel == "sms":
            return False

        # An initial row of any status means this prospect was already decided for this campaign.
        existing: int | None = self.db.execute(
            select(EmailQueue.id)
            .where(
                EmailQueue.campaign_id == campaign.id,
                EmailQueue.prospect_id == prospect_id,
                EmailQueue.queue_type == "initial",
            )
            .limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            return False

        located: tuple[int, ProspectDB] | None = next(
            ((index, prospect) for index, prospect in enumerate(campaign.prospects) if prospect.id == prospect_id),
            None,
        )
        if located is None:
            return False
        index, prospect = located

        if not prospect.email or unsubscribe_service.is_unsubscribed(self.db, prospect.email):
            return False
        if prospect.do_not_contact:
            return False

        # A/B variant is assigned by position, identically to the bulk enqueue.
        if campaign.ab_template_id_b is not None:
            variant: str | None = "A" if index % 2 == 0 else "B"
            template_id: int | None = campaign.template_id if variant == "A" else campaign.ab_template_id_b
        else:
            variant = None
            template_id = campaign.template_id
        if not template_id:
            return False

        template: EmailTemplate | None = self.db.get(EmailTemplate, template_id)
        skip_kind: str | None = self._send_guard_skip(
            prospect_id,
            campaign.user_id,
            variant,
            self._template_uses_demo_link(template),
            self._template_uses_video(template),
            campaign.include_video,
        )
        if skip_kind is not None:
            return False

        now = _utcnow()
        # Append after the last pending J1 only — never behind a scheduled follow-up (which sits days
        # out), so a newly-ready prospect takes the next available send slot instead of the queue's tail.
        latest: datetime | None = self.db.execute(
            select(func.max(EmailQueue.scheduled_at)).where(
                EmailQueue.campaign_id == campaign.id,
                EmailQueue.status == _STATUS_PENDING,
                EmailQueue.queue_type == "initial",
            )
        ).scalar()
        slot: datetime = self._schedule_slots(campaign, 1, now, latest)[0]
        self.db.add(
            EmailQueue(
                user_id=campaign.user_id,
                campaign_id=campaign.id,
                prospect_id=prospect_id,
                template_id=template_id,
                email_account_id=None,
                queue_type="initial",
                ab_variant=variant,
                follow_up_index=0,
                scheduled_at=slot,
                status=_STATUS_PENDING,
            )
        )
        self.db.commit()
        logger.info("[Queue] Auto-enqueued now-ready prospect %d into active campaign %d", prospect_id, campaign.id)
        return True

    def _schedule_slots(
        self,
        campaign: Campaign,
        count: int,
        now: datetime,
        latest: datetime | None,
    ) -> list[datetime]:
        """
        Compute ``count`` send datetimes.

        When the user has a :class:`SendPolicy`, slots honour its weekday/hour
        window and daily cap (spread across days). Otherwise we keep the legacy
        behaviour: one email every ``campaign.send_delay_minutes``, no window.

        Args:
            campaign: The campaign being enqueued.
            count: Number of slots needed.
            now: Current UTC time.
            latest: Last pending scheduled slot of this campaign, if any.

        Returns:
            ``count`` ascending naive-UTC datetimes.
        """
        if count <= 0:
            return []

        from services.send_policy_service import send_policy_service

        # Take the policy path too when the campaign has its own daily cap (legacy path ignores it).
        policy_row = send_policy_service.get_policy(self.db, campaign.user_id)
        if policy_row is not None or campaign.max_emails_per_day is not None:
            resolved = send_policy_service.resolve(self.db, campaign.user_id)
            start = (
                latest + timedelta(minutes=resolved.spacing_minutes) if (latest is not None and latest > now) else now
            )
            seed_counts, occupied = send_policy_service.pending_schedule(self.db, campaign.user_id)
            return send_policy_service.next_send_slots(
                resolved,
                count,
                start_utc=start,
                seed_counts=seed_counts,
                occupied=occupied,
                per_campaign_cap=campaign.max_emails_per_day,
                campaign_seed_counts=send_policy_service.pending_campaign_counts_by_day(self.db, campaign.id),
            )

        delay = timedelta(minutes=max(campaign.send_delay_minutes, 1))
        start = latest + delay if (latest is not None and latest > now) else now
        return [start + delay * i for i in range(count)]

    def reschedule_pending_initial(self, campaign: Campaign) -> int:
        """Re-date the campaign's pending J1 sends to follow the current prospect order.

        The queue is materialised at launch — each J1 carries a fixed ``scheduled_at`` — so once the
        operator reorders, adds, or removes a prospect on a launched campaign, the pending J1s must be
        re-paired to the send slots in ``campaign_prospects.position`` order (the order the launch
        used). Sends already gone keep their day and still consume it; only pending J1s move, onto the
        same policy cadence. Follow-ups are scheduled off their own J1 at dispatch, so they are left
        untouched.

        Args:
            campaign: The launched campaign whose pending J1s should be re-dated.

        Returns:
            The number of pending J1 items re-dated.
        """
        pending_by_prospect: dict[int, EmailQueue] = {
            item.prospect_id: item
            for item in self.db.execute(
                select(EmailQueue).where(
                    EmailQueue.campaign_id == campaign.id,
                    EmailQueue.queue_type == "initial",
                    EmailQueue.status == _STATUS_PENDING,
                )
            ).scalars()
        }
        if not pending_by_prospect:
            return 0

        # campaign.prospects is ordered by position, so this is the new send order.
        ordered: list[EmailQueue] = [
            pending_by_prospect[prospect.id] for prospect in campaign.prospects if prospect.id in pending_by_prospect
        ]
        slots: list[datetime] = self._reschedule_slots(campaign, ordered)
        for item, slot in zip(ordered, slots):
            item.scheduled_at = slot
        self.db.commit()
        logger.info("[Queue] Re-dated %d pending J1 item(s) for campaign %d", len(ordered), campaign.id)
        return len(ordered)

    def _reschedule_slots(self, campaign: Campaign, pending_items: list[EmailQueue]) -> list[datetime]:
        """
        Compute fresh send slots for the campaign's pending J1s, in their new order.

        Same policy/legacy split as the launch scheduler, but the campaign's own pending J1s (the rows
        being moved) are removed from the per-day usage and occupied instants so they don't block
        themselves, and the days its sent J1s already used are seeded so the per-campaign cap still
        holds (today is full once one J1 has left).

        Args:
            campaign: The campaign being rescheduled.
            pending_items: The pending J1 rows about to be re-dated (in their new order).

        Returns:
            One ascending naive-UTC slot per pending item.
        """
        count: int = len(pending_items)
        if count == 0:
            return []

        now: datetime = _utcnow()

        from services.send_policy_service import send_policy_service

        policy_row = send_policy_service.get_policy(self.db, campaign.user_id)
        if policy_row is None and campaign.max_emails_per_day is None:
            # Legacy spacing: no window/cap, just the campaign's fixed gap from now.
            delay: timedelta = timedelta(minutes=max(campaign.send_delay_minutes, 1))
            return [now + delay * index for index in range(count)]

        resolved = send_policy_service.resolve(self.db, campaign.user_id)
        seed_counts, occupied = send_policy_service.pending_schedule(self.db, campaign.user_id)
        # Drop this campaign's own pending J1s from the global seeds — we're re-dating exactly them.
        for day, used in send_policy_service.pending_campaign_counts_by_day(self.db, campaign.id).items():
            remaining: int = seed_counts.get(day, 0) - used
            if remaining > 0:
                seed_counts[day] = remaining
            else:
                seed_counts.pop(day, None)
        for item in pending_items:
            occupied.discard(item.scheduled_at)

        return send_policy_service.next_send_slots(
            resolved,
            count,
            start_utc=now,
            seed_counts=seed_counts,
            occupied=occupied,
            per_campaign_cap=campaign.max_emails_per_day,
            campaign_seed_counts=send_policy_service.sent_campaign_counts_by_day(self.db, campaign.id),
        )

    def _enqueue_sms(self, campaign: Campaign) -> EnqueueResult:
        """Enqueue cold-SMS items for an SMS-channel campaign (reuses the email queue + scheduler).

        Mirrors :meth:`enqueue_campaign` but with no template / A-B: the reachability guard is
        "French mobile + not opted-out + active demo" (the SMS always ships the demo link). Rows are
        plain :class:`EmailQueue` items with ``template_id=None``, drained by the same worker and sent
        through :meth:`_dispatch_sms`. Prospects are iterated in ``campaign.prospects`` order (explicit
        ``position``), so with ``max_emails_per_day=1`` the send is one group per day.
        """
        from services.sms.phone_normalizer import is_mobile_fr, to_e164_fr
        from services.sms_service import sms_service

        now = _utcnow()
        latest: datetime | None = self.db.execute(
            select(func.max(EmailQueue.scheduled_at)).where(
                EmailQueue.campaign_id == campaign.id,
                EmailQueue.status == _STATUS_PENDING,
            )
        ).scalar()
        self._purge_skipped_initial_items(campaign.id)
        already_queued: set[int] = {
            row[0]
            for row in self.db.execute(
                select(EmailQueue.prospect_id).where(
                    EmailQueue.campaign_id == campaign.id,
                    EmailQueue.queue_type == "initial",
                )
            ).all()
        }

        result = EnqueueResult()
        to_enqueue: list[int] = []
        for prospect in campaign.prospects:
            if prospect.id in already_queued:
                continue
            if prospect.do_not_contact:
                continue
            if not is_mobile_fr(prospect.phone):
                continue  # not SMS-reachable — no 06/07 mobile
            to_e164 = to_e164_fr(prospect.phone)
            if to_e164 and sms_service.is_suppressed(self.db, campaign.user_id, to_e164):
                continue
            if not self._active_demo_for_prospect(prospect.id, campaign.user_id):
                result.skipped_no_demo.append({"id": prospect.id, "name": prospect.name or ""})
                continue
            to_enqueue.append(prospect.id)

        slots: list[datetime] = self._schedule_slots(campaign, len(to_enqueue), now, latest)
        for prospect_id, slot in zip(to_enqueue, slots):
            self.db.add(
                EmailQueue(
                    user_id=campaign.user_id,
                    campaign_id=campaign.id,
                    prospect_id=prospect_id,
                    template_id=None,
                    email_account_id=None,
                    queue_type="initial",
                    ab_variant=None,
                    follow_up_index=0,
                    scheduled_at=slot,
                    status=_STATUS_PENDING,
                )
            )
            result.enqueued += 1

        self.db.commit()
        logger.info(
            "[Queue] Enqueued %d SMS items for campaign %d (%d skipped no-demo)",
            result.enqueued,
            campaign.id,
            len(result.skipped_no_demo),
        )
        return result

    async def _dispatch_sms(self, item: EmailQueue) -> None:
        """Compose and send one cold SMS for an SMS-channel queue item.

        Reuses :meth:`sms_service.send_to_prospect` (all SMS guards: sender / provider / legal window /
        mobile / STOP-suppression, plus compose + provider send + log). Outside the SMS legal window the
        item is pushed forward and left ``pending`` so the worker retries when the window opens, instead
        of being burned as skipped.
        """
        from services.demo_site_service import demo_site_service
        from services.sms_config_service import sms_config_service
        from services.sms_service import sms_service

        prospect: ProspectDB = item.prospect
        campaign: Campaign = item.campaign

        if prospect.do_not_contact:
            item.status = _STATUS_SKIPPED
            item.skip_reason = _DO_NOT_CONTACT_SKIP_REASON
            self.db.commit()
            return

        config = sms_config_service.get(self.db, campaign.user_id)
        if config is None or not config.sender:
            item.status = _STATUS_SKIPPED
            item.skip_reason = "Expéditeur SMS non configuré"
            self.db.commit()
            return

        # Outside the legal SMS window → wait, don't burn the item: re-arm it pending a bit later.
        if sms_service.legal_window_refusal():
            item.status = _STATUS_PENDING
            item.scheduled_at = _utcnow() + timedelta(minutes=60)
            self.db.commit()
            return

        site: DemoSite | None = self._active_demo_for_prospect(prospect.id, campaign.user_id)
        if not site or not site.slug:
            item.status = _STATUS_SKIPPED
            item.skip_reason = "Pas de site démo actif"
            self.db.commit()
            return

        demo_url: str = sms_tracked_link(demo_site_service.demo_url_for_slug(site.slug))
        # Only the "video" template needs it; harmless (rendered as nothing) for the others.
        from services.demo_video_service import has_ready_video, video_page_url

        video_url: str = sms_tracked_link(video_page_url(site.slug)) if has_ready_video(site) else ""
        outcome = await sms_service.send_to_prospect(
            self.db,
            user_id=campaign.user_id,
            prospect=prospect,
            config=config,
            demo_url=demo_url,
            cold=True,
            template_key=campaign.sms_template_key or None,
            video_url=video_url,
        )
        if outcome.sent:
            item.status = _STATUS_SENT
            demo_site_service.restart_demo_ttl(self.db, site, datetime.now(UTC))
        else:
            item.status = _STATUS_SKIPPED
            item.skip_reason = (outcome.reason or "Échec SMS")[:160]
        self.db.commit()

    def reclaim_orphaned_sending(self) -> int:
        """
        Reconcile queue items a dying process left stuck in ``sending``.

        An item only holds ``sending`` while ``_dispatch`` runs, so on a fresh worker start any such
        row is orphaned — a previous process died mid-dispatch (typically a deploy restart). If the
        email actually went out, an ``EmailLog`` exists for the same campaign/prospect at or after the
        item's slot: we settle the row as ``sent`` and arm its follow-ups, the step the dead process
        never reached. Otherwise the send never happened and we requeue the row as ``pending`` to
        retry. The ``EmailLog`` check is what keeps this safe — a claimed row is never re-sent once its
        email already left. Call once at startup, before any dispatch, so no in-flight row is touched.

        Returns:
            The number of orphaned rows reconciled.
        """
        orphans: list[EmailQueue] = list(
            self.db.execute(select(EmailQueue).where(EmailQueue.status == _STATUS_SENDING)).scalars()
        )
        reconciled: int = 0
        for item in orphans:
            log: EmailLog | None = self._sent_log_for_item(item)
            if log is not None:
                item.status = _STATUS_SENT
                item.email_log_id = log.id
                # The email went out, so the post-send bookkeeping the dead process skipped applies too.
                prospect: ProspectDB | None = self.db.get(ProspectDB, item.prospect_id)
                if prospect is not None and not prospect.contacted:
                    prospect.contacted = True
                self.db.commit()
                if item.queue_type == "initial" and not self._has_follow_ups(item.campaign_id, item.prospect_id):
                    self._schedule_follow_ups(item)
                logger.info("[Queue] Reclaimed orphaned item %d as sent (email_log %d)", item.id, log.id)
            else:
                item.status = _STATUS_PENDING
                self.db.commit()
                logger.info("[Queue] Reclaimed orphaned item %d back to pending (no email went out)", item.id)
            reconciled += 1
        if reconciled:
            logger.info("[Queue] Reclaimed %d orphaned 'sending' item(s)", reconciled)
        return reconciled

    def _sent_log_for_item(self, item: EmailQueue) -> EmailLog | None:
        """Return the EmailLog proving this queue item's email actually left, or None.

        Matches the item's campaign, prospect and A/B variant, and only a log sent at or after the
        item's slot so an earlier send to the same prospect is never mistaken for this one.
        """
        conditions = [
            EmailLog.campaign_id == item.campaign_id,
            EmailLog.prospect_id == item.prospect_id,
            EmailLog.sent_at.isnot(None),
            EmailLog.sent_at >= item.scheduled_at,
        ]
        if item.ab_variant:
            conditions.append(EmailLog.ab_variant == item.ab_variant)
        return self.db.execute(
            select(EmailLog).where(*conditions).order_by(EmailLog.sent_at.desc()).limit(1)
        ).scalar_one_or_none()

    def _has_follow_ups(self, campaign_id: int, prospect_id: int) -> bool:
        """Return True when a follow-up queue row already exists for this campaign/prospect."""
        count: int = (
            self.db.execute(
                select(func.count()).where(
                    EmailQueue.campaign_id == campaign_id,
                    EmailQueue.prospect_id == prospect_id,
                    EmailQueue.queue_type == "followup",
                )
            ).scalar()
            or 0
        )
        return count > 0

    def _prospect_replied(self, user_id: int, prospect_id: int) -> bool:
        """
        ``True`` when the prospect has a captured human reply to any of this user's sends.

        Scoped to the user (not the campaign): once a conversation started, no
        automated relance should interrupt it, whichever campaign it came from.

        Args:
            user_id: Owner of the sends.
            prospect_id: The prospect to check.

        Returns:
            ``True`` when at least one send carries a ``replied_at`` timestamp.
        """
        return (
            self.db.execute(
                select(EmailLog.id)
                .where(
                    EmailLog.user_id == user_id,
                    EmailLog.prospect_id == prospect_id,
                    EmailLog.replied_at.isnot(None),
                )
                .limit(1)
            ).scalar_one_or_none()
            is not None
        )

    async def process_next(self) -> bool:
        """
        Dispatch the next due queue item across all active campaigns.

        Returns:
            ``True`` if an item was processed, ``False`` if nothing was due.
        """
        now = _utcnow()

        item: EmailQueue | None = self.db.execute(
            select(EmailQueue)
            .join(Campaign, EmailQueue.campaign_id == Campaign.id)
            .where(
                and_(
                    EmailQueue.status == _STATUS_PENDING,
                    EmailQueue.scheduled_at <= now,
                    Campaign.status == CampaignStatus.ACTIVE.value,
                )
            )
            .order_by(EmailQueue.scheduled_at.asc())
            .limit(1)
        ).scalar_one_or_none()

        if item is None:
            return False

        # Claim the item immediately to prevent concurrent pick.
        item.status = _STATUS_SENDING
        self.db.commit()

        try:
            await self._dispatch(item)
        except Exception as exc:
            logger.error("[Queue] Unhandled error dispatching item %d: %s", item.id, exc)
            item.status = _STATUS_FAILED
            self.db.commit()

        return True

    @staticmethod
    def _template_uses_demo_link(template: EmailTemplate | None) -> bool:
        """
        Return True when a template references the ``{lien_demo}`` placeholder.

        Args:
            template: Template to inspect (subject + HTML body), or None.

        Returns:
            True if the rendered email would contain the demo link placeholder.
        """
        if template is None:
            return False
        haystack: str = f"{template.subject or ''} {template.body_html or ''}"
        return f"{{{EmailVariables.DEMO_LINK}}}" in haystack

    @staticmethod
    def _template_uses_video(template: EmailTemplate | None) -> bool:
        """
        Return True when a template references ``{lien_video}`` or
        ``{vignette_video}`` (either one requires a generated video).
        """
        if template is None:
            return False
        haystack: str = f"{template.subject or ''} {template.body_html or ''}"
        return f"{{{EmailVariables.VIDEO_LINK}}}" in haystack or f"{{{EmailVariables.VIDEO_THUMBNAIL}}}" in haystack

    def _active_demo_for_prospect(self, prospect_id: int, user_id: int) -> DemoSite | None:
        """Latest ACTIVE demo site of a prospect (or None)."""
        return self.db.execute(
            select(DemoSite)
            .where(
                DemoSite.prospect_id == prospect_id,
                DemoSite.user_id == user_id,
                DemoSite.status == DemoSiteStatus.ACTIVE.value,
            )
            .order_by(DemoSite.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    def _demo_link_for_prospect(self, prospect_id: int, user_id: int, variant: str | None) -> str:
        """
        Resolve the ``{lien_demo}`` value: the prospect's active demo URL, tagged with
        the email channel (``?src=email``) and the A/B variant (``&v=A``) so PostHog can
        attribute the demo visit to the channel and the variant. Returns "" when the
        prospect has no active demo.
        """
        site: DemoSite | None = self._active_demo_for_prospect(prospect_id, user_id)
        if not site or not site.demo_url:
            return ""
        url: str = append_query_param(site.demo_url, "src", CHANNEL_EMAIL)
        if variant:
            url = append_query_param(url, "v", variant)
        return url

    def _video_for_prospect(self, prospect_id: int, user_id: int, variant: str | None) -> tuple[str, str]:
        """
        Resolve the ``{lien_video}``/``{vignette_video}`` values for a prospect.

        The player-page link carries the email channel (``?src=email``) and the A/B
        variant (``&v=A``) so PostHog can attribute the video view like ``{lien_demo}``.

        Returns:
            ``(player page URL, thumbnail URL)`` — both "" when the prospect's active demo has no generated video.
        """
        from services.demo_video_service import has_ready_video, public_thumbnail_url, video_page_url

        site: DemoSite | None = self._active_demo_for_prospect(prospect_id, user_id)
        if not site or not has_ready_video(site):
            return "", ""
        url: str = append_query_param(video_page_url(site.slug), "src", CHANNEL_EMAIL)
        if variant:
            url = append_query_param(url, "v", variant)
        return url, public_thumbnail_url(site.slug)

    def _send_guard_skip(
        self,
        prospect_id: int,
        user_id: int,
        variant: str | None,
        uses_demo: bool,
        uses_video: bool,
        include_video: bool,
    ) -> str | None:
        """
        Return why a prospect can't receive the initial email yet, or None when it can.

        Two launch guards, shared by the bulk enqueue and the single-prospect re-enqueue:
          - ``"demo"``: the template ships ``{lien_demo}`` but the prospect has no active demo site.
          - ``"video"``: a video-only template (no ``{lien_demo}`` fallback) has no ready video, or the
            campaign's video toggle is off — the email would have no content. A combo template
            (``{lien_demo}`` + ``{vignette_video}``) is never blocked here: it degrades to the demo
            link at dispatch when the video is missing.

        Args:
            prospect_id: Prospect being evaluated.
            user_id: Owner of the prospect's demo/video.
            variant: A/B variant assigned to this prospect (None outside A/B).
            uses_demo: Whether the assigned template references ``{lien_demo}``.
            uses_video: Whether it references ``{lien_video}``/``{vignette_video}``.
            include_video: The campaign's video toggle.

        Returns:
            ``"demo"``, ``"video"``, or None when the prospect can be enqueued.
        """
        if uses_demo and not self._demo_link_for_prospect(prospect_id, user_id, variant):
            return "demo"
        if uses_video and not uses_demo:
            has_video: bool = include_video and bool(self._video_for_prospect(prospect_id, user_id, variant)[0])
            if not has_video:
                return "video"
        return None

    async def _dispatch(self, item: EmailQueue) -> None:
        """
        Render and send the email for a single queue item, then schedule follow-ups.

        Args:
            item: The queue item to process.
        """
        prospect: ProspectDB = item.prospect
        campaign: Campaign = item.campaign

        # SMS-channel items compose + send through the SMS path (no email template / rendering).
        if campaign.channel == "sms":
            await self._dispatch_sms(item)
            return

        template: EmailTemplate | None = item.template

        # Guard: prospect may have unsubscribed after being enqueued.
        if not prospect.email or unsubscribe_service.is_unsubscribed(self.db, prospect.email):
            logger.info("[Queue] Skipping unsubscribed prospect %d", prospect.id)
            item.status = _STATUS_SKIPPED
            self.db.commit()
            return

        # Guard: the operator marked the prospect « ne plus contacter » after it was enqueued.
        if prospect.do_not_contact:
            logger.info("[Queue] Skipping do-not-contact prospect %d", prospect.id)
            item.status = _STATUS_SKIPPED
            item.skip_reason = _DO_NOT_CONTACT_SKIP_REASON
            self.db.commit()
            return

        # A follow-up is NOT auto-skipped on an open/click: opens are a noisy
        # signal (bot/proxy prefetch inflates them), so a relance goes out unless
        # the prospect unsubscribed or the operator cancelled it by hand from the
        # queue. Unsubscribe is still enforced above; manual control lives in
        # ``cancel_queue_item`` / ``requeue_item``.
        #
        # A captured REPLY is different: it is a definitive human signal, and a
        # relance in the middle of a live conversation would be embarrassing.
        if item.queue_type != "initial" and self._prospect_replied(item.user_id, prospect.id):
            logger.info("[Queue] Skipping follow-up for prospect %d — prospect replied", prospect.id)
            item.status = _STATUS_SKIPPED
            item.skip_reason = "Le prospect a répondu"
            self.db.commit()
            return

        # Guard (defense in depth): never send an email whose template needs
        # {lien_demo} when the prospect has no active demo site — e.g. the demo
        # expired between enqueue and dispatch.
        uses_demo: bool = self._template_uses_demo_link(template)
        demo_link: str = self._demo_link_for_prospect(prospect.id, item.user_id, item.ab_variant)
        if uses_demo and not demo_link:
            logger.info("[Queue] Skipping send for prospect %d — no active demo site for {lien_demo}", prospect.id)
            item.status = _STATUS_SKIPPED
            self.db.commit()
            return

        if uses_demo and demo_link:
            demo_site = self._active_demo_for_prospect(prospect.id, item.user_id)
            if demo_site is not None and demo_site.demo_link_sent_at is None:
                from services.demo_site_service import demo_site_service

                try:
                    await demo_site_service.ensure_storyblok_space_for_outreach(self.db, demo_site)
                except Exception:
                    logger.warning(
                        "[Queue] Storyblok outreach swap failed for prospect %d — sending anyway",
                        prospect.id,
                        exc_info=True,
                    )

        # Video: attach it only when the template uses it AND the campaign's video
        # toggle is on. A video-only template (no {lien_demo} fallback) with no
        # usable video has nothing to say and is skipped; a combo template just
        # degrades to its demo link (empty vignette).
        uses_video: bool = self._template_uses_video(template)
        video_link, video_thumbnail_url = "", ""
        if uses_video and campaign.include_video:
            video_link, video_thumbnail_url = self._video_for_prospect(prospect.id, item.user_id, item.ab_variant)
        if uses_video and not uses_demo and not video_link:
            logger.info("[Queue] Skipping send for prospect %d — video-only template, no video ready", prospect.id)
            item.status = _STATUS_SKIPPED
            self.db.commit()
            return

        # Build personalisation variables ({salutation}/{prenom}/{nom} come from
        # the resolved decision-maker — never the company name).
        sale_price_cents: int = PricingService.sale_price_cents(self.db, item.user_id)
        variables: dict[str, str] = EmailVariables.build_for_prospect(
            self.db, prospect, demo_link, video_link, video_thumbnail_url, sale_price_cents=sale_price_cents
        )

        email_service = EmailSendingService(self.db)
        subject: str = email_service.replace_variables(template.subject, variables)
        body_html: str = email_service.replace_variables(template.body_html, variables)

        # Behaviour-personalised follow-up (additive — keeps the rendered template
        # as the base and falls back to it if there is no behaviour data / LLM).
        if item.queue_type == "followup" and getattr(campaign, "behavior_personalized_followups", False):
            try:
                from services.behavior_service import behavior_service

                personalized = await behavior_service.draft_personalized_followup(
                    self.db,
                    item.user_id,
                    prospect,
                    base_subject=subject,
                    base_body_html=body_html,
                )
                subject = personalized.get("subject", subject) or subject
                body_html = personalized.get("body_html", body_html) or body_html
            except Exception as exc:
                logger.warning("[Queue] Behaviour personalisation failed for prospect %d: %s", prospect.id, exc)

        # Append the signature LAST so it survives the LLM personalisation above.
        from services.email_signatures import render_signature_html

        body_html += render_signature_html(self.db, template.signature_id, variables, user_id=item.user_id)

        result: dict = await email_service.send_via_user_identity(
            user_id=item.user_id,
            recipient_email=prospect.email,
            recipient_name=prospect.name,
            subject=subject,
            body_html=body_html,
            prospect_id=str(prospect.id),
            campaign_id=str(item.campaign_id),
            ab_variant=item.ab_variant,
        )

        item.email_log_id = result.get("email_log_id")
        item.status = _STATUS_SENT if result.get("success") else _STATUS_FAILED
        self.db.commit()

        # Schedule follow-ups after a successful J1 send.
        if item.queue_type == "initial" and result.get("success"):
            self._schedule_follow_ups(item)

    def _demo_link_outlives(self, j1_item: EmailQueue, template_id: int | None, scheduled_at: datetime) -> bool:
        """
        Whether a follow-up may be queued, i.e. its demo link will still be alive.

        A demo site dies ``DEMO_SITE_TTL_DAYS`` after its demo link is **first emailed**
        to the prospect (``demo_link_sent_at``). Before that send the site stays live
        so batches can be generated ahead of a slow outreach cadence.

        The refusal is recorded as a ``skipped`` queue row so the campaign page shows
        why the sequence stopped, instead of the follow-up silently never existing.

        Args:
            j1_item: The J1 whose follow-up is being scheduled.
            template_id: Template of the follow-up step.
            scheduled_at: When that follow-up would leave.

        Returns:
            True when the follow-up can be queued.
        """
        template: EmailTemplate | None = self.db.get(EmailTemplate, template_id) if template_id else None
        if not self._template_uses_demo_link(template):
            return True

        site: DemoSite | None = self._active_demo_for_prospect(j1_item.prospect_id, j1_item.user_id)
        expires_at: datetime | None = site.expires_at if site else None
        if expires_at is not None and expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)
        if expires_at is not None and expires_at > scheduled_at:
            return True

        logger.warning(
            "[Queue] Follow-up skipped for prospect %d — demo site expires %s, before the follow-up on %s",
            j1_item.prospect_id,
            expires_at.isoformat() if expires_at else "never (no active site)",
            scheduled_at.isoformat(),
        )
        self.db.add(
            EmailQueue(
                user_id=j1_item.user_id,
                campaign_id=j1_item.campaign_id,
                prospect_id=j1_item.prospect_id,
                template_id=template_id,
                email_account_id=None,
                queue_type="followup",
                ab_variant=j1_item.ab_variant,
                follow_up_index=j1_item.follow_up_index + 1,
                scheduled_at=scheduled_at,
                status=_STATUS_SKIPPED,
                skip_reason="Site démo expiré avant la relance",
            )
        )
        self.db.commit()
        return False

    def _schedule_follow_ups(self, j1_item: EmailQueue) -> None:
        """
        Create EmailQueue rows for all follow-up steps after a J1 success.

        Uses ``campaign_follow_ups`` rows when they exist; falls back to the
        legacy ``follow_up_template_id`` / ``follow_up_delay_days`` fields.

        Args:
            j1_item: The just-sent J1 queue item.
        """
        campaign: Campaign = j1_item.campaign

        # Prefer the new multi-step follow-up table.
        follow_ups: list[CampaignFollowUp] = (
            self.db.execute(
                select(CampaignFollowUp)
                .where(CampaignFollowUp.campaign_id == campaign.id)
                .order_by(CampaignFollowUp.position.asc())
            )
            .scalars()
            .all()
        )

        from services.send_policy_service import send_policy_service

        resolved = send_policy_service.resolve(self.db, campaign.user_id)
        sent_at: datetime = _utcnow()

        if not follow_ups:
            # Legacy fallback: single follow-up fields on the campaign.
            if campaign.follow_up_template_id:
                follow_up_at = send_policy_service.follow_up_slot(
                    resolved, sent_at, campaign.follow_up_delay_days or None
                )
                if not self._demo_link_outlives(j1_item, campaign.follow_up_template_id, follow_up_at):
                    return
                self.db.add(
                    EmailQueue(
                        user_id=j1_item.user_id,
                        campaign_id=j1_item.campaign_id,
                        prospect_id=j1_item.prospect_id,
                        template_id=campaign.follow_up_template_id,
                        email_account_id=None,
                        queue_type="followup",
                        ab_variant=j1_item.ab_variant,
                        follow_up_index=1,
                        scheduled_at=follow_up_at,
                        status=_STATUS_PENDING,
                    )
                )
                self.db.commit()
            return

        # Each step waits its own delay, counted in sending days from the J1 send.
        elapsed_days: int = 0
        for step in follow_ups:
            elapsed_days += max(1, step.delay_days)
            step_at: datetime = send_policy_service.follow_up_slot(resolved, sent_at, elapsed_days)
            if not self._demo_link_outlives(j1_item, step.template_id, step_at):
                break
            self.db.add(
                EmailQueue(
                    user_id=j1_item.user_id,
                    campaign_id=j1_item.campaign_id,
                    prospect_id=j1_item.prospect_id,
                    template_id=step.template_id,
                    email_account_id=None,
                    queue_type="followup",
                    ab_variant=j1_item.ab_variant,
                    follow_up_index=step.position,
                    scheduled_at=step_at,
                    status=_STATUS_PENDING,
                )
            )
        self.db.commit()
        logger.info(
            "[Queue] Scheduled %d follow-up(s) for prospect %d",
            len(follow_ups),
            j1_item.prospect_id,
        )

    async def send_followup_now(
        self,
        campaign: Campaign,
        prospect_id: int,
        template_id: int,
    ) -> dict:
        """
        Immediately dispatch a follow-up email for a specific prospect,
        bypassing the scheduled queue.  Sends via the user's active identity
        (Resend or Gmail).

        Args:
            campaign:    The parent campaign.
            prospect_id: Target prospect ID.
            template_id: Template to use.

        Returns:
            Result dict from ``EmailSendingService.send_via_user_identity``.
        """
        prospect: ProspectDB | None = self.db.get(ProspectDB, prospect_id)
        template: EmailTemplate | None = self.db.get(EmailTemplate, template_id)

        if not prospect or not prospect.email:
            return {"success": False, "error": "Prospect introuvable ou sans email"}
        if not template:
            return {"success": False, "error": "Template introuvable"}

        video_link, video_thumbnail_url = "", ""
        if self._template_uses_video(template) and campaign.include_video:
            video_link, video_thumbnail_url = self._video_for_prospect(prospect_id, campaign.user_id, None)
        variables: dict[str, str] = EmailVariables.build_for_prospect(
            self.db,
            prospect,
            self._demo_link_for_prospect(prospect_id, campaign.user_id, None),
            video_link,
            video_thumbnail_url,
            sale_price_cents=PricingService.sale_price_cents(self.db, campaign.user_id),
        )

        email_service = EmailSendingService(self.db)
        subject = email_service.replace_variables(template.subject, variables)
        body_html = email_service.replace_variables(template.body_html, variables)

        from services.email_signatures import render_signature_html

        body_html += render_signature_html(self.db, template.signature_id, variables, user_id=campaign.user_id)

        return await email_service.send_via_user_identity(
            user_id=campaign.user_id,
            recipient_email=prospect.email,
            recipient_name=prospect.name,
            subject=subject,
            body_html=body_html,
            prospect_id=str(prospect_id),
            campaign_id=str(campaign.id),
        )

    def cancel_campaign_queue(self, campaign_id: int) -> int:
        """
        Cancel all pending items for a campaign (pause / cancel).

        Returns:
            Number of items cancelled.
        """
        items: list[EmailQueue] = (
            self.db.execute(
                select(EmailQueue).where(
                    EmailQueue.campaign_id == campaign_id,
                    EmailQueue.status == _STATUS_PENDING,
                )
            )
            .scalars()
            .all()
        )

        for item in items:
            item.status = _STATUS_SKIPPED
        self.db.commit()
        logger.info("[Queue] Cancelled %d pending items for campaign %d", len(items), campaign_id)
        return len(items)

    def cancel_queue_item(self, item: EmailQueue) -> None:
        """
        Cancel a single pending queue item so the worker never sends it.

        The row is marked ``skipped`` with a manual reason (surfaced on the campaign
        page); a later :meth:`requeue_item` can put it back. Only a ``pending`` item
        can be cancelled.

        Args:
            item: The queue row to cancel — already loaded and ownership-checked by the caller.

        Raises:
            ValueError: When the item is not ``pending``.
        """
        if item.status != _STATUS_PENDING:
            raise ValueError("Seuls les envois en attente peuvent être annulés")
        item.status = _STATUS_SKIPPED
        item.skip_reason = _MANUAL_CANCEL_REASON
        self.db.commit()
        logger.info("[Queue] Item %d cancelled manually", item.id)

    def skip_pending_for_prospect(self, prospect_id: int, reason: str | None = None) -> int:
        """Hold back every pending queue item of a prospect just marked « ne plus contacter ».

        The rows are marked ``skipped`` with a stop reason instead of being deleted, so the
        campaign page keeps showing the line as *planned but held back* — the trace the operator
        wants. Called by :meth:`ProspectService.set_do_not_contact` when the flag is turned on.

        Args:
            prospect_id: The prospect whose pending sends are cancelled.
            reason: Optional operator note appended to the stop label.

        Returns:
            The number of queue items held back.
        """
        label = _DO_NOT_CONTACT_SKIP_REASON + (f" — {reason}" if reason else "")
        items = (
            self.db.query(EmailQueue)
            .filter(EmailQueue.prospect_id == prospect_id, EmailQueue.status == _STATUS_PENDING)
            .all()
        )
        for item in items:
            item.status = _STATUS_SKIPPED
            item.skip_reason = label[:160]  # EmailQueue.skip_reason is String(160)
        if items:
            self.db.commit()
            logger.info("[Queue] Held back %d pending item(s) for do-not-contact prospect %d", len(items), prospect_id)
        return len(items)

    def cancel_prospect_pending(self, campaign_id: int, prospect_id: int, reason: str) -> int:
        """Skip every pending queue item of one prospect within one campaign (removed from it).

        Marked ``skipped`` with a reason rather than deleted, so the campaign's queue tab keeps the
        trace of a send that was planned but held back; sent/failed rows are left untouched. Called
        when a prospect is removed from a launched campaign so their email never goes out.

        Args:
            campaign_id: The campaign the prospect is being removed from.
            prospect_id: The prospect whose pending sends are cancelled.
            reason: Skip label shown on the queue tab.

        Returns:
            The number of pending items skipped.
        """
        items: list[EmailQueue] = list(
            self.db.execute(
                select(EmailQueue).where(
                    EmailQueue.campaign_id == campaign_id,
                    EmailQueue.prospect_id == prospect_id,
                    EmailQueue.status == _STATUS_PENDING,
                )
            ).scalars()
        )
        for item in items:
            item.status = _STATUS_SKIPPED
            item.skip_reason = reason[:160]
        if items:
            self.db.commit()
            logger.info(
                "[Queue] Cancelled %d pending item(s) for prospect %d removed from campaign %d",
                len(items),
                prospect_id,
                campaign_id,
            )
        return len(items)

    def requeue_item(self, item: EmailQueue) -> None:
        """
        Re-queue a skipped item so the worker sends it on its next tick (~1 min).

        The row returns to ``pending`` scheduled now and its ``skip_reason`` is cleared,
        so the standard dispatch path re-runs in full — personalisation, signature, A/B,
        logging, and follow-up chaining. Only a ``skipped`` item can be re-queued.

        Args:
            item: The queue row to re-send — already loaded and ownership-checked by the caller.

        Raises:
            ValueError: When the item is not ``skipped``.
        """
        if item.status != _STATUS_SKIPPED:
            raise ValueError("Seuls les envois ignorés peuvent être renvoyés")
        item.status = _STATUS_PENDING
        item.skip_reason = None
        item.scheduled_at = _utcnow()
        self.db.commit()
        logger.info("[Queue] Item %d re-queued for immediate send", item.id)

    def get_pending_count(self, campaign_id: int) -> int:
        """Return the number of pending items in the queue for a campaign."""
        return (
            self.db.execute(
                select(func.count()).where(
                    EmailQueue.campaign_id == campaign_id,
                    EmailQueue.status == _STATUS_PENDING,
                )
            ).scalar()
            or 0
        )

    def complete_drained_campaigns(self) -> list[int]:
        """
        Flip every ACTIVE campaign whose send queue has fully drained to COMPLETED.

        A campaign is finished once it has at least one queued send and none left
        ``pending`` or ``sending`` — every J1 and every follow-up has reached a
        terminal state (sent, failed, or skipped). Only ACTIVE campaigns are swept,
        so a paused campaign (whose pending rows were cancelled) never reads as
        completed, and an already-completed one is never touched again. Runs once
        per worker tick, so it also finishes campaigns that drained through a manual
        cancel, a reply, or an expired-demo skip rather than a final send — and
        back-fills campaigns that finished before this sweep existed.

        Returns:
            The ids of the campaigns marked completed this pass.
        """
        remaining = func.sum(case((EmailQueue.status.in_((_STATUS_PENDING, _STATUS_SENDING)), 1), else_=0))
        drained_ids: list[int] = [
            campaign_id
            for (campaign_id,) in self.db.execute(
                select(EmailQueue.campaign_id)
                .join(Campaign, Campaign.id == EmailQueue.campaign_id)
                .where(Campaign.status == CampaignStatus.ACTIVE.value)
                .group_by(EmailQueue.campaign_id)
                .having(remaining == 0)
            ).all()
        ]
        if not drained_ids:
            return []

        campaigns: list[Campaign] = list(
            self.db.execute(
                select(Campaign).where(
                    Campaign.id.in_(drained_ids),
                    Campaign.status == CampaignStatus.ACTIVE.value,
                )
            ).scalars()
        )
        if not campaigns:
            return []

        for campaign in campaigns:
            campaign.status = CampaignStatus.COMPLETED.value
        self.db.commit()

        for campaign in campaigns:
            activity_log_service.record(
                category=CATEGORY_CAMPAIGN,
                action="campaign_completed",
                status=STATUS_INFO,
                title=f"Campagne terminée · {campaign.name}",
                user_id=campaign.user_id,
                entity_type="campaign",
                entity_id=campaign.id,
            )
        logger.info("[Queue] Marked %d campaign(s) completed", len(campaigns))
        return [campaign.id for campaign in campaigns]

    def next_send_at_by_campaign(self, campaign_ids: list[int]) -> dict[int, datetime]:
        """
        Return the earliest still-pending send time per campaign.

        One grouped query for every id, so the campaigns list can show a
        « prochain envoi » without an N+1.

        Args:
            campaign_ids: Campaigns to look up.

        Returns:
            Mapping of campaign id → earliest pending ``scheduled_at``. Campaigns
            with no pending item are absent from the map.
        """
        if not campaign_ids:
            return {}
        rows = self.db.execute(
            select(EmailQueue.campaign_id, func.min(EmailQueue.scheduled_at))
            .where(
                EmailQueue.campaign_id.in_(campaign_ids),
                EmailQueue.status == _STATUS_PENDING,
            )
            .group_by(EmailQueue.campaign_id)
        ).all()
        return {campaign_id: scheduled_at for campaign_id, scheduled_at in rows if scheduled_at is not None}

    def send_window_by_campaign(self, campaign_ids: list[int]) -> dict[int, tuple[datetime, datetime]]:
        """
        Return each campaign's send-activity span — first to last scheduled send.

        Spans every queued row (sent, pending, and skipped alike), so the window
        covers the whole run from the first J1 to the last follow-up regardless of
        what has already gone out. One grouped query, so the list view can slice
        campaigns by when they actually send — not by when they were created —
        without an N+1. Campaigns with an empty queue are absent from the map.

        Args:
            campaign_ids: Campaigns to look up.

        Returns:
            Mapping of campaign id → ``(first_scheduled_at, last_scheduled_at)``.
        """
        if not campaign_ids:
            return {}
        rows = self.db.execute(
            select(
                EmailQueue.campaign_id,
                func.min(EmailQueue.scheduled_at),
                func.max(EmailQueue.scheduled_at),
            )
            .where(EmailQueue.campaign_id.in_(campaign_ids))
            .group_by(EmailQueue.campaign_id)
        ).all()
        return {
            campaign_id: (first, last) for campaign_id, first, last in rows if first is not None and last is not None
        }

    def count_upcoming_sends(self, user_id: int, *, days: int = 7) -> int:
        """
        Count a user's pending sends scheduled within the next ``days`` days.

        Args:
            user_id: Owner of the queue items.
            days:    Size of the forward window (default 7).

        Returns:
            The number of pending items scheduled in ``[now, now + days)``.
        """
        now = _utcnow()
        return (
            self.db.execute(
                select(func.count()).where(
                    EmailQueue.user_id == user_id,
                    EmailQueue.status == _STATUS_PENDING,
                    EmailQueue.scheduled_at >= now,
                    EmailQueue.scheduled_at < now + timedelta(days=days),
                )
            ).scalar()
            or 0
        )

    def get_queue_items(
        self,
        campaign_id: int,
        *,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EmailQueue]:
        """Return queue items ordered by ``scheduled_at``."""
        stmt = select(EmailQueue).where(EmailQueue.campaign_id == campaign_id)
        if status is not None:
            stmt = stmt.where(EmailQueue.status == status)
        return self.db.execute(stmt.order_by(EmailQueue.scheduled_at.asc()).limit(limit).offset(offset)).scalars().all()

    def _active_demos_by_prospect(self, prospect_ids: list[int], user_id: int) -> dict[int, DemoSite]:
        """
        Map each prospect to its latest ACTIVE demo site in a single query (no N+1).

        Args:
            prospect_ids: Prospects to resolve a site for.
            user_id:      Owner of the demo sites.

        Returns:
            ``prospect_id → DemoSite`` for prospects that have an active site.
        """
        unique_ids: list[int] = list({pid for pid in prospect_ids if pid is not None})
        if not unique_ids:
            return {}
        rows: list[DemoSite] = (
            self.db.execute(
                select(DemoSite)
                .where(
                    DemoSite.prospect_id.in_(unique_ids),
                    DemoSite.user_id == user_id,
                    DemoSite.status == DemoSiteStatus.ACTIVE.value,
                )
                .order_by(DemoSite.created_at.desc())
            )
            .scalars()
            .all()
        )
        by_prospect: dict[int, DemoSite] = {}
        for site in rows:
            # Rows come newest-first, so the first seen per prospect is the latest active site.
            if site.prospect_id is not None and site.prospect_id not in by_prospect:
                by_prospect[site.prospect_id] = site
        return by_prospect

    def build_forecast(self, user_id: int, start: datetime, days: int) -> list[dict[str, object]]:
        """
        Build the week-ahead send forecast across all of a user's campaigns.

        Returns every queue item scheduled in ``[start, start + days)`` that is still pending,
        plus items that were skipped for a stated reason (e.g. a demo site that expired before a
        follow-up) so the operator sees why a send will not go out. Each item carries the link the
        email will contain — today the prospect's active demo URL, with the A/B variant appended
        for tracking, exactly as the prospect receives it — and the demo site's review sign-off.

        Args:
            user_id: Owner of the queue.
            start:   Window start (naive UTC).
            days:    Window width in days.

        Returns:
            Forecast rows ordered by ``scheduled_at``, one dict per queue item.
        """
        end: datetime = start + timedelta(days=days)
        items: list[EmailQueue] = (
            self.db.execute(
                select(EmailQueue)
                .options(joinedload(EmailQueue.prospect), joinedload(EmailQueue.campaign))
                .where(
                    EmailQueue.user_id == user_id,
                    EmailQueue.scheduled_at >= start,
                    EmailQueue.scheduled_at < end,
                    or_(
                        EmailQueue.status == _STATUS_PENDING,
                        EmailQueue.status == _STATUS_SENT,
                        and_(EmailQueue.status == _STATUS_SKIPPED, EmailQueue.skip_reason.isnot(None)),
                    ),
                )
                .order_by(EmailQueue.scheduled_at.asc())
            )
            .scalars()
            .all()
        )

        demos: dict[int, DemoSite] = self._active_demos_by_prospect([i.prospect_id for i in items], user_id)

        forecast: list[dict[str, object]] = []
        for item in items:
            site: DemoSite | None = demos.get(item.prospect_id)
            link: str = ""
            if site and site.demo_url:
                link = site.demo_url
                if item.ab_variant:
                    link = f"{link}{'&' if '?' in link else '?'}v={item.ab_variant}"
            prospect = item.prospect
            campaign = item.campaign
            forecast.append(
                {
                    "queue_id": item.id,
                    "scheduled_at": item.scheduled_at.isoformat(),
                    "campaign_id": item.campaign_id,
                    "campaign_name": campaign.name if campaign else "",
                    "prospect_id": item.prospect_id,
                    "prospect_name": prospect.name if prospect else None,
                    "prospect_email": prospect.email if prospect else None,
                    "prospect_city": prospect.city if prospect else None,
                    "prospect_category": prospect.category if prospect else "",
                    "queue_type": item.queue_type,
                    "follow_up_index": item.follow_up_index,
                    "ab_variant": item.ab_variant,
                    "status": item.status,
                    "skip_reason": item.skip_reason,
                    "link": link or None,
                    "link_kind": "website" if link else None,
                    "demo_site_id": site.id if site else None,
                    "site_reviewed_at": site.site_reviewed_at.isoformat() if site and site.site_reviewed_at else None,
                }
            )
        return forecast
