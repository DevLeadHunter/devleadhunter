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

from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.send_policy import (
    DEFAULT_DAILY_CAP,
    DEFAULT_DAYS_OF_WEEK,
    DEFAULT_SPACING_MINUTES,
    DEFAULT_WINDOW_END_HOUR,
    DEFAULT_WINDOW_START_HOUR,
    SendPolicy,
)

try:  # Timezone-aware window when tzdata is present.
    from zoneinfo import ZoneInfo

    _POLICY_TZ: Optional[ZoneInfo] = ZoneInfo("Europe/Paris")
except Exception:  # noqa: BLE001 — no tzdata → treat naive datetimes as local
    _POLICY_TZ = None


def _utcnow() -> datetime:
    """Current UTC time as a timezone-naive datetime (DB-compatible)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_local(dt_utc_naive: datetime) -> datetime:
    """Convert a naive-UTC datetime to naive local (policy) time."""
    if _POLICY_TZ is None:
        return dt_utc_naive
    return dt_utc_naive.replace(tzinfo=timezone.utc).astimezone(_POLICY_TZ).replace(tzinfo=None)


def _to_utc(dt_local_naive: datetime) -> datetime:
    """Convert a naive local (policy) datetime back to naive-UTC."""
    if _POLICY_TZ is None:
        return dt_local_naive
    return dt_local_naive.replace(tzinfo=_POLICY_TZ).astimezone(timezone.utc).replace(tzinfo=None)


class ResolvedPolicy:
    """Effective policy values (from a row or defaults), sanitised."""

    def __init__(
        self,
        daily_cap: int,
        days_of_week: list[int],
        window_start_hour: int,
        window_end_hour: int,
        spacing_minutes: int,
    ) -> None:
        self.daily_cap: int = max(1, daily_cap)
        self.days_of_week: list[int] = sorted(set(days_of_week)) or list(DEFAULT_DAYS_OF_WEEK)
        self.window_start_hour: int = max(0, min(23, window_start_hour))
        # Ensure the window is at least one hour wide.
        self.window_end_hour: int = max(self.window_start_hour + 1, min(24, window_end_hour))
        self.spacing_minutes: int = max(1, spacing_minutes)


class SendPolicyService:
    """Reads/writes the per-user send policy and schedules send slots."""

    # -----------------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------------

    def get_policy(self, db: Session, user_id: int) -> Optional[SendPolicy]:
        """Return the user's SendPolicy row, or None."""
        return db.execute(
            select(SendPolicy).where(SendPolicy.user_id == user_id)
        ).scalar_one_or_none()

    def resolve(self, db: Session, user_id: int) -> ResolvedPolicy:
        """Return the effective policy values (row when set, else defaults)."""
        row: Optional[SendPolicy] = self.get_policy(db, user_id)
        if row is None:
            return ResolvedPolicy(
                DEFAULT_DAILY_CAP,
                list(DEFAULT_DAYS_OF_WEEK),
                DEFAULT_WINDOW_START_HOUR,
                DEFAULT_WINDOW_END_HOUR,
                DEFAULT_SPACING_MINUTES,
            )
        return ResolvedPolicy(
            row.daily_cap,
            list(row.days_of_week) if row.days_of_week else list(DEFAULT_DAYS_OF_WEEK),
            row.window_start_hour,
            row.window_end_hour,
            row.spacing_minutes,
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
    ) -> SendPolicy:
        """Create or update the user's send policy."""
        row: Optional[SendPolicy] = self.get_policy(db, user_id)
        if row is None:
            row = SendPolicy(user_id=user_id)
            db.add(row)
        row.daily_cap = max(1, daily_cap)
        row.days_of_week = sorted({d for d in days_of_week if 0 <= d <= 6}) or list(DEFAULT_DAYS_OF_WEEK)
        row.window_start_hour = max(0, min(23, window_start_hour))
        row.window_end_hour = max(row.window_start_hour + 1, min(24, window_end_hour))
        row.spacing_minutes = max(1, spacing_minutes)
        db.commit()
        db.refresh(row)
        return row

    # -----------------------------------------------------------------------
    # Scheduling
    # -----------------------------------------------------------------------

    def next_send_slots(
        self,
        policy: ResolvedPolicy,
        count: int,
        *,
        start_utc: Optional[datetime] = None,
        seed_counts: Optional[dict[date, int]] = None,
    ) -> list[datetime]:
        """
        Produce ``count`` naive-UTC send datetimes respecting the policy.

        Slots fall on allowed weekdays, inside ``[window_start_hour,
        window_end_hour)`` local time, spaced by ``spacing_minutes``, and never
        exceed ``daily_cap`` per calendar day (local). ``seed_counts`` pre-loads
        per-day usage (e.g. emails already queued today) so a second launch the
        same day doesn't blow the cap.

        Args:
            policy: The resolved policy.
            count: Number of slots to generate.
            start_utc: Earliest UTC instant (defaults to now).
            seed_counts: Optional {local date: already-used count}.

        Returns:
            A list of ``count`` naive-UTC datetimes, ascending.
        """
        if count <= 0:
            return []

        cur: datetime = _to_local(start_utc or _utcnow())
        per_day: dict[date, int] = dict(seed_counts or {})
        slots: list[datetime] = []

        # Hard bound on iterations to avoid any pathological loop.
        guard: int = 0
        while len(slots) < count and guard < count * 400 + 1000:
            guard += 1
            cur = self._advance_into_window(cur, policy)
            day: date = cur.date()
            if per_day.get(day, 0) >= policy.daily_cap:
                cur = self._next_day_window_start(cur, policy)
                continue
            slots.append(_to_utc(cur))
            per_day[day] = per_day.get(day, 0) + 1
            cur = cur + timedelta(minutes=policy.spacing_minutes)

        return slots

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


send_policy_service = SendPolicyService()
