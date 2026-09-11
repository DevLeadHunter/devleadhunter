"""Background worker for the opt-in SMS automations (auto-relance + cold SMS).

Off by default: a user turns each automation on in Paramètres → Relance SMS. On each
pass, for every user who enabled one, it sends a throttled batch — always inside the
legal window, capped per pass and per day (warm-up), never texting a prospect twice.
Relance (emailed, no reaction) is preferred; cold (mobile, no email) fills the rest.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal
from models.sms_config import SmsConfig
from models.sms_message import SmsMessage
from services.sms.send_window import is_within_window, next_send_slot, now_in_paris
from services.sms.smsmode_provider import smsmode_provider
from services.sms_config_service import sms_config_service
from services.sms_relance_service import SmsRelanceCandidate, sms_relance_service
from services.sms_service import sms_service

logger = logging.getLogger(__name__)

try:
    from zoneinfo import ZoneInfo

    _PARIS_TZ: ZoneInfo | None = ZoneInfo("Europe/Paris")
except Exception:  # pragma: no cover - tzdata missing on the host
    _PARIS_TZ = None

# Cadence of the background passes — keep in sync with ``run_loop``'s default interval.
_PASS_INTERVAL: timedelta = timedelta(minutes=30)

# Hard stop of the forecast projection, whatever the window (guards a runaway loop).
_MAX_PROJECTED_SLOTS: int = 500


def _paris_to_utc_naive(moment: datetime) -> datetime:
    """Convert a naive Europe/Paris datetime to naive UTC (identity when tzdata is unavailable)."""
    if _PARIS_TZ is None:
        return moment
    return moment.replace(tzinfo=_PARIS_TZ).astimezone(UTC).replace(tzinfo=None)


def _utc_to_paris_naive(moment: datetime) -> datetime:
    """Convert a naive UTC datetime to naive Europe/Paris (identity when tzdata is unavailable)."""
    if _PARIS_TZ is None:
        return moment
    return moment.replace(tzinfo=UTC).astimezone(_PARIS_TZ).replace(tzinfo=None)


class SmsAutomationService:
    """Send the opt-in automated SMS (auto-relance + cold), throttled and legal."""

    def enabled_configs(self, db: Session) -> list[SmsConfig]:
        """Configs of users who enabled any SMS automation (with a sender, provider ready)."""
        if not smsmode_provider.is_configured:
            return []
        return (
            db.query(SmsConfig)
            .filter(
                SmsConfig.sender != "",
                or_(SmsConfig.auto_relance_enabled.is_(True), SmsConfig.cold_sms_enabled.is_(True)),
            )
            .all()
        )

    def _sent_today(self, db: Session, user_id: int) -> int:
        """Number of SMS (any source) the user sent since midnight UTC — the daily-cap base."""
        day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        return int(
            db.query(func.count(SmsMessage.id))
            .filter(SmsMessage.user_id == user_id, SmsMessage.created_at >= day_start)
            .scalar()
            or 0
        )

    def _gather(self, db: Session, config: SmsConfig, budget: int) -> list[SmsRelanceCandidate]:
        """Collect up to *budget* candidates for a user: relance first, then cold to fill."""
        candidates: list[SmsRelanceCandidate] = []
        if config.auto_relance_enabled:
            candidates += sms_relance_service.find_candidates(
                db, config.user_id, after_days=config.auto_relance_after_days, limit=budget
            )
        if config.cold_sms_enabled and len(candidates) < budget:
            candidates += sms_relance_service.find_cold_candidates(db, config.user_id, limit=budget - len(candidates))
        return candidates[:budget]

    def forecast_rows(self, db: Session, user_id: int, start: datetime, end: datetime) -> list[dict[str, object]]:
        """Project the upcoming automated SMS (relance + cold) as campaign-forecast rows.

        The automations have no queue: candidates are computed live and sent by the
        30-minute passes, capped per day, inside the legal window. This replays that
        scheduling from now on so the forecast shows who should be texted when —
        estimated times, not queue rows (a send that happened leaves the projection).

        Args:
            db: Active database session.
            user_id: Owner of the forecast.
            start: Window start (naive UTC).
            end: Window end (naive UTC, exclusive).

        Returns:
            Forecast rows in the same dict shape as the campaign queue's.
        """
        if not smsmode_provider.is_configured:
            return []
        config = sms_config_service.get(db, user_id)
        if config is None or not config.sender:
            return []
        if not (config.auto_relance_enabled or config.cold_sms_enabled):
            return []

        end_paris = _utc_to_paris_naive(end)
        slots = self._projected_slots(db, user_id, end_paris)
        if not slots:
            return []
        candidates = self._gather(db, config, len(slots))

        rows: list[dict[str, object]] = []
        for candidate, slot_paris in zip(candidates, slots, strict=False):
            scheduled_utc = _paris_to_utc_naive(slot_paris)
            if not (start <= scheduled_utc < end):
                continue
            site = candidate.demo_site
            rows.append(
                {
                    "queue_id": None,
                    "scheduled_at": scheduled_utc.isoformat(),
                    "campaign_id": None,
                    "campaign_name": "Cold SMS auto" if candidate.cold else "Relance SMS auto",
                    "prospect_id": candidate.prospect.id,
                    "prospect_name": candidate.prospect.name,
                    "prospect_email": candidate.prospect.email,
                    "prospect_city": candidate.prospect.city,
                    "prospect_category": candidate.prospect.category or "",
                    "queue_type": "sms_cold" if candidate.cold else "sms_relance",
                    "follow_up_index": 0,
                    "ab_variant": None,
                    "status": "pending",
                    "skip_reason": None,
                    "link": candidate.demo_url or None,
                    "link_kind": "website" if candidate.demo_url else None,
                    "demo_site_id": site.id,
                    "site_reviewed_at": site.site_reviewed_at.isoformat() if site.site_reviewed_at else None,
                }
            )
        return rows

    def _projected_slots(self, db: Session, user_id: int, end_paris: datetime) -> list[datetime]:
        """Paris-time slots the next automated passes will fill, from now until *end_paris*.

        Replays the worker's own throttles: sends only inside the legal window, at most
        ``sms_auto_per_run`` per 30-minute pass, at most ``sms_auto_daily_cap`` per day
        (today's cap already consumed by whatever was sent since midnight).

        Args:
            db: Active database session.
            user_id: Owner (for today's already-sent count).
            end_paris: Projection horizon (naive Europe/Paris).

        Returns:
            One slot per projected SMS, oldest first (several SMS share a pass time).
        """
        slots: list[datetime] = []
        cursor = next_send_slot(now_in_paris())
        daily_used = self._sent_today(db, user_id)
        current_date = cursor.date()
        while cursor < end_paris and len(slots) < _MAX_PROJECTED_SLOTS:
            if cursor.date() != current_date:
                current_date = cursor.date()
                daily_used = 0
            if daily_used >= settings.sms_auto_daily_cap:
                cursor = next_send_slot(datetime.combine(current_date + timedelta(days=1), datetime.min.time()))
                continue
            if not is_within_window(cursor):
                cursor = next_send_slot(cursor)
                continue
            for _ in range(settings.sms_auto_per_run):
                if daily_used >= settings.sms_auto_daily_cap or len(slots) >= _MAX_PROJECTED_SLOTS:
                    break
                slots.append(cursor)
                daily_used += 1
            cursor = cursor + _PASS_INTERVAL
        return slots

    async def run_pass(self, db: Session) -> int:
        """Send one throttled batch of automated SMS across all opted-in users.

        Args:
            db: Active database session.

        Returns:
            The number of SMS sent in this pass.
        """
        # Outside the legal window nothing goes out — wait silently for the next window.
        if sms_service.legal_window_refusal() is not None:
            return 0

        total_sent = 0
        for config in self.enabled_configs(db):
            budget = min(
                settings.sms_auto_per_run, max(0, settings.sms_auto_daily_cap - self._sent_today(db, config.user_id))
            )
            if budget <= 0:
                continue
            for candidate in self._gather(db, config, budget):
                try:
                    if await sms_relance_service.send_relance(db, config.user_id, candidate):
                        total_sent += 1
                except Exception as exc:
                    logger.warning("Auto-SMS failed for prospect %s: %s", candidate.prospect.id, exc)
        return total_sent

    async def run_loop(self, interval_seconds: int = 1800) -> None:
        """Run an automated-SMS pass on a periodic loop (legal window + caps enforced per pass)."""
        while True:
            db = SessionLocal()
            try:
                sent = await self.run_pass(db)
                if sent:
                    logger.info("Auto-SMS pass sent %s message(s)", sent)
            except Exception as exc:
                logger.exception("Auto-SMS pass failed: %s", exc)
            finally:
                db.close()
            await asyncio.sleep(interval_seconds)


sms_automation_service = SmsAutomationService()


async def run_sms_automation_loop(interval_seconds: int = 1800) -> None:
    """Entrypoint used by the API lifespan to run the auto-SMS loop."""
    await sms_automation_service.run_loop(interval_seconds)
