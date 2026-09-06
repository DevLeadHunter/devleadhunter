"""
User model for authentication and authorization.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base
from enums.sending_provider import SendingProvider
from enums.user_role import UserRole

if TYPE_CHECKING:
    from models.campaign import Campaign
    from models.credit_transaction import CreditTransaction
    from models.demo_site import DemoSite
    from models.email_account import EmailAccount
    from models.email_log import EmailLog
    from models.email_signature import EmailSignature
    from models.email_template import EmailTemplate
    from models.payment_account import PaymentAccount
    from models.support_message import SupportMessage
    from models.support_ticket import SupportTicket


class User(Base):
    """
    User model for authentication and authorization.

    Attributes:
        id: Unique identifier
        name: User's full name
        email: User's email address (unique)
        hashed_password: Hashed password
        role: User role (USER, ADMIN or SUPER_ADMIN)
        company_name: Optional business name shown in outreach / AI prompts
        is_active: Whether the user is active
        sending_provider: Active email-sending transport (resend | gmail)
        onboarding_completed: Whether the setup wizard has been completed
        site_sale_price_cents: Website sale price in cents (default 500 €)
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
        credit_transactions: Relationship to credit transactions
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default=UserRole.USER.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    # Active email-sending transport (resend | gmail). One identity per user.
    sending_provider: Mapped[str] = mapped_column(String(20), default=SendingProvider.RESEND.value, nullable=False)
    # Whether the post-signup setup wizard (/configuration) has been completed.
    onboarding_completed: Mapped[bool] = mapped_column(default=False, nullable=False)
    # Website sale price in cents (default 500 €): per-user default for {prix},
    # new orders, and the sale drawer.
    site_sale_price_cents: Mapped[int] = mapped_column(default=50000, nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Optional public website of the user's business — linked from the prospection
    # video page signature (« Site réalisé par {company_name} »).
    company_website_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Gmail Postmaster Tools OAuth — per-user read access to Gmail-side reputation.
    postmaster_google_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    postmaster_oauth_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    postmaster_oauth_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    postmaster_oauth_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now(), nullable=True)

    # Relationship to credit transactions
    credit_transactions: Mapped[list["CreditTransaction"]] = relationship(
        "CreditTransaction", back_populates="user", cascade="all, delete-orphan"
    )
    support_tickets: Mapped[list["SupportTicket"]] = relationship(
        "SupportTicket", back_populates="user", cascade="all, delete-orphan", foreign_keys="SupportTicket.user_id"
    )
    assigned_support_tickets: Mapped[list["SupportTicket"]] = relationship(
        "SupportTicket", back_populates="assigned_admin", foreign_keys="SupportTicket.assigned_admin_id"
    )
    support_messages: Mapped[list["SupportMessage"]] = relationship(
        "SupportMessage", back_populates="sender", cascade="all, delete-orphan", foreign_keys="SupportMessage.sender_id"
    )
    email_accounts: Mapped[list["EmailAccount"]] = relationship(
        "EmailAccount", back_populates="user", cascade="all, delete-orphan"
    )
    email_templates: Mapped[list["EmailTemplate"]] = relationship(
        "EmailTemplate", back_populates="user", cascade="all, delete-orphan"
    )
    email_signatures: Mapped[list["EmailSignature"]] = relationship(
        "EmailSignature", back_populates="user", cascade="all, delete-orphan"
    )
    email_logs: Mapped[list["EmailLog"]] = relationship("EmailLog", back_populates="user", cascade="all, delete-orphan")
    campaigns: Mapped[list["Campaign"]] = relationship("Campaign", back_populates="user", cascade="all, delete-orphan")
    demo_sites: Mapped[list["DemoSite"]] = relationship(
        "DemoSite",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    # At most one connected encashment provider (Qonto or Stripe) per user.
    payment_account: Mapped["PaymentAccount | None"] = relationship(
        "PaymentAccount", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<User id={self.id} name={self.name} email={self.email} role={self.role}>"
