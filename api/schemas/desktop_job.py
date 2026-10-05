"""Contracts of the desktop jobs: work a device without the desktop app hands to the owner's computer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from enums.desktop_job import DesktopJobKind


class DesktopJobCreateRequest(BaseModel):
    """Work to leave for the desktop app, about one record."""

    kind: DesktopJobKind = Field(..., description="What the desktop app has to do")
    subject_id: int = Field(..., description="The prospect, site or other record the work is about")


class DesktopJobFailureRequest(BaseModel):
    """Why the desktop app could not do a job."""

    message: str = Field(min_length=1, max_length=1000)


class DesktopJobResponse(BaseModel):
    """A desktop job as the dashboard and the desktop app read it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    subject_id: int | None
    payload: dict[str, Any] | None
    status: str
    error_message: str | None
    requested_at: datetime
    claimed_at: datetime | None
    finished_at: datetime | None
