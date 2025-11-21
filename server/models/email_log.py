"""
Email log model for tracking sent emails.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from enums.email_status import EmailStatus

if TYPE_CHECKING:
    from models.user import User
    from models.email_account import EmailAccount
    from models.campaign import Campaign


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
        provider: Email provider used (mailjet, gmail)
        provider_message_id: Message ID from provider
        
        sent_at: Timestamp when email was sent
        delivered_at: Timestamp when email was delivered
        opened_at: Timestamp when email was opened
        clicked_at: Timestamp when email links were clicked
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
    email_account_id: Mapped[int] = mapped_column(
        ForeignKey("email_accounts.id"),
        nullable=False,
        index=True
    )
    
    prospect_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    recipient_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    
    status: Mapped[str] = mapped_column(
        String(50),
        default=EmailStatus.PENDING.value,
        nullable=False,
        index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    sent_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    opened_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    clicked_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    bounced_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now(), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="email_logs")
    email_account: Mapped["EmailAccount"] = relationship(
        "EmailAccount",
        back_populates="email_logs"
    )
    campaign: Mapped[Optional["Campaign"]] = relationship(
        "Campaign",
        back_populates="email_logs"
    )
    
    def __repr__(self) -> str:
        """String representation of the email log."""
        return f"<EmailLog id={self.id} to={self.recipient_email} status={self.status}>"

