"""Records and reads the activity log — the admin monitoring feed.

Every meaningful action funnels through :meth:`ActivityLogService.record`, which
opens its own short-lived session (callers rarely thread one through) and never
raises into the action it describes — exactly like the notification persist and
the scraper diagnostics writer. The admin monitoring page reads :meth:`recent`
(filtered by status / category / free text) and :meth:`categories`.

Category and status values are plain string constants so any new event source
records without a schema change; they double as the filter vocabulary.
"""

from __future__ import annotations

import logging
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from core.database import SessionLocal
from models.activity_log import ActivityLog

logger = logging.getLogger(__name__)

# Domains of the feed (the category filter vocabulary).
CATEGORY_EMAIL: str = "email"
CATEGORY_SMS: str = "sms"
CATEGORY_DEMO: str = "demo"
CATEGORY_SALE: str = "sale"
CATEGORY_PROSPECT: str = "prospect"
CATEGORY_DEMO_SITE: str = "demo_site"
CATEGORY_CAMPAIGN: str = "campaign"
CATEGORY_SCRAPING: str = "scraping"
CATEGORY_AUTH: str = "auth"
CATEGORY_SYSTEM: str = "system"

# Outcome levels (the status filter vocabulary + badge colours). Aligned with the
# notification levels so a notification's level maps straight onto a log status.
STATUS_SUCCESS: str = "success"
STATUS_ERROR: str = "error"
STATUS_WARNING: str = "warning"
STATUS_PENDING: str = "pending"
STATUS_INFO: str = "info"

# Feed retention — the log is high-volume, so it is pruned more aggressively than
# the notification history.
_RETENTION_DAYS: int = 60
# Prune runs on a small fraction of writes so a DELETE never rides every action.
_PRUNE_PROBABILITY: float = 0.02


class ActivityLogService:
    """Persist and read the append-only activity feed."""

    def record(
        self,
        *,
        category: str,
        action: str,
        title: str,
        status: str = STATUS_INFO,
        detail: str | None = None,
        user_id: int | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
    ) -> None:
        """Persist one action in the feed (best-effort — never raises).

        Opens its own session so callers do not have to thread one through.

        Args:
            category: Domain of the action (one of the ``CATEGORY_*`` constants).
            action: Precise event name (e.g. ``sms.sent``).
            title: Human one-line summary.
            status: Outcome level (one of the ``STATUS_*`` constants).
            detail: Optional longer context (error reason, subject, host…).
            user_id: Owner of the action (``None`` for a system/background event).
            entity_type: Kind of the linked resource, for a deep link.
            entity_id: Id of the linked resource, when there is one.
        """
        db = SessionLocal()
        try:
            row = ActivityLog(
                user_id=user_id,
                category=category,
                action=action[:64],
                status=status,
                title=title[:255],
                detail=(detail[:2000] if detail else None),
                entity_type=(entity_type[:32] if entity_type else None),
                entity_id=entity_id,
            )
            db.add(row)
            db.commit()
            if random.random() < _PRUNE_PROBABILITY:
                self._prune(db)
        except Exception as exc:
            logger.warning("Failed to record activity (%s/%s): %s", category, action, exc)
            db.rollback()
        finally:
            db.close()

    def _prune(self, db: Session) -> None:
        """Delete entries older than the retention window (keeps the table bounded)."""
        cutoff = datetime.now(UTC) - timedelta(days=_RETENTION_DAYS)
        try:
            db.query(ActivityLog).filter(ActivityLog.created_at < cutoff).delete(synchronize_session=False)
            db.commit()
        except Exception:
            db.rollback()

    def recent(
        self,
        db: Session,
        *,
        limit: int = 200,
        status: str | None = None,
        category: str | None = None,
        query: str | None = None,
    ) -> list[ActivityLog]:
        """Return the most recent entries, filtered by status / category / free text.

        Args:
            db: Active database session.
            limit: Maximum number of entries to return.
            status: Keep only this outcome level, when given.
            category: Keep only this domain, when given.
            query: Free-text match on title, detail or action (case-insensitive).

        Returns:
            The matching entries, newest first.
        """
        statement = db.query(ActivityLog)
        if status:
            statement = statement.filter(ActivityLog.status == status)
        if category:
            statement = statement.filter(ActivityLog.category == category)
        search = (query or "").strip()
        if search:
            pattern = f"%{search}%"
            statement = statement.filter(
                or_(
                    ActivityLog.title.ilike(pattern),
                    ActivityLog.detail.ilike(pattern),
                    ActivityLog.action.ilike(pattern),
                )
            )
        return statement.order_by(ActivityLog.created_at.desc()).limit(limit).all()

    def categories(self, db: Session) -> list[str]:
        """Return the distinct categories present in the feed (for the filter dropdown)."""
        rows = db.query(ActivityLog.category).distinct().all()
        return sorted(row[0] for row in rows if row[0])

    def total_count(self, db: Session) -> int:
        """Total number of stored activity entries."""
        return int(db.query(func.count(ActivityLog.id)).scalar() or 0)


activity_log_service = ActivityLogService()
