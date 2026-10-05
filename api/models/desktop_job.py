"""Desktop job — work a device without the desktop app leaves for the owner's computer, which does it in the background."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.clock import naive_utc_now
from core.database import UTF8MB4_TABLE_OPTIONS, Base
from enums.desktop_job import DesktopJobStatus


class DesktopJob(Base):
    """
    One piece of work only the desktop app can do, asked from another device.

    Attributes:
        id: Unique identifier
        user_id: Owner, whose desktop app does the work
        kind: What to do (see ``DesktopJobKind``)
        subject_id: The prospect, site or other record the work is about
        payload: What the desktop app needs to do the work, when the subject is not enough
        status: Lifecycle state
        error_message: Why the desktop app gave up
        requested_at: When the work was asked (naive UTC)
        claimed_at: When a desktop app took it (naive UTC)
        finished_at: When it ended, done, failed or cancelled (naive UTC)
    """

    __tablename__ = "desktop_jobs"
    __table_args__ = (UTF8MB4_TABLE_OPTIONS,)

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    subject_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=DesktopJobStatus.WAITING.value, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(default=naive_utc_now, nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
