"""Planned automated SMS (auto-relance J+30 + cold): planner, dispatcher, forecast.

Off by default: a user turns each automation on in Paramètres → Relance SMS. Every
upcoming send is MATERIALISED as an :class:`SmsAutoQueue` row with an exact slot —
the forecast shows real times and the operator can cancel or reschedule any pending
row. On each pass the worker revalidates pending rows (eligibility can be lost),
plans the newly eligible prospects, then sends what is due — always inside the legal
window, capped per pass and per day, never texting a prospect twice.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal
from models.campaign import Campaign
from models.email_log import EmailLog
from models.prospect_db import ProspectDB
from models.sms_auto_queue import SmsAutoQueue
from models.sms_config import SmsConfig
from models.sms_message import SmsMessage
from services.demo_site_service import demo_site_service
from services.sms.phone_normalizer import is_mobile_fr, to_e164_fr
from services.sms.send_window import (
    is_within_window,
    next_send_slot,
    now_in_paris,
    paris_to_utc_naive,
    utc_to_paris_naive,
)
from services.sms.smsmode_provider import smsmode_provider
from services.sms_auto_campaign_service import sms_auto_campaign_service
from services.sms_config_service import sms_config_service
from services.sms_relance_service import SmsRelanceCandidate, sms_relance_service
from services.sms_service import sms_service
from services.tracking_links import sms_tracked_link

logger = logging.getLogger(__name__)

# Cadence of the background passes — keep in sync with ``run_loop``'s default interval.
_PASS_INTERVAL: timedelta = timedelta(minutes=30)

# Hard stop of the planner, whatever the horizon (guards a runaway loop).
_MAX_PLANNED: int = 500

# How far ahead the planner materialises rows (a relance is known ~delay days early).
_PLAN_HORIZON_DAYS: int = 60


class SmsAutomationService:
    """Plan, revalidate and send the opt-in automated SMS, throttled and legal."""

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
            db.query(SmsMessage.id).filter(SmsMessage.user_id == user_id, SmsMessage.created_at >= day_start).count()
            or 0
        )

    def _kind_enabled(self, config: SmsConfig, kind: str) -> bool:
        """Whether the automation behind *kind* is currently switched on."""
        return bool(config.auto_relance_enabled if kind == "relance" else config.cold_sms_enabled)

    def _ineligibility_reason(self, db: Session, user_id: int, prospect: ProspectDB | None, kind: str) -> str | None:
        """Why a planned SMS may no longer go out to *prospect*, or ``None`` when still fine.

        Args:
            db: Active database session.
            user_id: Owner of the automation.
            prospect: The recipient (``None`` when deleted since planning).
            kind: ``relance`` or ``cold``.

        Returns:
            A short French reason shown on the forecast row, or ``None``.
        """
        if prospect is None:
            return "Prospect introuvable"
        if db.query(SmsMessage.id).filter(SmsMessage.user_id == user_id, SmsMessage.prospect_id == prospect.id).first():
            return "Déjà SMSé"
        if prospect.do_not_contact:
            return "Ne plus contacter"
        if prospect.sms_auto_excluded:
            return "SMS automatiques coupés pour ce prospect"
        if kind == "cold" and prospect.contacted:
            return "Déjà contacté (le 1er contact SMS ne part jamais)"
        if not is_mobile_fr(prospect.phone):
            return "Numéro non mobile"
        to_e164 = to_e164_fr(prospect.phone)
        if to_e164 and sms_service.is_suppressed(db, user_id, to_e164):
            return "STOP reçu sur ce numéro"
        if kind == "relance" and (
            db.query(EmailLog.id)
            .filter(
                EmailLog.user_id == user_id,
                EmailLog.prospect_id == prospect.id,
                EmailLog.replied_at.isnot(None),
            )
            .first()
        ):
            return "A répondu à l'email"
        if sms_relance_service.demo_for_prospect(db, user_id, prospect.id) is None:
            return "Démo injoignable"
        return None

    def revalidate(self, db: Session) -> None:
        """Sweep pending rows: eligibility lost → skipped, automation switched off → cancelled."""
        pending = db.query(SmsAutoQueue).filter(SmsAutoQueue.status == "pending").all()
        if not pending:
            return
        configs: dict[int, SmsConfig | None] = {}
        changed = False
        for row in pending:
            if row.user_id not in configs:
                configs[row.user_id] = sms_config_service.get(db, row.user_id)
            config = configs[row.user_id]
            if config is None or not config.sender or not self._kind_enabled(config, row.kind):
                row.status = "cancelled"
                row.skip_reason = "Automatisation désactivée"
                changed = True
                continue
            prospect = db.query(ProspectDB).filter(ProspectDB.id == row.prospect_id).first()
            reason = self._ineligibility_reason(db, row.user_id, prospect, row.kind)
            if reason:
                row.status = "skipped"
                row.skip_reason = reason
                changed = True
        if changed:
            db.commit()

    def plan(self, db: Session) -> None:
        """Materialise a pending row, with its exact slot, for every newly eligible prospect."""
        for config in self.enabled_configs(db):
            if config.auto_relance_enabled or config.cold_sms_enabled:
                self._plan_user(db, config)

    def _link_orphan_relances(self, db: Session, user_id: int, campaign: Campaign) -> None:
        """Attach pending relance rows planned before the system campaign existed — no-op afterwards.

        Args:
            db: Active database session.
            user_id: Owner.
            campaign: The user's J+30 system campaign.
        """
        orphans = (
            db.query(SmsAutoQueue)
            .filter(
                SmsAutoQueue.user_id == user_id,
                SmsAutoQueue.kind == "relance",
                SmsAutoQueue.status == "pending",
                SmsAutoQueue.campaign_id.is_(None),
            )
            .all()
        )
        if not orphans:
            return
        for row in orphans:
            row.campaign_id = campaign.id
            sms_auto_campaign_service.attach_prospect(db, campaign, row.prospect_id)
        db.commit()

    def _plan_user(self, db: Session, config: SmsConfig) -> None:
        """Plan the user's unplanned candidates around the slots already taken."""
        relance_campaign: Campaign | None = None
        if config.auto_relance_enabled:
            relance_campaign = sms_auto_campaign_service.ensure(
                db, config.user_id, enabled=True, template_key=config.relance_template_key
            )
            self._link_orphan_relances(db, config.user_id, relance_campaign)
        # ANY existing row blocks a re-plan, whatever its status: a cancelled or skipped send
        # must never sneak back by itself — only the operator's « Replanifier » revives it.
        engaged = {
            prospect_id
            for (prospect_id,) in db.query(SmsAutoQueue.prospect_id)
            .filter(SmsAutoQueue.user_id == config.user_id)
            .all()
        }
        now = now_in_paris()
        delay = timedelta(days=config.auto_relance_after_days)
        entries: list[tuple[datetime, SmsRelanceCandidate]] = []
        if config.auto_relance_enabled:
            for candidate in sms_relance_service.find_relance_projection_candidates(db, config.user_id):
                if candidate.prospect.id in engaged:
                    continue
                eligible = utc_to_paris_naive(candidate.emailed_at + delay) if candidate.emailed_at else now
                entries.append((max(now, eligible), candidate))
        if config.cold_sms_enabled:
            for candidate in sms_relance_service.find_cold_candidates(db, config.user_id, limit=_MAX_PLANNED):
                if candidate.prospect.id in engaged:
                    continue
                entries.append((now, candidate))
        if not entries:
            return
        entries.sort(key=lambda entry: (entry[0], entry[1].cold))

        slot_used: dict[datetime, int] = {}
        day_used: dict[date, int] = {}
        existing = (
            db.query(SmsAutoQueue.scheduled_at)
            .filter(SmsAutoQueue.user_id == config.user_id, SmsAutoQueue.status == "pending")
            .all()
        )
        for (scheduled_at,) in existing:
            paris = utc_to_paris_naive(scheduled_at)
            slot_used[paris] = slot_used.get(paris, 0) + 1
            day_used[paris.date()] = day_used.get(paris.date(), 0) + 1
        today = now.date()
        day_used[today] = day_used.get(today, 0) + self._sent_today(db, config.user_id)

        slots = self._assign_slots(
            [entry[0] for entry in entries],
            slot_used=slot_used,
            day_used=day_used,
            end_paris=now + timedelta(days=_PLAN_HORIZON_DAYS),
        )
        for (_, candidate), slot_paris in zip(entries, slots, strict=False):
            belongs_to_campaign = relance_campaign is not None and not candidate.cold
            db.add(
                SmsAutoQueue(
                    user_id=config.user_id,
                    prospect_id=candidate.prospect.id,
                    demo_site_id=candidate.demo_site.id,
                    campaign_id=relance_campaign.id if belongs_to_campaign and relance_campaign else None,
                    kind="cold" if candidate.cold else "relance",
                    status="pending",
                    scheduled_at=paris_to_utc_naive(slot_paris),
                    emailed_at=candidate.emailed_at,
                )
            )
            if belongs_to_campaign and relance_campaign:
                sms_auto_campaign_service.attach_prospect(db, relance_campaign, candidate.prospect.id)
        db.commit()

    def _assign_slots(
        self,
        earliest_list: list[datetime],
        *,
        slot_used: dict[datetime, int],
        day_used: dict[date, int],
        end_paris: datetime,
    ) -> list[datetime]:
        """Assign each entry the first legal pass at/after its earliest time, capacity aware.

        Replays the worker's throttle forward: legal window only, at most
        ``sms_auto_per_run`` per 30-minute pass and ``sms_auto_daily_cap`` per day —
        counting the slots already taken by previously planned rows and today's real
        sends. Dead time before the soonest entry is skipped so a far horizon stays cheap.

        Args:
            earliest_list: Earliest legal Paris time per entry, sorted ascending.
            slot_used: Pass slot → how many planned sends already sit on it.
            day_used: Paris date → sends already planned (or made today) that day.
            end_paris: Planning horizon (naive Europe/Paris, exclusive).

        Returns:
            One Paris slot per assigned entry, aligned with ``earliest_list`` (may be shorter).
        """
        slot_used = dict(slot_used)
        day_used = dict(day_used)
        assigned: list[datetime] = []
        cursor = next_send_slot(now_in_paris())
        index = 0
        while index < len(earliest_list) and cursor < end_paris and len(assigned) < _MAX_PLANNED:
            if day_used.get(cursor.date(), 0) >= settings.sms_auto_daily_cap:
                cursor = next_send_slot(datetime.combine(cursor.date() + timedelta(days=1), datetime.min.time()))
                continue
            if not is_within_window(cursor):
                cursor = next_send_slot(cursor)
                continue
            if earliest_list[index] > cursor:
                cursor = next_send_slot(earliest_list[index])
                continue
            room = settings.sms_auto_per_run - slot_used.get(cursor, 0)
            while (
                index < len(earliest_list)
                and room > 0
                and day_used.get(cursor.date(), 0) < settings.sms_auto_daily_cap
                and earliest_list[index] <= cursor
                and len(assigned) < _MAX_PLANNED
            ):
                assigned.append(cursor)
                slot_used[cursor] = slot_used.get(cursor, 0) + 1
                day_used[cursor.date()] = day_used.get(cursor.date(), 0) + 1
                room -= 1
                index += 1
            cursor = cursor + _PASS_INTERVAL
        return assigned

    async def _send_due(self, db: Session) -> int:
        """Send the pending rows whose slot has passed, within the per-pass and daily caps."""
        total = 0
        now_utc = datetime.utcnow()
        for config in self.enabled_configs(db):
            budget = min(
                settings.sms_auto_per_run, max(0, settings.sms_auto_daily_cap - self._sent_today(db, config.user_id))
            )
            if budget <= 0:
                continue
            relance_campaign = sms_auto_campaign_service.get(db, config.user_id)
            due = (
                db.query(SmsAutoQueue)
                .filter(
                    SmsAutoQueue.user_id == config.user_id,
                    SmsAutoQueue.status == "pending",
                    SmsAutoQueue.scheduled_at <= now_utc,
                )
                .order_by(SmsAutoQueue.scheduled_at.asc())
                .all()
            )
            sent_for_user = 0
            for row in due:
                if sent_for_user >= budget:
                    break
                prospect = db.query(ProspectDB).filter(ProspectDB.id == row.prospect_id).first()
                reason = self._ineligibility_reason(db, config.user_id, prospect, row.kind)
                candidate = None
                if reason is None and prospect is not None:
                    candidate = sms_relance_service.candidate_for(
                        db, config.user_id, prospect, emailed_at=row.emailed_at, cold=row.kind == "cold"
                    )
                if candidate is None:
                    row.status = "skipped"
                    row.skip_reason = reason or "Non éligible"
                    continue
                template_key = (
                    relance_campaign.sms_template_key
                    if relance_campaign is not None and row.campaign_id == relance_campaign.id
                    else None
                )
                try:
                    sent = await sms_relance_service.send_relance(
                        db, config.user_id, candidate, template_key=template_key
                    )
                except Exception as exc:
                    logger.warning("Auto-SMS failed for prospect %s: %s", row.prospect_id, exc)
                    sent = False
                if sent:
                    row.status = "sent"
                    row.sent_at = datetime.utcnow()
                    sent_for_user += 1
                    total += 1
                else:
                    row.status = "skipped"
                    row.skip_reason = "Échec d'envoi SMS"
            db.commit()
        return total

    def forecast_rows(self, db: Session, user_id: int, start: datetime, end: datetime) -> list[dict[str, object]]:
        """The planned automated SMS of the window, as campaign-forecast rows with exact times.

        Args:
            db: Active database session.
            user_id: Owner of the forecast.
            start: Window start (naive UTC).
            end: Window end (naive UTC, exclusive).

        Returns:
            Forecast rows in the same dict shape as the campaign queue's — pending rows
            with their exact slot, skipped ones with their reason, sent ones as a trace.
        """
        rows = (
            db.query(SmsAutoQueue)
            .filter(
                SmsAutoQueue.user_id == user_id,
                SmsAutoQueue.scheduled_at >= start,
                SmsAutoQueue.scheduled_at < end,
                SmsAutoQueue.status.in_(("pending", "sent", "skipped")),
            )
            .order_by(SmsAutoQueue.scheduled_at.asc())
            .all()
        )
        if not rows:
            return []
        prospects = {
            prospect.id: prospect
            for prospect in db.query(ProspectDB).filter(ProspectDB.id.in_({row.prospect_id for row in rows})).all()
        }
        system_campaign = sms_auto_campaign_service.get(db, user_id)
        out: list[dict[str, object]] = []
        for row in rows:
            prospect = prospects.get(row.prospect_id)
            site = sms_relance_service.demo_for_prospect(db, user_id, row.prospect_id)
            link = sms_tracked_link(demo_site_service.demo_url_for_slug(site.slug)) if site else None
            is_campaign_row = system_campaign is not None and row.campaign_id == system_campaign.id
            out.append(
                {
                    "queue_id": None,
                    "sms_queue_id": row.id,
                    "scheduled_at": row.scheduled_at.isoformat(),
                    "campaign_id": row.campaign_id if is_campaign_row else None,
                    "campaign_name": (
                        system_campaign.name
                        if is_campaign_row and system_campaign
                        else ("Relance SMS auto" if row.kind == "relance" else "Cold SMS auto")
                    ),
                    "prospect_id": row.prospect_id,
                    "prospect_name": prospect.name if prospect else None,
                    "prospect_email": prospect.email if prospect else None,
                    "prospect_city": prospect.city if prospect else None,
                    "prospect_category": (prospect.category or "") if prospect else "",
                    "queue_type": "sms_relance" if row.kind == "relance" else "sms_cold",
                    "follow_up_index": 0,
                    "ab_variant": None,
                    "status": row.status,
                    "skip_reason": row.skip_reason,
                    "link": link,
                    "link_kind": "website" if link else None,
                    "demo_site_id": site.id if site else row.demo_site_id,
                    "site_reviewed_at": site.site_reviewed_at.isoformat() if site and site.site_reviewed_at else None,
                }
            )
        return out

    async def run_pass(self, db: Session) -> int:
        """Revalidate, plan, then send the due automated SMS across all opted-in users.

        Args:
            db: Active database session.

        Returns:
            The number of SMS sent in this pass.
        """
        if not smsmode_provider.is_configured:
            return 0
        self.revalidate(db)
        self.plan(db)
        # Outside the legal window nothing goes out — the plan stays visible, sends wait.
        if sms_service.legal_window_refusal() is not None:
            return 0
        return await self._send_due(db)

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
