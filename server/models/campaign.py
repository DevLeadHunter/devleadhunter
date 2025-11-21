"""
Campaign model for email campaign management.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List
from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum, Table, Column, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum

from core.database import Base

if TYPE_CHECKING:
    from models.user import User
    from models.prospect_db import ProspectDB
    from models.email_log import EmailLog


class CampaignStatus(enum.Enum):
    """Campaign status enumeration."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


# Association table for many-to-many relationship between campaigns and prospects
campaign_prospects = Table(
    'campaign_prospects',
    Base.metadata,
    Column('campaign_id', Integer, ForeignKey('campaigns.id', ondelete='CASCADE'), primary_key=True),
    Column('prospect_id', Integer, ForeignKey('prospects.id', ondelete='CASCADE'), primary_key=True),
    Column('added_at', DateTime, nullable=False, server_default=func.now())
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
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        SQLEnum(CampaignStatus),
        default=CampaignStatus.DRAFT.value,
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now(), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="campaigns")
    prospects: Mapped[List["ProspectDB"]] = relationship(
        "ProspectDB",
        secondary=campaign_prospects,
        back_populates="campaigns"
    )
    email_logs: Mapped[List["EmailLog"]] = relationship(
        "EmailLog",
        back_populates="campaign",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        """String representation of the campaign."""
        return f"<Campaign id={self.id} name={self.name} status={self.status}>"

