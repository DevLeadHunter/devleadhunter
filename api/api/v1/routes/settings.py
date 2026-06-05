"""
Settings routes — per-user application settings.

Currently exposes Resend email configuration (GET + PUT).
The API key and webhook secret are encrypted at rest and never returned
in plain text to the frontend.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_db
from models.resend_config import ResendConfig
from models.user import User
from services.auth_service import get_current_user
from services.encryption_service import encryption_service

router = APIRouter(prefix="/settings", tags=["settings"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic schemas (local — only used by this module)
# ---------------------------------------------------------------------------


class ResendConfigUpdate(BaseModel):
    """Payload for creating or updating the user's Resend configuration."""

    api_key: str
    """Resend API key (``re_…``).  Always required — there is no partial update."""
    webhook_secret: str | None = None
    """Resend webhook signing secret (``whsec_…``).  Optional."""
    from_email: str
    """Sender address verified on Resend (e.g. ``leo@mail.dibodev.fr``)."""
    from_name: str | None = None
    """Sender display name shown to recipients."""


class ResendConfigResponse(BaseModel):
    """
    Resend configuration returned to the frontend.

    The raw API key and webhook secret are **never** included.  The frontend
    only needs to know whether they are configured (``has_api_key``,
    ``has_webhook_secret``) and the non-sensitive sender fields.
    """

    has_api_key: bool
    has_webhook_secret: bool
    from_email: str | None
    from_name: str | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_or_none(db: Session, user_id: int) -> ResendConfig | None:
    """Return the ResendConfig row for *user_id*, or ``None`` if absent."""
    return db.execute(
        select(ResendConfig).where(ResendConfig.user_id == user_id)
    ).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/resend", response_model=ResendConfigResponse)
async def get_resend_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Return the current user's Resend configuration (no secrets exposed).

    ``has_api_key`` and ``has_webhook_secret`` let the frontend display
    whether the values are configured without leaking them.
    """
    config: ResendConfig | None = _get_or_none(db, current_user.id)
    return {
        "has_api_key":        config is not None and bool(config.api_key),
        "has_webhook_secret": config is not None and bool(config.webhook_secret),
        "from_email":         config.from_email if config else None,
        "from_name":          config.from_name if config else None,
    }


@router.put("/resend", response_model=ResendConfigResponse)
async def upsert_resend_config(
    payload: ResendConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Create or replace the current user's Resend configuration.

    The API key and webhook secret are encrypted before being written to the
    database using the application's symmetric Fernet key.
    """
    encrypted_api_key: str = encryption_service.encrypt(payload.api_key)
    encrypted_secret: str | None = (
        encryption_service.encrypt(payload.webhook_secret)
        if payload.webhook_secret
        else None
    )

    config: ResendConfig | None = _get_or_none(db, current_user.id)
    if config is None:
        config = ResendConfig(user_id=current_user.id)
        db.add(config)

    config.api_key        = encrypted_api_key
    config.webhook_secret = encrypted_secret
    config.from_email     = payload.from_email
    config.from_name      = payload.from_name
    db.commit()

    logger.info("[Settings] ResendConfig upserted for user %d", current_user.id)

    return {
        "has_api_key":        True,
        "has_webhook_secret": encrypted_secret is not None,
        "from_email":         config.from_email,
        "from_name":          config.from_name,
    }
