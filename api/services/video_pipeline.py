"""Shared building blocks for the prospection-video pipelines (the site's, and a product module's own).

:mod:`services.demo_video_service` and a product module's video service (its receptionist's…) are built by the
owner's desktop app the same way — the same limits on the middle a capture fills and on the time a build may take,
the same record of the builds under way — and differ only in *what* they capture and *where* they store it. Those
common mechanics live here so no module reaches into another's privates.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TypeAlias

from core.clock import naive_utc_now

# Minimum duration of the "middle" segment (site scroll, a module's own scene) for a capture to mean something.
MIN_SCROLL_SECONDS = 6.0

# A render taking longer is stuck: it is abandoned and marked failed (the desktop app stops waiting at the same point).
MAXIMUM_GENERATION_MINUTES = 20
MAXIMUM_GENERATION_SECONDS = MAXIMUM_GENERATION_MINUTES * 60.0
GENERATION_OVERRUN_MESSAGE = (
    f"La génération a duré plus de {MAXIMUM_GENERATION_MINUTES} minutes : elle a été arrêtée. Relancez-la."
)

# A build takes two to three minutes and the desktop app gives it up after twenty. Past this delay the app is
# taken for closed mid-build, and the request is offered again.
_DESKTOP_BUILD_LIFETIME: timedelta = timedelta(minutes=25)

# A generation is known by its kind of video and the id of the demo site (or module demo) it presents.
GenerationKey: TypeAlias = tuple[str, int]


class VideoGenerationError(Exception):
    """Raised when a step of a video pipeline fails (message shown in-app)."""


class VideoCaptureError(Exception):
    """Raised when the middle of a prospection video cannot be filmed (message shown in-app); a module's own
    capture raises a subclass."""


class DesktopVideoBuilds:
    """
    The videos a desktop app took to build, kept in the memory of the API process.

    The API runs a single worker, like the desktop app presence: a restart forgets the builds under way, so their
    requests are simply offered again.
    """

    def __init__(self, build_lifetime: timedelta = _DESKTOP_BUILD_LIFETIME) -> None:
        """
        Start with no build under way.

        Args:
            build_lifetime: How long a taken build is believed to run before its request is offered again.
        """
        self._build_lifetime = build_lifetime
        self._started_at: dict[GenerationKey, datetime] = {}

    def start(self, key: GenerationKey) -> None:
        """
        Record that a desktop app starts building a video.

        Args:
            key: The video.
        """
        self._started_at[key] = naive_utc_now()

    def forget(self, key: GenerationKey) -> None:
        """
        Drop a build: published, given up, withdrawn or replaced by a new request.

        Args:
            key: The video.
        """
        self._started_at.pop(key, None)

    def is_running(self, key: GenerationKey) -> bool:
        """
        Whether a desktop app took the video recently enough to still be building it.

        Args:
            key: The video.

        Returns:
            True while the build is taken for running.
        """
        started_at = self._started_at.get(key)
        return started_at is not None and naive_utc_now() - started_at <= self._build_lifetime


desktop_video_builds = DesktopVideoBuilds()
