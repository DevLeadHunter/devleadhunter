"""
Sending identity resolution — the single source of truth for *how* a user
sends outreach.

A user has exactly one active sending identity, selected by
``users.sending_provider`` (``resend`` | ``gmail``). This module resolves that
choice into a concrete :class:`SendingIdentity` (address + credentials) that
``EmailSendingService`` uses to dispatch, and exposes read/write helpers used by
the settings routes.

Keeping this logic in one place means every send path (campaign queue,
follow-ups, orders, quick-send) routes through the same provider decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from enums.email_account_type import EmailAccountType
from enums.sending_provider import SendingProvider
from models.email_account import EmailAccount
from models.resend_config import ResendConfig
from models.user import User
from services.encryption_service import encryption_service

_VALID_PROVIDERS: set[str] = {SendingProvider.RESEND.value, SendingProvider.GMAIL.value}


class SendingNotConfiguredError(Exception):
    """Raised when the user's active sending provider is not usable yet.

    The message is user-facing (French) and safe to surface as an HTTP 422.
    """


@dataclass
class SendingIdentity:
    """A resolved, ready-to-use sending identity for a single user.

    Attributes:
        provider:       ``resend`` or ``gmail``.
        from_email:     Sender address shown to the recipient.
        from_name:      Sender display name (may be empty).
        resend_api_key: Decrypted Resend API key — set only for the Resend provider.
        gmail_account:  The Gmail ``EmailAccount`` to send through — set only for Gmail.
    """

    provider: str
    from_email: str
    from_name: str
    resend_api_key: Optional[str] = None
    gmail_account: Optional[EmailAccount] = None


def get_active_provider(db: Session, user_id: int) -> str:
    """Return the user's active sending provider, defaulting to ``resend``.

    Args:
        db: Database session.
        user_id: Owner of the sending identity.

    Returns:
        One of the :class:`SendingProvider` values.
    """
    user: User | None = db.get(User, user_id)
    raw: str = (getattr(user, "sending_provider", None) or SendingProvider.RESEND.value)
    return raw if raw in _VALID_PROVIDERS else SendingProvider.RESEND.value


def set_active_provider(db: Session, user_id: int, provider: str) -> None:
    """Persist the user's active sending provider.

    Args:
        db: Database session.
        user_id: Owner of the sending identity.
        provider: Target provider (``resend`` | ``gmail``).
    @raises ValueError - When *provider* is not a valid provider value.
    @raises SendingNotConfiguredError - When the chosen provider is not configured yet.
    """
    if provider not in _VALID_PROVIDERS:
        raise ValueError(f"Fournisseur d'envoi invalide : {provider!r}")
    user: User | None = db.get(User, user_id)
    if user is None:
        raise ValueError("Utilisateur introuvable")
    # Guard: never switch onto a provider the user cannot actually send with.
    _assert_provider_configured(db, user_id, provider)
    user.sending_provider = provider
    db.commit()


def _default_gmail_account(db: Session, user_id: int) -> EmailAccount | None:
    """Return the Gmail account to send through, preferring the default one.

    Picks the user's active Gmail OAuth account, favouring ``is_default`` then
    the most recently created.

    Args:
        db: Database session.
        user_id: Owner of the account.

    Returns:
        The chosen :class:`EmailAccount`, or ``None`` when none exists.
    """
    return db.execute(
        select(EmailAccount)
        .where(
            EmailAccount.user_id == user_id,
            EmailAccount.account_type == EmailAccountType.GMAIL_OAUTH.value,
            EmailAccount.is_active.is_(True),
        )
        .order_by(EmailAccount.is_default.desc(), EmailAccount.id.desc())
    ).scalars().first()


def _resend_config(db: Session, user_id: int) -> ResendConfig | None:
    """Return the user's ResendConfig row, or ``None`` when absent."""
    return db.execute(
        select(ResendConfig).where(ResendConfig.user_id == user_id)
    ).scalar_one_or_none()


def _assert_provider_configured(db: Session, user_id: int, provider: str) -> None:
    """Raise :class:`SendingNotConfiguredError` if *provider* is not usable."""
    if provider == SendingProvider.GMAIL.value:
        if _default_gmail_account(db, user_id) is None:
            raise SendingNotConfiguredError(
                "Aucun compte Gmail connecté — Paramètres → Configuration d'envoi"
            )
        return
    config = _resend_config(db, user_id)
    if config is None or not config.api_key:
        raise SendingNotConfiguredError(
            "Resend non configuré — Paramètres → Configuration d'envoi"
        )


def resolve_sending_identity(db: Session, user_id: int) -> SendingIdentity:
    """Resolve the user's active sending identity into concrete credentials.

    Args:
        db: Database session.
        user_id: Owner of the sending identity.

    Returns:
        A ready-to-use :class:`SendingIdentity`.
    @raises SendingNotConfiguredError - When the active provider is not configured.
    """
    provider: str = get_active_provider(db, user_id)

    if provider == SendingProvider.GMAIL.value:
        account = _default_gmail_account(db, user_id)
        if account is None:
            raise SendingNotConfiguredError(
                "Aucun compte Gmail connecté — Paramètres → Configuration d'envoi"
            )
        return SendingIdentity(
            provider=SendingProvider.GMAIL.value,
            from_email=account.email,
            from_name=account.name,
            gmail_account=account,
        )

    # Default: Resend (covers plain Resend and custom-domain-on-Resend).
    config = _resend_config(db, user_id)
    if config is None or not config.api_key:
        raise SendingNotConfiguredError(
            "Resend non configuré — Paramètres → Configuration d'envoi"
        )
    return SendingIdentity(
        provider=SendingProvider.RESEND.value,
        from_email=config.from_email,
        from_name=config.from_name or "",
        resend_api_key=encryption_service.decrypt(config.api_key),
    )


def describe_sending_config(db: Session, user_id: int) -> dict[str, object]:
    """Summarise the user's sending setup for the settings UI (no secrets).

    Args:
        db: Database session.
        user_id: Owner of the sending identity.

    Returns:
        A dict with the active provider and per-provider readiness flags.
    """
    config = _resend_config(db, user_id)
    gmail = _default_gmail_account(db, user_id)
    return {
        "provider": get_active_provider(db, user_id),
        "resend_configured": config is not None and bool(config.api_key),
        "resend_from_email": config.from_email if config else None,
        "gmail_configured": gmail is not None,
        "gmail_email": gmail.email if gmail else None,
    }
