"""
Campaign model for email campaign management.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

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
    Column("added_at", DateTime, nullable=False, server_default=func.now()),
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
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now(), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="campaigns")
    prospects: Mapped[list["ProspectDB"]] = relationship(
        "ProspectDB", secondary=campaign_prospects, back_populates="campaigns"
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
