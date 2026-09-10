"""
Notification model — a persisted in-app notification (log journal) for a user.

Every notification the app raises is stored here (attributed to a user), whether
or not the Web Push actually reaches a device — so the settings page can show a
complete, scrollable history and nothing is ever missed. Kept ~90 days.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Notification(Base):
    """
    A stored in-app notification for a user (persisted even when no push is sent).

    Attributes:
        id: Primary key.
        user_id: Owner of the notification.
        category: Domain — email / demo / sale / system / recap.
        level: Visual level — info / success / warning / error.
        title: Notification title (emoji + prospect, or a label).
        body: Notification body (the action / detail).
        url: In-app deep link opened on click.
        read_at: When the user read it (NULL = unread).
        created_at: Creation timestamp.
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    level: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    url: Mapped[str] = mapped_column(String(500), nullable=False, default="/dashboard")
    read_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User")

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user_id={self.user_id} category={self.category}>"
