"""
Campaign model for email campaign management.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

if TYPE_CHECKING:
    from models.campaign_follow_up import CampaignFollowUp
    from models.email_log import EmailLog
    from models.prospect_db import ProspectDB
    from models.user import User


class CampaignStatus(enum.Enum):
    """Campaign status enumeration."""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


# Association table for many-to-many relationship between campaigns and prospects
campaign_prospects = Table(
    "campaign_prospects",
    Base.metadata,
    Column("campaign_id", Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True),
    Column("prospect_id", Integer, ForeignKey("prospects.id", ondelete="CASCADE"), primary_key=True),
    Column("added_at", DateTime, nullable=False, default=datetime.utcnow),
    # Explicit send order within the campaign (0-based, set from the order prospects are added).
    # The queue pairs ascending time-slots to prospects in this order, so with max_emails_per_day=1
    # the operator fully controls which group goes on which day (1 métier/jour). Bulk inserts share
    # the same ``added_at`` second, so ``added_at`` alone can't order them — hence this column.
    Column("position", Integer, nullable=False, server_default="0"),
)


class Campaign(Base):
    """
    Campaign model for organizing prospects and email campaigns.

    Attributes:
        id: Unique identifier
        user_id: ID of the user who owns this campaign
        name: Campaign name
        description: Campaign description
        status: Campaign status (draft, active, completed, paused, cancelled)
        created_at: Timestamp when campaign was created
        updated_at: Timestamp when campaign was last updated
        prospects: List of prospects in this campaign (many-to-many)
        email_logs: List of email logs associated with this campaign
    """

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        SQLEnum(CampaignStatus), default=CampaignStatus.DRAFT.value, nullable=False, index=True
    )
    # Send channel: "email" (default, email templates via Resend) or "sms" (cold SMS via smsmode).
    # SMS campaigns reuse the exact same queue + SendPolicy scheduling; only enqueue/dispatch branch.
    channel: Mapped[str] = mapped_column(String(10), default="email", nullable=False)
    # SMS campaigns only: the first-contact library template rendered at send time. NULL = the default
    # first-contact template. (Email campaigns use ``template_id``/``ab_template_id_b`` instead.)
    sms_template_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Campaign configuration — stored here so the detail page can edit anytime.
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True
    )
    email_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_accounts.id", ondelete="SET NULL"), nullable=True
    )
    # A/B testing: template_id = variant A, ab_template_id_b = variant B
    ab_template_id_b: Mapped[int | None] = mapped_column(
        ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True
    )
    # Legacy single-follow-up fields (kept for backward compat, superseded by campaign_follow_ups)
    follow_up_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True
    )
    follow_up_delay_days: Mapped[int] = mapped_column(default=5, nullable=False)
    send_delay_minutes: Mapped[int] = mapped_column(default=20, nullable=False)
    # When True, follow-up emails are personalized from the prospect's demo
    # behaviour (PostHog) at send time, falling back to the static template.
    behavior_personalized_followups: Mapped[bool] = mapped_column(default=False, nullable=False)
    # When False, the campaign never attaches the prospection video: {vignette_video}
    # renders empty and combo templates fall back to their demo link. Default on.
    include_video: Mapped[bool] = mapped_column(default=True, nullable=False)
    # Per-campaign daily cap for J1 sends; None = no per-campaign limit (the global
    # SendPolicy cap still applies). Set to 1 to send one métier per day.
    max_emails_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.utcnow, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="campaigns")
    # Ordered by the association's ``added_at`` so enqueue is deterministic: the send queue pairs
    # ascending slots to this list in order, so "prospect added first → sent first". Combined with
    # ``max_emails_per_day=1`` this yields a controlled one-group-per-day sequence (1 métier/jour).
    prospects: Mapped[list["ProspectDB"]] = relationship(
        "ProspectDB",
        secondary=campaign_prospects,
        back_populates="campaigns",
        order_by=(campaign_prospects.c.position, campaign_prospects.c.added_at, campaign_prospects.c.prospect_id),
    )
    email_logs: Mapped[list["EmailLog"]] = relationship(
        "EmailLog", back_populates="campaign", cascade="all, delete-orphan"
    )
    follow_ups: Mapped[list["CampaignFollowUp"]] = relationship(
        "CampaignFollowUp",
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="CampaignFollowUp.position",
    )

    def __repr__(self) -> str:
        """String representation of the campaign."""
        return f"<Campaign id={self.id} name={self.name} status={self.status}>"
