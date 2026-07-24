"""
Email unsubscribe model for RGPD compliance.
"""

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.database import Base


class EmailUnsubscribe(Base):
    """
    Email unsubscribe model for tracking users who unsubscribed from emails.

    This is required for RGPD compliance. Users must be able to unsubscribe
    from email campaigns.

    Attributes:
        id: Unique identifier
        email: Email address that unsubscribed
        prospect_id: Optional prospect ID (if associated with a prospect)
        user_id: ID of the user who owned the prospect (for filtering)
        reason: Optional reason for unsubscribing
        created_at: Timestamp when unsubscribed
    """

    __tablename__ = "email_unsubscribes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    prospect_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        """String representation of the unsubscribe."""
        return f"<EmailUnsubscribe email={self.email}>"
