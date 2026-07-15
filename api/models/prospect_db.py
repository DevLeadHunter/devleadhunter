"""
Prospect database model for SQLAlchemy.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List
from sqlalchemy import String, Integer, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base

if TYPE_CHECKING:
    from models.user import User
    from models.campaign import Campaign


class ProspectDB(Base):
    """
    Prospect database model for storing scraped business data.
    
    Attributes:
        id: Unique identifier (auto-increment)
        name: Business name
        address: Street address
        city: City name
        phone: Phone number
        email: Email address
        website: Website URL
        category: Business category
        source: Data source (google, pagesjaunes, etc.)
        confidence: Confidence score (1-4)
        user_id: ID of the user who saved this prospect
        created_at: Timestamp when prospect was created
        updated_at: Timestamp when prospect was last updated
    """
    __tablename__ = "prospects"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    category: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    contacted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0", index=True
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # Team sharing: set while the creator belongs to an organization → the prospect
    # is visible to every member. Cleared when the creator leaves the org.
    organization_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    # Reservation: one member "takes" the prospect; the others see it locked
    # (anti double-outreach — one prospect, one outreacher).
    reserved_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    reserved_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    # Lighthouse audit of the prospect's EXISTING website (PageSpeed Insights) —
    # feeds the "site améliorable → proposer une refonte" pitch.
    lighthouse_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    lighthouse_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now(), nullable=True)
    
    # Relationships
    campaigns: Mapped[list["Campaign"]] = relationship(
        "Campaign",
        secondary="campaign_prospects",
        back_populates="prospects"
    )
    
    def __repr__(self) -> str:
        """String representation of the prospect."""
        return f"<ProspectDB(id={self.id}, name='{self.name}', city='{self.city}', source='{self.source}')>"

