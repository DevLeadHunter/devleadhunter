"""
Email log model for tracking sent emails.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from enums.email_status import EmailStatus

if TYPE_CHECKING:
    from models.campaign import Campaign
    from models.email_account import EmailAccount
    from models.email_reply import EmailReply
    from models.user import User


class EmailLog(Base):
    """
    Email log model for tracking all sent emails.

    Attributes:
        id: Unique identifier
        user_id: Foreign key to user
        email_account_id: Foreign key to email account used
        prospect_id: ID of the prospect (from prospects table)
        campaign_id: Foreign key to campaign (optional)

        recipient_email: Recipient email address
        recipient_name: Recipient name (optional)
        subject: Email subject
        body_html: Email body HTML

        status: Email status (pending, sent, delivered, etc.)
        provider: Email provider used (resend, gmail)
        provider_message_id: Message ID from provider

        sent_at: Timestamp when email was sent
        delivered_at: Timestamp when email was delivered
        opened_at: Timestamp of the first HUMAN open (machine prefetch excluded)
        machine_opened_at: Timestamp of the delivery-time pixel prefetch (Gmail/scanner), not a human read
        open_count: Number of HUMAN opens (reopens included)
        last_open_at: Timestamp of the most recent HUMAN open
        clicked_at: Timestamp when email links were clicked
        replied_at: Timestamp of the first captured prospect reply
        bounced_at: Timestamp when email bounced
        failed_at: Timestamp when email failed

        error_message: Error message if sending failed
        extra_metadata: JSON string for additional metadata

        created_at: Timestamp when log was created
        updated_at: Timestamp when log was last updated
    """

    __tablename__ = "email_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    email_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )

    prospect_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    campaign_id: Mapped[int | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True
    )

    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    recipient_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(String(50), default=EmailStatus.PENDING.value, nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # opened_at = first HUMAN open; a delivery-time prefetch is recorded on machine_opened_at instead.
    opened_at: Mapped[datetime | None] = mapped_column(nullable=True)
    machine_opened_at: Mapped[datetime | None] = mapped_column(nullable=True)
    open_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_open_at: Mapped[datetime | None] = mapped_column(nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # replied_at = first prospect reply captured via the reply-capture inbound domain.
    replied_at: Mapped[datetime | None] = mapped_column(nullable=True)
    bounced_at: Mapped[datetime | None] = mapped_column(nullable=True)
    complained_at: Mapped[datetime | None] = mapped_column(nullable=True)
    suppressed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # A/B variant ('A' or 'B') — populated from the queue item at send time.
    ab_variant: Mapped[str | None] = mapped_column(String(1), nullable=True)

    # Direct answer to a prospect's reply (threaded conversation, not outreach) —
    # excluded from the outreach funnel stats.
    is_conversation_reply: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.utcnow, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="email_logs")
    email_account: Mapped["EmailAccount"] = relationship("EmailAccount", back_populates="email_logs")
    campaign: Mapped[Optional["Campaign"]] = relationship("Campaign", back_populates="email_logs")
    replies: Mapped[list["EmailReply"]] = relationship(
        "EmailReply", back_populates="email_log", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of the email log."""
        return f"<EmailLog id={self.id} to={self.recipient_email} status={self.status}>"
