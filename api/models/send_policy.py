"""
SendPolicy model — the user's global cold-email sending policy.

One row per user. Governs the WHOLE email queue (automatisations + manual
campaigns): the daily volume cap, which weekdays and hours emails may go out,
and the minimum spacing between two sends. Defaults encode the anti-spam
baseline: 20 mails/day, Mon–Fri, 07:00–18:00, one every 20 minutes.
"""

from datetime import datetime

from sqlalchemy import JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.database import Base

#: Default weekdays (0 = Monday … 6 = Sunday) → Monday through Friday.
DEFAULT_DAYS_OF_WEEK: list[int] = [0, 1, 2, 3, 4]
DEFAULT_DAILY_CAP: int = 20
DEFAULT_WINDOW_START_HOUR: int = 7
DEFAULT_WINDOW_END_HOUR: int = 18
DEFAULT_SPACING_MINUTES: int = 20


class SendPolicy(Base):
    """Per-user cold-email cadence policy."""

    __tablename__ = "send_policies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    daily_cap: Mapped[int] = mapped_column(Integer, nullable=False, default=DEFAULT_DAILY_CAP, server_default="20")
    # Weekdays allowed (0 = Monday … 6 = Sunday).
    days_of_week: Mapped[list | None] = mapped_column(JSON, nullable=True)
    window_start_hour: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_WINDOW_START_HOUR, server_default="7"
    )
    window_end_hour: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_WINDOW_END_HOUR, server_default="18"
    )
    spacing_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=DEFAULT_SPACING_MINUTES, server_default="20"
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now(), nullable=True)

    def __repr__(self) -> str:
        """String representation of the policy."""
        return f"<SendPolicy user={self.user_id} cap={self.daily_cap}/day>"
