"""
PushSubscription model — a browser Web Push endpoint registered for a user.

One row per browser / PWA install. Used to deliver mobile notifications to the
dashboard user (email, demo and sale events). Registered via the /notifications API.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class PushSubscription(Base):
    """
    A browser Web Push subscription used to notify a user on their mobile PWA.

    Attributes:
        id:          Primary key.
        user_id:     Owner of the subscription.
        endpoint:    Push service endpoint URL (unique per browser install).
        p256dh:      Client public key for payload encryption.
        auth:        Client auth secret for payload encryption.
        user_agent:  Optional device hint shown in the settings UI.
        created_at:  Row creation timestamp.
    """

    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    endpoint: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    p256dh: Mapped[str] = mapped_column(String(255), nullable=False)
    auth: Mapped[str] = mapped_column(String(255), nullable=False)
    user_agent: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    user = relationship("User")

    def __repr__(self) -> str:
        return f"<PushSubscription id={self.id} user_id={self.user_id}>"
