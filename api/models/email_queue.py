"""
EmailQueue model — drives the rate-limited cold-email send queue.

Each row represents one email to dispatch (initial J1 or follow-up J+N).
A background worker processes ``pending`` rows in ``scheduled_at`` order,
respecting the per-campaign ``send_delay_minutes`` rate limit that is baked
into the row timestamps at enqueue time.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base

if TYPE_CHECKING:
    from models.campaign import Campaign
    from models.email_account import EmailAccount
    from models.email_log import EmailLog
    from models.email_template import EmailTemplate
    from models.prospect_db import ProspectDB
    from models.user import User


class EmailQueue(Base):
    """
    Queued email item for rate-limited cold outreach.

    Attributes:
        id:               Primary key.
        user_id:          Owning user (denormalised for fast per-user queries).
        campaign_id:      Parent campaign.
        prospect_id:      Target prospect.
        template_id:      Template to render when sending.
        email_account_id: Email account to send from.
        queue_type:       ``"initial"`` (J1) or ``"followup"`` (J+N relance).
        scheduled_at:     Earliest UTC time at which this item may be sent.
        email_log_id:     Populated once the email has been dispatched.
        status:           ``pending`` → ``sending`` → ``sent`` / ``skipped`` /
                          ``failed``.
        created_at:       Row creation timestamp.
        updated_at:       Last modification timestamp (auto-updated by DB).
    """

    __tablename__ = "email_queue"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prospect_id: Mapped[int] = mapped_column(
        ForeignKey("prospects.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id: Mapped[int] = mapped_column(
        ForeignKey("email_templates.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Nullable: campaigns now send via the user's ResendConfig, not an EmailAccount.
    email_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_accounts.id", ondelete="SET NULL"),
        nullable=True,
    )
    queue_type: Mapped[str] = mapped_column(String(20), nullable=False, default="initial")
    # A/B variant assigned at enqueue time: 'A', 'B', or None for non-A/B campaigns.
    ab_variant: Mapped[str | None] = mapped_column(String(1), nullable=True)
    # Follow-up sequence index: 0 = J1, 1 = first follow-up, 2 = second, etc.
    follow_up_index: Mapped[int] = mapped_column(nullable=False, default=0)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    email_log_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_logs.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now(), nullable=True)

    # Relationships — loaded lazily; the worker reads many rows per tick.
    user: Mapped[User] = relationship("User")
    campaign: Mapped[Campaign] = relationship("Campaign")
    prospect: Mapped[ProspectDB] = relationship("ProspectDB")
    template: Mapped[EmailTemplate] = relationship("EmailTemplate")
    email_account: Mapped[EmailAccount | None] = relationship("EmailAccount")
    email_log: Mapped[EmailLog | None] = relationship("EmailLog")

    def __repr__(self) -> str:
        return (
            f"<EmailQueue id={self.id} type={self.queue_type!r} "
            f"status={self.status!r} scheduled={self.scheduled_at.isoformat()}>"
        )
