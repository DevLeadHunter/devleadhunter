"""
Support message model.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base

if TYPE_CHECKING:
    from models.user import User
    from models.support_ticket import SupportTicket
    from models.support_attachment import SupportAttachment


class SupportMessage(Base):
    """
    Single message within a support ticket conversation.
    """

    __tablename__ = "support_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support_tickets.id"), nullable=False, index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    sender_role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False, index=True)

    ticket: Mapped["SupportTicket"] = relationship(
        "SupportTicket",
        back_populates="messages",
    )
    sender: Mapped["User"] = relationship(
        "User",
        back_populates="support_messages",
        foreign_keys=[sender_id],
    )
    attachments: Mapped[list["SupportAttachment"]] = relationship(
        "SupportAttachment",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="SupportAttachment.created_at",
    )

    def __repr__(self) -> str:
        """Readable representation."""
        return (
            f"<SupportMessage id={self.id} ticket_id={self.ticket_id} "
            f"sender_id={self.sender_id}>"
        )


