"""Planned automated SMS — one row per scheduled send, with its exact slot.

The automations used to pick candidates live on each worker pass, so the forecast
could only estimate times. Rows here ARE the schedule: the planner materialises every
upcoming relance J+30 / cold SMS with an exact ``scheduled_at``, the worker sends what
is due, and the operator can cancel or reschedule any pending row from the forecast.
"""

from datetime import datetime

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class SmsAutoQueue(Base):
    """One planned automated SMS (relance J+30 or cold first contact).

    Attributes:
        id: Unique identifier (auto-increment)
        user_id: Owner of the automation
        prospect_id: Recipient prospect
        demo_site_id: Demo attached at planning time (display convenience)
        kind: ``relance`` (J+30 after an unanswered email) or ``cold`` (first touch)
        status: ``pending`` / ``sent`` / ``cancelled`` / ``skipped``
        scheduled_at: Exact planned send time (naive UTC)
        emailed_at: First-email date anchoring a relance (``None`` for cold)
        skip_reason: Why a row was skipped (eligibility lost, send failure…)
        sent_at: When the SMS actually went out
        created_at: When the row was planned
        updated_at: Last status/schedule change
    """

    __tablename__ = "sms_auto_queue"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    prospect_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    demo_site_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # The per-user « Relances SMS J+30 » system campaign a relance row belongs to (NULL for cold).
    campaign_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending", index=True)
    scheduled_at: Mapped[datetime] = mapped_column(nullable=False, index=True)
    emailed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    skip_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # UTC (Python-side), like the SMS log — the MySQL clock is not UTC in prod.
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.utcnow, nullable=True)
