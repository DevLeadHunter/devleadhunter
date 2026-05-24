"""
Support ticket model.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from enums.support_status import SupportTicketStatus
from enums.support_topic import SupportTicketTopic

if TYPE_CHECKING:
    from models.user import User
    from models.support_message import SupportMessage
    from models.support_attachment import SupportAttachment


class SupportTicket(Base):
    """
    Support ticket entity representing a support request initiated by a user.
    """

    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    assigned_admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    topic: Mapped[str] = mapped_column(String(64), default=SupportTicketTopic.OTHER.value, nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=SupportTicketStatus.OPEN.value, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now(), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_message_at: Mapped[Optional[datetime]] = mapped_column(nullable=True, index=True)

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="support_tickets",
    )
    assigned_admin: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[assigned_admin_id],
        back_populates="assigned_support_tickets",
    )
    messages: Mapped[list["SupportMessage"]] = relationship(
        "SupportMessage",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="SupportMessage.created_at",
    )
    attachments: Mapped[list["SupportAttachment"]] = relationship(
        "SupportAttachment",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="SupportAttachment.created_at",
    )

    def __repr__(self) -> str:
        """Readable representation."""
        return (
            f"<SupportTicket id={self.id} subject={self.subject!r} "
            f"status={self.status} user_id={self.user_id}>"
        )


