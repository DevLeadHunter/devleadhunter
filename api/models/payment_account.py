"""Payment account model — a user's connected sales-encashment provider.

One row per user (at most one active provider). Holds the encrypted
credentials for whichever provider the user connected, plus the environment
tag that keeps sandbox and production strictly separated.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from enums.payment_provider import PaymentEnvironment

if TYPE_CHECKING:
    from models.user import User


class PaymentAccount(Base):
    """A user's connected encashment provider (Qonto or Stripe).

    Secrets (OAuth tokens, API key) are stored encrypted via
    ``encryption_service`` — the same treatment as Gmail OAuth tokens on
    ``EmailAccount``. The ``environment`` column records which provider
    environment the credentials were minted against.

    Attributes:
        user_id: Owner of the account (unique — one provider per user).
        provider: Connected provider (``qonto`` | ``stripe``).
        environment: Environment the credentials belong to (``sandbox`` |
            ``production``), guarding against cross-environment use.
        is_connected: Whether the connection completed and is usable.
        display_name: Human label shown in the UI (org name / business name).
        qonto_access_token: Encrypted Qonto OAuth access token.
        qonto_refresh_token: Encrypted Qonto OAuth refresh token (rotates on
            every refresh — one-time use, always re-persisted).
        qonto_token_expires_at: Access-token expiry (access token lives 1h).
        qonto_api_login: Encrypted Qonto API-key login (Léo-only fallback).
        qonto_api_secret: Encrypted Qonto API-key secret (Léo-only fallback).
        qonto_iban: IBAN printed on invoices — captured manually because the
            ``organization.read`` scope is deliberately not requested.
        stripe_account_id: Connected account id (``acct_...``).
        stripe_charges_enabled: Whether the connected account can be charged.
        stripe_details_submitted: Whether onboarding details were submitted.
    """

    __tablename__ = "payment_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    environment: Mapped[str] = mapped_column(String(20), nullable=False, default=PaymentEnvironment.SANDBOX.value)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Qonto OAuth (encrypted)
    qonto_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    qonto_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    qonto_token_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Qonto API-key fallback — admin-only, advanced settings (encrypted)
    qonto_api_login: Mapped[str | None] = mapped_column(Text, nullable=True)
    qonto_api_secret: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Qonto invoicing needs the IBAN, unreadable via API without organization.read
    qonto_iban: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Stripe Connect (Standard account, onboarded via Account Links)
    stripe_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_charges_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stripe_details_submitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=datetime.utcnow, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="payment_account")

    def __repr__(self) -> str:
        """String representation of the payment account."""
        return (
            f"<PaymentAccount id={self.id} user_id={self.user_id} "
            f"provider={self.provider} environment={self.environment} "
            f"connected={self.is_connected}>"
        )
