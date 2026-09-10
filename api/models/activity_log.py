"""Append-only activity log — one row per meaningful action in the software.

This is the audit feed behind the admin monitoring page: every email, SMS, demo
visit, sale, scraping run, prospect/site/campaign change and server error writes
one row here. It is deliberately generic (category + action + status + a human
title) so any new event source records without a schema change. Writes are
best-effort and must never break the action they describe (see
:mod:`services.activity_log_service`).
"""

from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ActivityLog(Base):
    """One recorded action in the activity feed.

    Attributes:
        id: Unique identifier (auto-increment).
        user_id: Owner of the action (``None`` for a system/background event).
        category: Domain of the action (``email``, ``sms``, ``demo``, ``sale``,
            ``prospect``, ``demo_site``, ``campaign``, ``scraping``, ``auth``,
            ``system``…) — drives the category filter.
        action: Precise event name (e.g. ``sms.sent``, ``email.delivered``,
            ``prospect.created``).
        status: Outcome level (``success`` / ``error`` / ``warning`` / ``pending``
            / ``info``) — drives the status filter and the badge colour.
        title: Human one-line summary shown in the feed.
        detail: Optional longer context (error reason, subject, target host…).
        entity_type: Kind of the linked resource (``prospect``, ``demo_site``,
            ``order``, ``campaign``, ``scraper_diagnostic``…), for a deep link.
        entity_id: Id of the linked resource, when there is one.
        created_at: When the action happened.
    """

    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="info", index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False, index=True)
