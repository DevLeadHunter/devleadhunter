"""
Settings routes — per-user application settings.

Exposes the Resend email configuration (GET + PUT) and the presenter
(webcam) takes used by prospection videos: several per module, one in use,
each with the example video it gives on one of the user's demos.
The Resend API key and webhook secret are encrypted at rest and never
returned in plain text to the frontend.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_db
from enums.sending_provider import SendingProvider
from models.presenter_video import PresenterVideo
from models.resend_config import ResendConfig
from models.user import User
from schemas.presenter_video import (
    PresenterVideoAutoGenerateUpdate,
    PresenterVideoResponse,
    PresenterVideoSettingsUpdate,
    PresenterVideoTakeListResponse,
    PresenterVideoTimingsUpdate,
)
from services.auth_service import get_current_user
from services.encryption_service import encryption_service
from services.presenter_video_service import PresenterTakeInUseError, presenter_video_service
from services.r2_storage_service import r2_storage
from services.sending_identity import (
    SendingNotConfiguredError,
    describe_sending_config,
    set_active_provider,
)

router = APIRouter(prefix="/settings", tags=["settings"])
logger = logging.getLogger(__name__)


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
    show_webhook_secret_warning: bool
    from_email: str | None
    from_name: str | None

    model_config = ConfigDict(from_attributes=True)


def _get_or_none(db: Session, user_id: int) -> ResendConfig | None:
    """Return the ResendConfig row for *user_id*, or ``None`` if absent."""
    return db.execute(select(ResendConfig).where(ResendConfig.user_id == user_id)).scalar_one_or_none()


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
    has_api_key = config is not None and bool(config.api_key)
    has_webhook_secret = config is not None and bool(config.webhook_secret)
    return {
        "has_api_key": has_api_key,
        "has_webhook_secret": has_webhook_secret,
        "show_webhook_secret_warning": has_api_key and not has_webhook_secret,
        "from_email": config.from_email if config else None,
        "from_name": config.from_name if config else None,
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
        encryption_service.encrypt(payload.webhook_secret) if payload.webhook_secret else None
    )

    config: ResendConfig | None = _get_or_none(db, current_user.id)
    if config is None:
        config = ResendConfig(user_id=current_user.id)
        db.add(config)

    config.api_key = encrypted_api_key
    config.webhook_secret = encrypted_secret
    config.from_email = payload.from_email
    config.from_name = payload.from_name
    db.commit()

    logger.info("[Settings] ResendConfig upserted for user %d", current_user.id)

    return {
        "has_api_key": True,
        "has_webhook_secret": encrypted_secret is not None,
        "show_webhook_secret_warning": encrypted_secret is None,
        "from_email": config.from_email,
        "from_name": config.from_name,
    }


class SendingIdentityResponse(BaseModel):
    """The user's active sending provider + per-provider readiness (no secrets)."""

    provider: str
    resend_configured: bool
    resend_from_email: str | None
    gmail_configured: bool
    gmail_email: str | None
    reply_capture_enabled: bool = False


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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    logger.info("[Settings] Sending provider set to %s for user %d", payload.provider.value, current_user.id)
    return describe_sending_config(db, current_user.id)


def _public_url_or_none(key: str | None) -> str | None:
    """Public read URL of a stored file, or None when it is not on R2 or R2 is not configured."""
    if not key or not key.startswith(r2_storage.VIDEOS_PRESENTER_PREFIX):
        return None
    try:
        return r2_storage.public_url(key)
    except RuntimeError:
        return None


def _serialize_take(take: PresenterVideo | None, *, is_clip_missing: bool = False) -> PresenterVideoResponse:
    """Build the response of one take, or of a module without take."""
    if take is None:
        return PresenterVideoResponse(has_video=False)
    return PresenterVideoResponse(
        has_video=True,
        id=take.id,
        take_number=take.take_number,
        is_active=take.is_active,
        original_filename=take.original_filename,
        duration_seconds=take.duration_seconds,
        intro_seconds=take.intro_seconds,
        outro_seconds=take.outro_seconds,
        site_seconds=take.site_seconds,
        auto_generate=take.auto_generate,
        source=take.source or "upload",
        clip_url=_public_url_or_none(take.file_path),
        is_clip_missing=is_clip_missing,
        example_video_url=_public_url_or_none(take.example_video_key),
        example_subject_id=take.example_subject_id,
        example_subject_name=take.example_subject_name,
        example_generated_at=take.example_generated_at,
        created_at=take.created_at,
        updated_at=take.updated_at or take.created_at,
    )


