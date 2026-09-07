"""
Send policy service — the user's global cold-email cadence.

Resolves the effective policy (row or defaults) and, above all, provides the
**slot scheduler** ``next_send_slots`` that spreads N emails across the allowed
weekdays and hour window, spaced by ``spacing_minutes`` and capped at
``daily_cap`` per day. This is what makes the whole queue respect
"20 mails/jour, lun–ven, 7h–18h, 1 toutes les 20 min".

Window hours are interpreted in **Europe/Paris** when the timezone database is
available (correct for Léo), and degrade to naive server time otherwise.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.send_policy import (
    DEFAULT_DAILY_CAP,
    DEFAULT_DAYS_OF_WEEK,
    DEFAULT_FOLLOW_UP_DELAY_DAYS,
    DEFAULT_SPACING_MINUTES,
    DEFAULT_WINDOW_END_HOUR,
    DEFAULT_WINDOW_START_HOUR,
    SendPolicy,
)

try:  # Timezone-aware window when tzdata is present.
    from zoneinfo import ZoneInfo

    _POLICY_TZ: ZoneInfo | None = ZoneInfo("Europe/Paris")
except Exception:
    _POLICY_TZ = None


def _utcnow() -> datetime:
    """Current UTC time as a timezone-naive datetime (DB-compatible)."""
    return datetime.now(UTC).replace(tzinfo=None)


def _to_local(dt_utc_naive: datetime) -> datetime:
    """Convert a naive-UTC datetime to naive local (policy) time."""
    if _POLICY_TZ is None:
        return dt_utc_naive
    return dt_utc_naive.replace(tzinfo=UTC).astimezone(_POLICY_TZ).replace(tzinfo=None)


def _to_utc(dt_local_naive: datetime) -> datetime:
    """Convert a naive local (policy) datetime back to naive-UTC."""
    if _POLICY_TZ is None:
        return dt_local_naive
    return dt_local_naive.replace(tzinfo=_POLICY_TZ).astimezone(UTC).replace(tzinfo=None)


class ResolvedPolicy:
    """Effective policy values (from a row or defaults), sanitised."""

    def __init__(
        self,
        daily_cap: int,
        days_of_week: list[int],
        window_start_hour: int,
        window_end_hour: int,
        spacing_minutes: int,
        follow_up_delay_days: int,
    ) -> None:
        self.daily_cap: int = max(1, daily_cap)
        self.days_of_week: list[int] = sorted(set(days_of_week)) or list(DEFAULT_DAYS_OF_WEEK)
        self.window_start_hour: int = max(0, min(23, window_start_hour))
        # Ensure the window is at least one hour wide.
        self.window_end_hour: int = max(self.window_start_hour + 1, min(24, window_end_hour))
        self.spacing_minutes: int = max(1, spacing_minutes)
        self.follow_up_delay_days: int = max(1, follow_up_delay_days)


class SendPolicyService:
    """Reads/writes the per-user send policy and schedules send slots."""

    def get_policy(self, db: Session, user_id: int) -> SendPolicy | None:
        """Return the user's SendPolicy row, or None."""
        return db.execute(select(SendPolicy).where(SendPolicy.user_id == user_id)).scalar_one_or_none()

    def resolve(self, db: Session, user_id: int) -> ResolvedPolicy:
        """Return the effective policy values (row when set, else defaults)."""
        row: SendPolicy | None = self.get_policy(db, user_id)
        if row is None:
            return ResolvedPolicy(
                DEFAULT_DAILY_CAP,
                list(DEFAULT_DAYS_OF_WEEK),
                DEFAULT_WINDOW_START_HOUR,
                DEFAULT_WINDOW_END_HOUR,
                DEFAULT_SPACING_MINUTES,
                DEFAULT_FOLLOW_UP_DELAY_DAYS,
            )
        return ResolvedPolicy(
            row.daily_cap,
            list(row.days_of_week) if row.days_of_week else list(DEFAULT_DAYS_OF_WEEK),
            row.window_start_hour,
            row.window_end_hour,
            row.spacing_minutes,
            row.follow_up_delay_days,
        )

    def upsert(
        self,
        db: Session,
        user_id: int,
        *,
        daily_cap: int,
        days_of_week: list[int],
        window_start_hour: int,
        window_end_hour: int,
        spacing_minutes: int,
        follow_up_delay_days: int,
    ) -> SendPolicy:
        """Create or update the user's send policy."""
        row: SendPolicy | None = self.get_policy(db, user_id)
        if row is None:
            row = SendPolicy(user_id=user_id)
            db.add(row)
        row.daily_cap = max(1, daily_cap)
        row.days_of_week = sorted({d for d in days_of_week if 0 <= d <= 6}) or list(DEFAULT_DAYS_OF_WEEK)
        row.window_start_hour = max(0, min(23, window_start_hour))
        row.window_end_hour = max(row.window_start_hour + 1, min(24, window_end_hour))
        row.spacing_minutes = max(1, spacing_minutes)
        row.follow_up_delay_days = max(1, follow_up_delay_days)
        db.commit()
        db.refresh(row)
        return row

    def next_send_slots(
        self,
        policy: ResolvedPolicy,
        count: int,
        *,
        start_utc: datetime | None = None,
        seed_counts: dict[date, int] | None = None,
        occupied: set[datetime] | None = None,
        per_campaign_cap: int | None = None,
        campaign_seed_counts: dict[date, int] | None = None,
    ) -> list[datetime]:
        """
        Produce ``count`` naive-UTC send datetimes respecting the policy.

        Slots fall on allowed weekdays, inside ``[window_start_hour,
        window_end_hour)`` local time, spaced by ``spacing_minutes``, and never
        exceed ``daily_cap`` per calendar day (local). ``seed_counts`` pre-loads
        per-day usage (e.g. emails already queued today) so a second launch the
        same day doesn't blow the cap.

        ``per_campaign_cap`` additionally limits how many of these slots may land
        on the same day — set it to 1 so one campaign spreads at one send/day.
        ``occupied`` are slots already taken by the user's other pending emails;
        a colliding instant is pushed to the next spaced slot so two campaigns
        launched together don't stack on the exact same timestamp.

        Args:
            policy: The resolved policy.
            count: Number of slots to generate.
            start_utc: Earliest UTC instant (defaults to now).
            seed_counts: Optional {local date: already-used count} across the user.
            occupied: Optional naive-UTC instants already taken by the user.
            per_campaign_cap: Optional max slots per day for this campaign.
            campaign_seed_counts: Optional {local date: this campaign's used count}.

        Returns:
            A list of ``count`` naive-UTC datetimes, ascending.
        """
        if count <= 0:
            return []

        cur: datetime = _to_local(start_utc or _utcnow())
        per_day: dict[date, int] = dict(seed_counts or {})
        per_day_campaign: dict[date, int] = dict(campaign_seed_counts or {})
        taken: set[datetime] = set(occupied or ())
        campaign_cap: int = per_campaign_cap if per_campaign_cap and per_campaign_cap > 0 else count
        slots: list[datetime] = []

        # Hard bound on iterations to avoid any pathological loop.
        guard: int = 0
        while len(slots) < count and guard < count * 400 + 1000:
            guard += 1
            cur = self._advance_into_window(cur, policy)
            day: date = cur.date()
            if per_day.get(day, 0) >= policy.daily_cap or per_day_campaign.get(day, 0) >= campaign_cap:
                cur = self._next_day_window_start(cur, policy)
                continue
            slot: datetime = _to_utc(cur)
            if slot in taken:
                cur = cur + timedelta(minutes=policy.spacing_minutes)
                continue
            slots.append(slot)
            taken.add(slot)
            per_day[day] = per_day.get(day, 0) + 1
            per_day_campaign[day] = per_day_campaign.get(day, 0) + 1
            cur = cur + timedelta(minutes=policy.spacing_minutes)

        return slots

    def follow_up_slot(
        self,
        policy: ResolvedPolicy,
        sent_at_utc: datetime,
        delay_days: int | None = None,
    ) -> datetime:
        """
        When a follow-up should leave, counted in *sending* days.

        Calendar arithmetic is wrong here: ``sent_at + 5 days`` on a Monday lands on
        the following Saturday, outside the window the user configured. Only the
        weekdays ticked in the policy are counted, so a follow-up always falls the
        same weekday and hour as the email it answers.

        Args:
            policy: The resolved policy.
            sent_at_utc: When the answered email actually left (naive UTC).
            delay_days: Sending days to wait; defaults to the policy value.

        Returns:
            The follow-up instant, as naive UTC, inside the sending window.
        """
        remaining: int = max(1, delay_days if delay_days is not None else policy.follow_up_delay_days)
        cur: datetime = _to_local(sent_at_utc)

        # Bounded: a policy always has at least one sending day, so this ends.
        guard: int = 0
        while remaining > 0 and guard < remaining * 8 + 16:
            guard += 1
            cur = cur + timedelta(days=1)
            if cur.weekday() in policy.days_of_week:
                remaining -= 1

        return _to_utc(self._advance_into_window(cur, policy))

    def _advance_into_window(self, cur: datetime, policy: ResolvedPolicy) -> datetime:
        """Move ``cur`` forward to the next valid weekday + in-window instant."""
        # Wrong weekday, or already past the window → jump to next day's start.
        if cur.weekday() not in policy.days_of_week or cur.hour >= policy.window_end_hour:
            return self._next_day_window_start(cur, policy)
        # Before the window on a valid day → snap to the window start.
        if cur.hour < policy.window_start_hour:
            return cur.replace(hour=policy.window_start_hour, minute=0, second=0, microsecond=0)
        return cur

    def _next_day_window_start(self, cur: datetime, policy: ResolvedPolicy) -> datetime:
        """Return the window start of the next allowed weekday after ``cur``."""
        nxt: datetime = (cur + timedelta(days=1)).replace(
            hour=policy.window_start_hour, minute=0, second=0, microsecond=0
        )
        for _ in range(8):
            if nxt.weekday() in policy.days_of_week:
                return nxt
            nxt = nxt + timedelta(days=1)
        return nxt  # unreachable (days_of_week is always non-empty)

    def pending_counts_by_day(self, db: Session, user_id: int) -> dict[date, int]:
        """
        Count the user's already-pending queue items grouped by local send day,
        so a new launch respects the daily cap across campaigns.
        """
        from models.email_queue import EmailQueue

        rows = db.execute(
            select(EmailQueue.scheduled_at).where(
                EmailQueue.user_id == user_id,
                EmailQueue.status == "pending",
            )
        ).all()
        counts: dict[date, int] = {}
        for (scheduled_at,) in rows:
            if scheduled_at is None:
                continue
            day: date = _to_local(scheduled_at).date()
            counts[day] = counts.get(day, 0) + 1
        return counts

    def pending_schedule(self, db: Session, user_id: int) -> tuple[dict[date, int], set[datetime]]:
        """
        Return the user's pending queue as ``(per-local-day counts, occupied instants)``.

        Counts feed the global daily cap; the occupied set lets a new launch avoid
        stacking on an exact timestamp already taken by another campaign.
        """
        from models.email_queue import EmailQueue

        rows = db.execute(
            select(EmailQueue.scheduled_at, EmailQueue.queue_type).where(
                EmailQueue.user_id == user_id,
                EmailQueue.status == "pending",
            )
        ).all()
        counts: dict[date, int] = {}
        occupied: set[datetime] = set()
        for scheduled_at, queue_type in rows:
            if scheduled_at is None:
                continue
            occupied.add(scheduled_at)
            # Follow-ups don't consume the daily cap — only J1s do — so they never push new sends to a later day.
            if queue_type != "initial":
                continue
            day: date = _to_local(scheduled_at).date()
            counts[day] = counts.get(day, 0) + 1
        return counts, occupied

    def pending_campaign_counts_by_day(self, db: Session, campaign_id: int) -> dict[date, int]:
        """Count a single campaign's already-pending J1 items grouped by local send day (follow-ups excluded)."""
        from models.email_queue import EmailQueue

        rows = db.execute(
            select(EmailQueue.scheduled_at).where(
                EmailQueue.campaign_id == campaign_id,
                EmailQueue.status == "pending",
                EmailQueue.queue_type == "initial",
            )
        ).all()
        counts: dict[date, int] = {}
        for (scheduled_at,) in rows:
            if scheduled_at is None:
                continue
            day: date = _to_local(scheduled_at).date()
            counts[day] = counts.get(day, 0) + 1
        return counts

    def sent_campaign_counts_by_day(self, db: Session, campaign_id: int) -> dict[date, int]:
        """Count a campaign's already-gone J1 items grouped by local send day (follow-ups excluded).

        A J1 that already left (sent, or in flight) consumes its day against the per-campaign cap, so
        re-dating the remaining pending J1s must not drop another send on a day this campaign already
        used — e.g. today is full for a 1/day campaign once its first email has gone out.
        """
        from models.email_queue import EmailQueue

        rows = db.execute(
            select(EmailQueue.scheduled_at).where(
                EmailQueue.campaign_id == campaign_id,
                EmailQueue.status.in_(("sent", "sending")),
                EmailQueue.queue_type == "initial",
            )
        ).all()
        counts: dict[date, int] = {}
        for (scheduled_at,) in rows:
            if scheduled_at is None:
                continue
            day: date = _to_local(scheduled_at).date()
            counts[day] = counts.get(day, 0) + 1
        return counts


send_policy_service = SendPolicyService()
