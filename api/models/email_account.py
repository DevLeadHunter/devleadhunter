"""
Email account model for storing user's email sender configurations.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base

if TYPE_CHECKING:
    from models.email_log import EmailLog
    from models.email_template import EmailTemplate
    from models.user import User


class EmailAccount(Base):
    """
    Email account model for storing sender configurations.

    Attributes:
        id: Unique identifier
        user_id: Foreign key to user
        account_type: Type of email account (custom_domain or gmail_oauth)
        email: Email address
        name: Sender name
        is_verified: Whether DNS records are verified (for custom domain)
        is_default: Whether this is the default sender account

        # For custom domain
        domain: Domain name (for custom domain)
        spf_verified: Whether SPF record is verified
        dkim_verified: Whether DKIM record is verified

        # For Gmail OAuth
        oauth_access_token: Encrypted OAuth access token
        oauth_refresh_token: Encrypted OAuth refresh token
        oauth_token_expires_at: Token expiration timestamp

        is_active: Whether the account is active
        created_at: Timestamp when account was created
        updated_at: Timestamp when account was last updated
    """

    __tablename__ = "email_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Custom domain fields
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    spf_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dkim_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Gmail OAuth fields (encrypted in production)
    oauth_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    oauth_token_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now(), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="email_accounts")
    email_templates: Mapped[list["EmailTemplate"]] = relationship(
        "EmailTemplate", back_populates="email_account", cascade="all, delete-orphan"
    )
    email_logs: Mapped[list["EmailLog"]] = relationship(
        "EmailLog", back_populates="email_account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """String representation of the email account."""
        return f"<EmailAccount id={self.id} email={self.email} type={self.account_type}>"