def _owned_take_or_404(db: Session, user_id: int, take_id: int) -> PresenterVideo:
    """Return the user's take, or answer 404 (also for another user's take)."""
    take = presenter_video_service.get_take(db, user_id, take_id)
    if take is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prise introuvable.")
    return take


async def _stream_clip(take: PresenterVideo | None) -> StreamingResponse:
    """Relay a take's clip from R2 without buffering it whole."""
    if take is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun clip de présentation.")
    try:
        body, content_type, size = await asyncio.to_thread(r2_storage.open_stream, take.file_path)
    # L'objet peut avoir disparu du bucket, ou R2 ne pas être configuré.
    except Exception as error:
        logger.warning("[Presenter] clip introuvable sur R2 pour la prise %s : %s", take.id, error)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Le fichier du clip est introuvable."
        ) from error
    headers = {"Content-Length": str(size)} if size else None
    return StreamingResponse(body.iter_chunks(), media_type=content_type, headers=headers)


async def _take_list_response(db: Session, user_id: int, module: str) -> PresenterVideoTakeListResponse:
    """Build the module's take list, flagging the takes whose clip is gone from the storage."""
    takes = presenter_video_service.list_takes(db, user_id, module)
    missing_clip_take_ids = await asyncio.to_thread(presenter_video_service.find_missing_clips, takes)
    return PresenterVideoTakeListResponse(
        takes=[_serialize_take(take, is_clip_missing=take.id in missing_clip_take_ids) for take in takes],
        auto_generate=presenter_video_service.is_module_auto_generating(db, user_id, module),
    )


