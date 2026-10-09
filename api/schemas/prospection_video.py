"""Schemas shared by the prospection videos of the demo sites and of the receptionists."""

from datetime import datetime

from pydantic import BaseModel, Field


class ProspectionVideoStateResponse(BaseModel):
    """Where a prospection video stands, light enough to be read every few seconds."""

    video_status: str | None = None
    video_error: str | None = None
    video_generated_at: datetime | None = None
    video_desktop_requested_at: datetime | None = None
    is_video_desktop_build_started: bool = False
    is_video_made_with_older_clip: bool = False
    video_page_url: str | None = None
    video_thumbnail_url: str | None = None


class ProspectionVideoDesktopFailureRequest(BaseModel):
    """Why the desktop app could not build a requested video."""

    message: str = Field(min_length=1, max_length=1000)
