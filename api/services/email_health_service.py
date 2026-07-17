"""Email deliverability health — aggregated stats over the user's ``email_logs``.

Everything here is computed from data we already store (no external calls):
per-account and global rates with health thresholds, daily trend series,
a breakdown by recipient mailbox provider (the free way to detect that Orange
or Free silently filters us while Gmail behaves), and an incident journal.

Industry thresholds (2024 Gmail/Yahoo sender requirements):
- complaint (spam) rate: keep < 0.1 %, hard ceiling 0.3 %
- bounce rate: healthy < 2 %, degraded >= 5 %
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from enums.email_status import EmailStatus
from models.email_account import EmailAccount
from models.email_log import EmailLog
from models.email_unsubscribe import EmailUnsubscribe

# Statuses that mean the email actually left (used when sent_at is missing).
_POST_SEND_STATUSES: tuple[str, ...] = (
    EmailStatus.SENT.value,
    EmailStatus.DELIVERED.value,
    EmailStatus.DELIVERY_DELAYED.value,
    EmailStatus.OPENED.value,
    EmailStatus.CLICKED.value,
    EmailStatus.BOUNCED.value,
    EmailStatus.COMPLAINED.value,
)

# Recipient-domain → mailbox-provider families (FR-centric on purpose: the
# target market is French artisans, massively hosted at Orange/Free/SFR).
_PROVIDER_FAMILIES: dict[str, tuple[str, ...]] = {
    "gmail": ("gmail.com", "googlemail.com"),
    "orange": ("orange.fr", "wanadoo.fr"),
    "outlook": ("outlook.com", "outlook.fr", "hotmail.com", "hotmail.fr", "live.com", "live.fr", "msn.com"),
    "free": ("free.fr",),
    "sfr": ("sfr.fr", "neuf.fr", "club-internet.fr"),
    "laposte": ("laposte.net",),
    "bouygues": ("bbox.fr", "bouyguestelecom.fr"),
    "yahoo": ("yahoo.com", "yahoo.fr", "ymail.com"),
    "apple": ("icloud.com", "me.com", "mac.com"),
}

_PROVIDER_LABELS: dict[str, str] = {
    "gmail": "Gmail",
    "orange": "Orange",
    "outlook": "Outlook / Hotmail",
    "free": "Free",
    "sfr": "SFR",
    "laposte": "La Poste",
    "bouygues": "Bouygues",
    "yahoo": "Yahoo",
    "apple": "Apple (iCloud)",
    "other": "Autres (pro, divers)",
}


def _provider_for_domain(domain: str) -> str:
    """Map a recipient domain to a provider family key.

    @param domain - Lower-cased recipient domain (part after ``@``).
    @returns The family key, ``other`` when unknown.
    """
    for family, domains in _PROVIDER_FAMILIES.items():
        if domain in domains:
            return family
    return "other"


def _rate(numerator: int, denominator: int) -> float:
    """Percentage helper (0 when the denominator is 0).

    @param numerator - Count of matching rows.
    @param denominator - Base count.
    @returns The percentage rounded to 2 decimals.
    """
    if denominator <= 0:
        return 0.0
    return round(numerator * 100.0 / denominator, 2)


def _signal(key: str, label: str, value: float, ok_below: float, warn_below: float, *, invert: bool = False,
            unit: str = "%", hint: str = "") -> dict[str, Any]:
    """Build a health signal with its ok/warn/danger status.

    @param key - Stable identifier.
    @param label - French label shown in the UI.
    @param value - Measured value.
    @param ok_below - Value below which the signal is healthy (or above, when inverted).
    @param warn_below - Value below which the signal is a warning (or above, when inverted).
    @param invert - When True, higher is better (e.g. delivery rate).
    @param unit - Display unit.
    @param hint - Short explanation of the threshold.
    @returns The signal payload.
    """
    if invert:
        status = "ok" if value >= ok_below else ("warn" if value >= warn_below else "danger")
    else:
        status = "ok" if value < ok_below else ("warn" if value < warn_below else "danger")
    return {"key": key, "label": label, "value": value, "unit": unit, "status": status, "hint": hint}


class EmailHealthService:
    """Read-only aggregations over ``email_logs`` for the health page."""

    # ------------------------------------------------------------------ #
    # Overview                                                           #
    # ------------------------------------------------------------------ #

    def overview(self, db: Session, user_id: int, period_days: int = 30) -> dict[str, Any]:
        """Global + per-account deliverability stats with health signals.

        @param db - Database session.
        @param user_id - Owner of the logs.
        @param period_days - Rolling window (7/30/90).
        @returns Totals, per-signal statuses and per-account stats.
        """
        since = datetime.utcnow() - timedelta(days=period_days)
        totals = self._stats_for(db, user_id, since=since)

        unsubscribed = int(
            db.query(func.count(EmailUnsubscribe.id))
            .filter(EmailUnsubscribe.user_id == user_id, EmailUnsubscribe.created_at >= since)
            .scalar()
            or 0
        )
        totals["unsubscribed"] = unsubscribed
        totals["unsubscribe_rate"] = _rate(unsubscribed, totals["sent"])

        signals = [
            _signal(
                "complaint_rate", "Signalés comme spam", totals["complaint_rate"], 0.1, 0.3,
                hint="Au-delà de 0,3 %, Gmail et Yahoo vous rangent direct en spam.",
            ),
            _signal(
                "bounce_rate", "Emails rejetés", totals["bounce_rate"], 2.0, 5.0,
                hint="Adresses invalides ou boîtes pleines. À nettoyer au-delà de 2 %.",
            ),
            _signal(
                "delivery_rate", "Bien arrivés", totals["delivery_rate"], 95.0, 90.0, invert=True,
                hint="Emails acceptés par le destinataire. Visez 95 % ou plus.",
            ),
            _signal(
                "unsubscribe_rate", "Désinscriptions", totals["unsubscribe_rate"], 0.5, 2.0,
                hint="Au-delà de 0,5 %, revoyez le message ou le ciblage.",
            ),
        ]

        accounts: list[dict[str, Any]] = []
        rows: list[EmailAccount] = (
            db.query(EmailAccount).filter(EmailAccount.user_id == user_id).order_by(EmailAccount.id).all()
        )
        for account in rows:
            stats = self._stats_for(db, user_id, since=since, email_account_id=account.id)
            accounts.append(
                {
                    "id": account.id,
                    "email": account.email,
                    "name": account.name,
                    "account_type": account.account_type,
                    "is_default": account.is_default,
                    "is_active": account.is_active,
                    "domain": (account.domain or account.email.split("@")[-1]).lower(),
                    "stats": stats,
                }
            )

        return {"period_days": period_days, "totals": totals, "signals": signals, "accounts": accounts}

    def _stats_for(
        self,
        db: Session,
        user_id: int,
        *,
        since: datetime,
        email_account_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Counters + rates over one window, optionally scoped to one account.

        @param db - Database session.
        @param user_id - Owner of the logs.
        @param since - Window start (compared to ``sent_at``/``created_at``).
        @param email_account_id - Restrict to a single sending account.
        @returns Raw counters and derived percentage rates.
        """
        sent_marker = or_(EmailLog.sent_at.isnot(None), EmailLog.status.in_(_POST_SEND_STATUSES))
        delivered_marker = or_(
            EmailLog.delivered_at.isnot(None),
            EmailLog.status.in_(
                (EmailStatus.DELIVERED.value, EmailStatus.OPENED.value, EmailStatus.CLICKED.value)
            ),
        )
        opened_marker = or_(
            EmailLog.opened_at.isnot(None),
            EmailLog.status.in_((EmailStatus.OPENED.value, EmailStatus.CLICKED.value)),
        )
        clicked_marker = or_(EmailLog.clicked_at.isnot(None), EmailLog.status == EmailStatus.CLICKED.value)
        bounced_marker = or_(EmailLog.bounced_at.isnot(None), EmailLog.status == EmailStatus.BOUNCED.value)
        complained_marker = or_(
            EmailLog.complained_at.isnot(None), EmailLog.status == EmailStatus.COMPLAINED.value
        )
        suppressed_marker = or_(
            EmailLog.suppressed_at.isnot(None), EmailLog.status == EmailStatus.SUPPRESSED.value
        )
        failed_marker = or_(EmailLog.failed_at.isnot(None), EmailLog.status == EmailStatus.FAILED.value)

        query = db.query(
            func.sum(case((sent_marker, 1), else_=0)),
            func.sum(case((delivered_marker, 1), else_=0)),
            func.sum(case((opened_marker, 1), else_=0)),
            func.sum(case((clicked_marker, 1), else_=0)),
            func.sum(case((bounced_marker, 1), else_=0)),
            func.sum(case((complained_marker, 1), else_=0)),
            func.sum(case((suppressed_marker, 1), else_=0)),
            func.sum(case((failed_marker, 1), else_=0)),
        ).filter(
            EmailLog.user_id == user_id,
            func.coalesce(EmailLog.sent_at, EmailLog.created_at) >= since,
        )
        if email_account_id is not None:
            query = query.filter(EmailLog.email_account_id == email_account_id)

        row = query.one()
        sent, delivered, opened, clicked, bounced, complained, suppressed, failed = (
            int(value or 0) for value in row
        )

        return {
            "sent": sent,
            "delivered": delivered,
            "opened": opened,
            "clicked": clicked,
            "bounced": bounced,
            "complained": complained,
            "suppressed": suppressed,
            "failed": failed,
            "delivery_rate": _rate(delivered, sent),
            "open_rate": _rate(opened, delivered or sent),
            "click_rate": _rate(clicked, delivered or sent),
            "bounce_rate": _rate(bounced, sent),
            "complaint_rate": _rate(complained, sent),
        }

    # ------------------------------------------------------------------ #
    # Trends                                                             #
    # ------------------------------------------------------------------ #

    def trends(self, db: Session, user_id: int, period_days: int = 30) -> dict[str, Any]:
        """Daily cohort series (per send day) for the trend charts.

        Bounces/complaints are attributed to the day the email was SENT, so a
        rising complaint curve reads as "the sends of that day caused it".

        @param db - Database session.
        @param user_id - Owner of the logs.
        @param period_days - Rolling window (7/30/90).
        @returns One point per day: counts + derived rates.
        """
        since = datetime.utcnow() - timedelta(days=period_days)
        day = func.date(func.coalesce(EmailLog.sent_at, EmailLog.created_at))

        rows = (
            db.query(
                day.label("day"),
                func.sum(
                    case((or_(EmailLog.sent_at.isnot(None), EmailLog.status.in_(_POST_SEND_STATUSES)), 1), else_=0)
                ),
                func.sum(
                    case(
                        (
                            or_(
                                EmailLog.delivered_at.isnot(None),
                                EmailLog.status.in_(
                                    (
                                        EmailStatus.DELIVERED.value,
                                        EmailStatus.OPENED.value,
                                        EmailStatus.CLICKED.value,
                                    )
                                ),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                func.sum(
                    case(
                        (
                            or_(
                                EmailLog.opened_at.isnot(None),
                                EmailLog.status.in_((EmailStatus.OPENED.value, EmailStatus.CLICKED.value)),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                func.sum(
                    case(
                        (or_(EmailLog.bounced_at.isnot(None), EmailLog.status == EmailStatus.BOUNCED.value), 1),
                        else_=0,
                    )
                ),
                func.sum(
                    case(
                        (
                            or_(
                                EmailLog.complained_at.isnot(None),
                                EmailLog.status == EmailStatus.COMPLAINED.value,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
            )
            .filter(
                EmailLog.user_id == user_id,
                func.coalesce(EmailLog.sent_at, EmailLog.created_at) >= since,
            )
            .group_by(day)
            .order_by(day)
            .all()
        )

        by_day: dict[str, dict[str, int]] = {}
        for row in rows:
            iso = row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0])
            by_day[iso] = {
                "sent": int(row[1] or 0),
                "delivered": int(row[2] or 0),
                "opened": int(row[3] or 0),
                "bounced": int(row[4] or 0),
                "complained": int(row[5] or 0),
            }

        # Dense series (a day without sends still appears — flat charts read better).
        days: list[dict[str, Any]] = []
        cursor = (datetime.utcnow() - timedelta(days=period_days - 1)).date()
        today = datetime.utcnow().date()
        while cursor <= today:
            iso = cursor.isoformat()
            counts = by_day.get(iso, {"sent": 0, "delivered": 0, "opened": 0, "bounced": 0, "complained": 0})
            days.append(
                {
                    "date": iso,
                    **counts,
                    "bounce_rate": _rate(counts["bounced"], counts["sent"]),
                    "complaint_rate": _rate(counts["complained"], counts["sent"]),
                    "delivery_rate": _rate(counts["delivered"], counts["sent"]),
                }
            )
            cursor += timedelta(days=1)

        return {"period_days": period_days, "days": days}

    # ------------------------------------------------------------------ #
    # Provider breakdown                                                 #
    # ------------------------------------------------------------------ #

    def providers(self, db: Session, user_id: int, period_days: int = 30) -> dict[str, Any]:
        """Deliverability broken down by recipient mailbox provider.

        This is the silent-filtering detector: a provider whose bounce rate
        explodes (or that never opens anything) while others behave normally
        is very likely spam-foldering us — no external tool can tell us that
        for Orange/Free/SFR, but our own logs can.

        @param db - Database session.
        @param user_id - Owner of the logs.
        @param period_days - Rolling window.
        @returns One entry per provider family, sorted by volume.
        """
        since = datetime.utcnow() - timedelta(days=period_days)
        domain_expr = func.lower(func.substring_index(EmailLog.recipient_email, "@", -1))

        rows = (
            db.query(
                domain_expr.label("domain"),
                func.sum(
                    case((or_(EmailLog.sent_at.isnot(None), EmailLog.status.in_(_POST_SEND_STATUSES)), 1), else_=0)
                ),
                func.sum(
                    case(
                        (
                            or_(
                                EmailLog.delivered_at.isnot(None),
                                EmailLog.status.in_(
                                    (
                                        EmailStatus.DELIVERED.value,
                                        EmailStatus.OPENED.value,
                                        EmailStatus.CLICKED.value,
                                    )
                                ),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                func.sum(
                    case(
                        (
                            or_(
                                EmailLog.opened_at.isnot(None),
                                EmailLog.status.in_((EmailStatus.OPENED.value, EmailStatus.CLICKED.value)),
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                func.sum(
                    case(
                        (or_(EmailLog.bounced_at.isnot(None), EmailLog.status == EmailStatus.BOUNCED.value), 1),
                        else_=0,
                    )
                ),
                func.sum(
                    case(
                        (
                            or_(
                                EmailLog.complained_at.isnot(None),
                                EmailLog.status == EmailStatus.COMPLAINED.value,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
            )
            .filter(
                EmailLog.user_id == user_id,
                func.coalesce(EmailLog.sent_at, EmailLog.created_at) >= since,
            )
            .group_by(domain_expr)
            .all()
        )

        families: dict[str, dict[str, Any]] = {}
        for row in rows:
            family = _provider_for_domain(str(row[0] or ""))
            bucket = families.setdefault(
                family,
                {"sent": 0, "delivered": 0, "opened": 0, "bounced": 0, "complained": 0, "domains": set()},
            )
            bucket["sent"] += int(row[1] or 0)
            bucket["delivered"] += int(row[2] or 0)
            bucket["opened"] += int(row[3] or 0)
            bucket["bounced"] += int(row[4] or 0)
            bucket["complained"] += int(row[5] or 0)
            bucket["domains"].add(str(row[0] or ""))

        providers: list[dict[str, Any]] = []
        for family, bucket in families.items():
            sent = bucket["sent"]
            bounce_rate = _rate(bucket["bounced"], sent)
            complaint_rate = _rate(bucket["complained"], sent)
            open_rate = _rate(bucket["opened"], bucket["delivered"] or sent)

            status = "ok"
            note = ""
            if bounce_rate >= 5.0 or complaint_rate >= 0.3:
                status = "danger"
                note = "Trop d'emails rejetés ou signalés spam — ce fournisseur nous bloque."
            elif bounce_rate >= 2.0:
                status = "warn"
                note = "Part d'emails rejetés à surveiller."
            elif sent >= 20 and bucket["opened"] == 0:
                status = "warn"
                note = "Aucune ouverture malgré le volume — filtrage spam probable."

            providers.append(
                {
                    "provider": family,
                    "label": _PROVIDER_LABELS.get(family, family),
                    "domains": sorted(bucket["domains"])[:6],
                    "sent": sent,
                    "delivered": bucket["delivered"],
                    "opened": bucket["opened"],
                    "bounced": bucket["bounced"],
                    "complained": bucket["complained"],
                    "delivery_rate": _rate(bucket["delivered"], sent),
                    "open_rate": open_rate,
                    "bounce_rate": bounce_rate,
                    "complaint_rate": complaint_rate,
                    "status": status,
                    "note": note,
                }
            )

        providers.sort(key=lambda item: -item["sent"])
        return {"period_days": period_days, "providers": providers}

    # ------------------------------------------------------------------ #
    # Incidents                                                          #
    # ------------------------------------------------------------------ #

    def incidents(self, db: Session, user_id: int, limit: int = 50) -> dict[str, Any]:
        """Recent deliverability incidents (bounces, complaints, suppressions, failures).

        @param db - Database session.
        @param user_id - Owner of the logs.
        @param limit - Max rows.
        @returns The incident journal, most recent first.
        """
        incident_statuses = (
            EmailStatus.BOUNCED.value,
            EmailStatus.COMPLAINED.value,
            EmailStatus.SUPPRESSED.value,
            EmailStatus.FAILED.value,
        )
        rows: list[EmailLog] = (
            db.query(EmailLog)
            .filter(
                EmailLog.user_id == user_id,
                or_(
                    EmailLog.status.in_(incident_statuses),
                    EmailLog.bounced_at.isnot(None),
                    EmailLog.complained_at.isnot(None),
                    EmailLog.suppressed_at.isnot(None),
                    EmailLog.failed_at.isnot(None),
                ),
            )
            .order_by(func.coalesce(
                EmailLog.bounced_at,
                EmailLog.complained_at,
                EmailLog.suppressed_at,
                EmailLog.failed_at,
                EmailLog.created_at,
            ).desc())
            .limit(limit)
            .all()
        )

        items: list[dict[str, Any]] = []
        for log in rows:
            if log.complained_at is not None or log.status == EmailStatus.COMPLAINED.value:
                kind, at = "complained", (log.complained_at or log.updated_at or log.created_at)
            elif log.bounced_at is not None or log.status == EmailStatus.BOUNCED.value:
                kind, at = "bounced", (log.bounced_at or log.updated_at or log.created_at)
            elif log.suppressed_at is not None or log.status == EmailStatus.SUPPRESSED.value:
                kind, at = "suppressed", (log.suppressed_at or log.updated_at or log.created_at)
            else:
                kind, at = "failed", (log.failed_at or log.updated_at or log.created_at)

            items.append(
                {
                    "id": log.id,
                    "kind": kind,
                    "recipient_email": log.recipient_email,
                    "subject": log.subject,
                    "campaign_id": log.campaign_id,
                    "error_message": log.error_message,
                    "at": at.isoformat() if at else None,
                }
            )

        return {"items": items}


email_health_service = EmailHealthService()