@router.get("/presenter-video", response_model=PresenterVideoResponse)
async def get_presenter_video(
    module: str = "websites",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresenterVideoResponse:
    """Return the take the module's prospection videos are built with ('websites' by default)."""
    return _serialize_take(presenter_video_service.get_for_user(db, current_user.id, module))


@router.put("/presenter-video", response_model=PresenterVideoResponse)
async def upload_presenter_video(
    file: UploadFile = File(...),
    intro_seconds: float = Form(default=4.0, ge=0, le=30),
    outro_seconds: float = Form(default=5.0, ge=0, le=30),
    auto_generate: bool = Form(default=True),
    module: str = "websites",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresenterVideoResponse:
    """Keep an imported clip as a new take of the module; it is used right away only when it is the first one."""
    take = await presenter_video_service.store_upload(
        db, current_user.id, file, intro_seconds, outro_seconds, auto_generate, module
    )
    logger.info(
        "[Settings] Presenter take %d uploaded for user %d (%.1fs)", take.id, current_user.id, take.duration_seconds
    )
    return _serialize_take(take)


@router.put("/presenter-video/segments", response_model=PresenterVideoResponse)
async def upload_presenter_video_segments(
    intro: UploadFile = File(...),
    middle: UploadFile = File(...),
    outro: UploadFile = File(...),
    auto_generate: bool = Form(default=True),
    module: str = "websites",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresenterVideoResponse:
    """Assemble the three parts filmed in-app into a new take of the module."""
    take = await presenter_video_service.store_recorded_segments(
        db, current_user.id, intro, middle, outro, auto_generate, module
    )
    logger.info(
        "[Settings] Presenter take %d recorded in-app for user %d (%.1fs — intro %.1fs / outro %.1fs)",
        take.id,
        current_user.id,
        take.duration_seconds,
        take.intro_seconds,
        take.outro_seconds,
    )
    return _serialize_take(take)


@router.patch("/presenter-video", response_model=PresenterVideoResponse)
async def update_presenter_video_settings(
    payload: PresenterVideoSettingsUpdate,
    module: str = "websites",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresenterVideoResponse:
    """Adjust the cut points of the take in use and the module's auto-generation."""
    take = presenter_video_service.get_for_user(db, current_user.id, module)
    if take is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun clip de présentation.")
    take = presenter_video_service.update_settings(
        db,
        take,
        payload.intro_seconds,
        payload.outro_seconds,
        payload.auto_generate,
        site_seconds=payload.site_seconds,
    )
    return _serialize_take(take)


@router.delete("/presenter-video", response_model=PresenterVideoResponse)
async def delete_presenter_video(
    module: str = "websites",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresenterVideoResponse:
    """Delete the take in use, when it is the module's last one."""
    try:
        presenter_video_service.delete_for_user(db, current_user.id, module)
    except PresenterTakeInUseError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return _serialize_take(None)


@router.get("/presenter-video/file")
async def stream_presenter_video_file(
    module: str = "websites",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream the take in use from R2, for the desktop app that builds the prospects' videos."""
    return await _stream_clip(presenter_video_service.get_for_user(db, current_user.id, module))


@router.get("/presenter-video/takes", response_model=PresenterVideoTakeListResponse)
async def list_presenter_video_takes(
    module: str = "websites",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresenterVideoTakeListResponse:
    """Return the module's takes, the oldest first, with the module's auto-generation setting."""
    return await _take_list_response(db, current_user.id, module)


@router.patch("/presenter-video/auto-generate", response_model=PresenterVideoTakeListResponse)
async def update_presenter_video_auto_generate(
    payload: PresenterVideoAutoGenerateUpdate,
    module: str = "websites",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresenterVideoTakeListResponse:
    """Turn on or off the video every new demo of the module gets on its own."""
    presenter_video_service.set_auto_generate(db, current_user.id, module, payload.auto_generate)
    return await _take_list_response(db, current_user.id, module)


@router.patch("/presenter-video/takes/{take_id}", response_model=PresenterVideoResponse)
async def update_presenter_video_take(
    take_id: int,
    payload: PresenterVideoTimingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresenterVideoResponse:
    """Adjust one take's cut points; its example video, built with the previous ones, goes when they move."""
    take = _owned_take_or_404(db, current_user.id, take_id)
    take = presenter_video_service.update_take_timings(
        db, take, payload.intro_seconds, payload.outro_seconds, payload.site_seconds
    )
    return _serialize_take(take)


@router.post("/presenter-video/takes/{take_id}/activate", response_model=PresenterVideoResponse)
async def activate_presenter_video_take(
    take_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresenterVideoResponse:
    """Make this take the one the module's next prospection videos are built with."""
    take = presenter_video_service.activate_take(db, _owned_take_or_404(db, current_user.id, take_id))
    logger.info("[Settings] Presenter take %d now used by user %d (%s)", take.id, current_user.id, take.module)
    return _serialize_take(take)


@router.delete("/presenter-video/takes/{take_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_presenter_video_take(
    take_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a take with its clip and example video; the take in use goes only once it is the last one."""
    take = _owned_take_or_404(db, current_user.id, take_id)
    try:
        presenter_video_service.delete_take(db, take)
    except PresenterTakeInUseError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/presenter-video/takes/{take_id}/file")
async def stream_presenter_video_take_file(
    take_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream one take's clip from R2, for the desktop app to build its example video."""
    return await _stream_clip(_owned_take_or_404(db, current_user.id, take_id))


@router.put("/presenter-video/takes/{take_id}/example", response_model=PresenterVideoResponse)
async def upload_presenter_video_take_example(
    take_id: int,
    file: UploadFile = File(...),
    subject_id: int = Form(...),
    subject_name: str = Form(..., min_length=1, max_length=255),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PresenterVideoResponse:
    """Keep the example video the desktop app built with this take on one of the user's demos."""
    take = _owned_take_or_404(db, current_user.id, take_id)
    take = await presenter_video_service.store_example(db, take, file, subject_id, subject_name)
    return _serialize_take(take)
