"""
Settings routes — per-user application settings.

Exposes the Resend email configuration (GET + PUT) and the presenter
(webcam) clip used by prospection videos (GET/PUT/PATCH/DELETE + preview).
The Resend API key and webhook secret are encrypted at rest and never
returned in plain text to the frontend.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_db
from enums.sending_provider import SendingProvider
from models.presenter_video import PresenterVideo
from models.resend_config import ResendConfig
from models.user import User
from services.auth_service import get_current_user
from services.encryption_service import encryption_service
from services.presenter_video_service import presenter_video_service
from services.sending_identity import (
    SendingNotConfiguredError,
    describe_sending_config,
    set_active_provider,
)

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


# ---------------------------------------------------------------------------
# Sending identity (active email transport: Resend or Gmail)
# ---------------------------------------------------------------------------


class SendingIdentityResponse(BaseModel):
    """The user's active sending provider + per-provider readiness (no secrets)."""

    provider: str
    resend_configured: bool
    resend_from_email: str | None
    gmail_configured: bool
    gmail_email: str | None


class SendingProviderUpdate(BaseModel):
    """Payload to switch the user's active sending provider."""

    provider: SendingProvider


@router.get("/sending-identity", response_model=SendingIdentityResponse)
async def get_sending_identity(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return the user's active sending provider and each provider's readiness."""
    return describe_sending_config(db, current_user.id)


@router.put("/sending-identity", response_model=SendingIdentityResponse)
async def update_sending_identity(
    payload: SendingProviderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Switch the user's active sending provider (Resend or Gmail).

    Rejects a switch onto a provider that is not configured yet (422) so the
    account can never point at an unusable transport.
    """
    try:
        set_active_provider(db, current_user.id, payload.provider.value)
    except SendingNotConfiguredError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    logger.info(
        "[Settings] Sending provider set to %s for user %d", payload.provider.value, current_user.id
    )
    return describe_sending_config(db, current_user.id)


# ---------------------------------------------------------------------------
# Presenter video (clip webcam générique des vidéos de prospection)
# ---------------------------------------------------------------------------


class PresenterVideoResponse(BaseModel):
    """Presenter clip state returned to the frontend (no file content)."""

    has_video: bool
    original_filename: Optional[str] = None
    duration_seconds: float = 0.0
    intro_seconds: float = 4.0
    outro_seconds: float = 5.0
    auto_generate: bool = True
    updated_at: Optional[str] = None


class PresenterVideoSettingsUpdate(BaseModel):
    """Payload to adjust the intro/outro segments + auto-generation toggle."""

    intro_seconds: float = Field(..., ge=0, le=30)
    outro_seconds: float = Field(..., ge=0, le=30)
    auto_generate: bool = True


def _serialize_presenter(record: PresenterVideo | None) -> dict[str, Any]:
    """Build the presenter clip response payload."""
    if record is None:
        return {"has_video": False}
    timestamp = record.updated_at or record.created_at
    return {
        "has_video": True,
        "original_filename": record.original_filename,
        "duration_seconds": record.duration_seconds,
        "intro_seconds": record.intro_seconds,
        "outro_seconds": record.outro_seconds,
        "auto_generate": record.auto_generate,
        "updated_at": timestamp.isoformat() if timestamp else None,
    }


@router.get("/presenter-video", response_model=PresenterVideoResponse)
async def get_presenter_video(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return the current user's presenter clip metadata."""
    return _serialize_presenter(presenter_video_service.get_for_user(db, current_user.id))


@router.put("/presenter-video", response_model=PresenterVideoResponse)
async def upload_presenter_video(
    file: UploadFile = File(...),
    intro_seconds: float = Form(default=4.0, ge=0, le=30),
    outro_seconds: float = Form(default=5.0, ge=0, le=30),
    auto_generate: bool = Form(default=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Upload (or replace) the presenter clip used by prospection videos."""
    record = await presenter_video_service.store_upload(
        db, current_user.id, file, intro_seconds, outro_seconds, auto_generate
    )
    logger.info("[Settings] Presenter clip uploaded for user %d (%.1fs)", current_user.id, record.duration_seconds)
    return _serialize_presenter(record)


@router.patch("/presenter-video", response_model=PresenterVideoResponse)
async def update_presenter_video_settings(
    payload: PresenterVideoSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Adjust intro/outro segments + auto-generation of the existing clip."""
    record = presenter_video_service.get_for_user(db, current_user.id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun clip de présentation.")
    record = presenter_video_service.update_settings(
        db, record, payload.intro_seconds, payload.outro_seconds, payload.auto_generate
    )
    return _serialize_presenter(record)


@router.delete("/presenter-video", response_model=PresenterVideoResponse)
async def delete_presenter_video(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Delete the presenter clip (file + record)."""
    presenter_video_service.delete_for_user(db, current_user.id)
    return {"has_video": False}


@router.get("/presenter-video/file")
async def stream_presenter_video_file(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Stream the user's own presenter clip (in-app preview player)."""
    record = presenter_video_service.get_for_user(db, current_user.id)
    if record is None or not Path(record.file_path).is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun clip de présentation.")
    suffix = Path(record.file_path).suffix.lower()
    media_types = {".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime", ".mkv": "video/x-matroska"}
    return FileResponse(record.file_path, media_type=media_types.get(suffix, "application/octet-stream"))
