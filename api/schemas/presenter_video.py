"""Contracts of the presenter (webcam) takes behind the prospection videos."""

from datetime import datetime

from pydantic import BaseModel, Field


class PresenterVideoResponse(BaseModel):
    """
    One presenter take returned to the frontend (no file content).

    ``has_video`` is False when the module has no take yet; every other field then keeps its default.
    """

    has_video: bool
    id: int | None = None
    take_number: int | None = None
    is_active: bool = False
    original_filename: str | None = None
    duration_seconds: float = 0.0
    intro_seconds: float = 4.0
    outro_seconds: float = 5.0
    # User-chosen site-scroll length; None = automatic split. Without this field the
    # response_model STRIPS the value and the UI falls back to the automatic split.
    site_seconds: float | None = None
    auto_generate: bool = True
    # « upload » (fichier importé) ou « recorded » (filmé dans l'app).
    source: str = "upload"
    clip_url: str | None = None
    is_clip_missing: bool = False
    example_video_url: str | None = None
    example_subject_id: int | None = None
    example_subject_name: str | None = None
    example_generated_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PresenterVideoTakeListResponse(BaseModel):
    """A module's takes, the oldest first, with the module's auto-generation setting."""

    takes: list[PresenterVideoResponse]
    auto_generate: bool


class PresenterVideoSettingsUpdate(BaseModel):
    """Cut points of the take in use and the module's auto-generation, as the single-clip settings form sent them."""

    intro_seconds: float = Field(..., ge=0, le=30)
    outro_seconds: float = Field(..., ge=0, le=30)
    # Length of the site-scroll part inside the middle; the Storyblok editor
    # sequence gets the remainder. None keeps the automatic split.
    site_seconds: float | None = Field(default=None, ge=0, le=120)
    auto_generate: bool = True


class PresenterVideoTimingsUpdate(BaseModel):
    """Cut points of one take."""

    intro_seconds: float = Field(..., ge=0, le=30)
    outro_seconds: float = Field(..., ge=0, le=30)
    site_seconds: float | None = Field(default=None, ge=0, le=120)


class PresenterVideoAutoGenerateUpdate(BaseModel):
    """Whether every new demo of the module gets its prospection video on its own."""

    auto_generate: bool
