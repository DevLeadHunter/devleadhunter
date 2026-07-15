"""
Support attachment model.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base

if TYPE_CHECKING:
    from models.support_ticket import SupportTicket
    from models.support_message import SupportMessage


class SupportAttachment(Base):
    """
    Persisted file linked to a support ticket and optionally to a specific message.
    """

    __tablename__ = "support_attachments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("support_tickets.id"), nullable=False, index=True)
    message_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("support_messages.id"),
        nullable=True,
        index=True,
    )
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(32), nullable=False, default="local")
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False, index=True)

    ticket: Mapped["SupportTicket"] = relationship(
        "SupportTicket",
        back_populates="attachments",
    )
    message: Mapped[Optional["SupportMessage"]] = relationship(
        "SupportMessage",
        back_populates="attachments",
    )

    def __repr__(self) -> str:
        return (
            f"<SupportAttachment id={self.id} ticket_id={self.ticket_id} "
            f"message_id={self.message_id} object_key={self.object_key!r}>"
        )


