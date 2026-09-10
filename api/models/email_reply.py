"""
Email reply model — a prospect's reply captured via the Resend inbound domain.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

if TYPE_CHECKING:
    from models.email_log import EmailLog


class EmailReply(Base):
    """
    A reply received on the reply-capture domain, linked back to the send it answers.

    Attributes:
        id: Unique identifier
        email_log_id: The outbound email this reply answers
        user_id: Owner of the original send (denormalized for fast per-user queries)
        prospect_id: Prospect who replied (denormalized from the email log)
        from_email: Bare sender address of the reply
        subject: Reply subject line
        body_text: Plain-text body (fetched from the Resend Receiving API)
        body_html: HTML body (fetched from the Resend Receiving API)
        resend_email_id: Resend received-email id — unique, makes webhook retries idempotent
        message_id: RFC 5322 Message-ID of the reply
        matched_by: How the reply was linked to the send (``token`` | ``from``)
        is_auto_reply: Out-of-office / autoresponder — stored but never notified
        received_at: When Resend received the reply
        created_at: Row creation timestamp
    """

    __tablename__ = "email_replies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email_log_id: Mapped[int] = mapped_column(
        ForeignKey("email_logs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    prospect_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    from_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)

    resend_email_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    matched_by: Mapped[str] = mapped_column(String(20), nullable=False)
    is_auto_reply: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    received_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # When the user dealt with the reply (answered from the app or marked handled).
    # A human reply with handled_at IS NULL is « à traiter ».
    handled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # When a readable copy was forwarded to the user's inbox (Gmail POP, etc.).
    inbox_forwarded_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # LLM verdict on what the prospect meant (interested / not_interested / later /
    # question / unsubscribe / other). Classified once, persisted forever.
    intent: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # SHA-256 of the classified text — identical content reuses the stored verdict.
    content_sha: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)

    email_log: Mapped["EmailLog"] = relationship("EmailLog", back_populates="replies")

    def __repr__(self) -> str:
        """String representation of the reply."""
        return f"<EmailReply id={self.id} log={self.email_log_id} from={self.from_email!r}>"
