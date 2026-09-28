"""Shared building blocks for the prospection-video pipelines (site + assistant).

Both :mod:`services.demo_video_service` and :mod:`services.assistant_video_service` assemble a
video the same way — materialise the owner's presenter clip + profile photo, guard the box's memory
before a heavy step, and serialise every render behind one global semaphore — and differ only in
*what* they capture and *where* they store it. Those common mechanics live here so neither module
reaches into the other's privates.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeAlias

from sqlalchemy.orm import Session

from models.presenter_video import PresenterVideo
from services.r2_storage_service import r2_storage

logger = logging.getLogger(__name__)

# One render at a time: Playwright + ffmpeg are heavy for the box that also hosts the scrapers.
generation_semaphore = asyncio.Semaphore(1)

# Minimum duration of the "middle" segment (site scroll / assistant answering) for a capture to mean something.
MIN_SCROLL_SECONDS = 6.0

# Server-side capture guard: headless Chromium + the ffmpeg montage easily exceed the service memory
# cap on a busy VPS, and an OOM kill there takes down the whole single-worker API. Below this floor of
# available memory we refuse cleanly rather than crash the box.
MIN_FREE_MEMORY_MB_FOR_CAPTURE = 1200.0

# The ffmpeg montage is lighter than a headless capture, but it still OOM-killed the whole API on a
# starved box. Refuse it (fail clean) below this floor — this covers the desktop path too, where the
# montage is the only server-side step.
MIN_FREE_MEMORY_MB_FOR_MONTAGE = 500.0

# A render taking longer is stuck: it is stopped and marked failed (the desktop app stops waiting at the same point).
MAXIMUM_GENERATION_MINUTES = 20
MAXIMUM_GENERATION_SECONDS = MAXIMUM_GENERATION_MINUTES * 60.0
GENERATION_OVERRUN_MESSAGE = (
    f"La génération a duré plus de {MAXIMUM_GENERATION_MINUTES} minutes : elle a été arrêtée. Relancez-la."
)

# A generation is known by its kind of video and the id of the demo site or receptionist it presents.
GenerationKey: TypeAlias = tuple[str, int]


class VideoGenerationError(Exception):
    """Raised when a step of a video pipeline fails (message shown in-app)."""


@dataclass
class GenerationRun:
    """A generation started by this process: its task, and since when it holds the render slot."""

    task: asyncio.Task[None]
    rendering_since: float | None = None


class GenerationRuns:
    """
    The video generations under way in this process, waiting for the render slot or rendering.

    Holding their tasks here keeps them alive (asyncio only keeps weak references to tasks), and it is how the
    watchdog tells a live generation from one that a restart or a crash left behind: the API runs a single worker,
    so this process sees every generation.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        """
        Start with no generation under way.

        Args:
            clock: The monotonic clock that times the renders.
        """
        self._clock = clock
        self._runs: dict[GenerationKey, GenerationRun] = {}

    def start(self, key: GenerationKey, generation: Coroutine[Any, Any, None]) -> asyncio.Task[None]:
        """
        Run a generation in the background, held until it ends.

        Args:
            key: The video the generation makes.
            generation: The generation coroutine.

        Returns:
            Its task.
        """
        task = asyncio.create_task(generation)
        self._runs[key] = GenerationRun(task=task)
        task.add_done_callback(functools.partial(self._forget, key))
        return task

    def is_in_progress(self, key: GenerationKey) -> bool:
        """
        Whether a generation of this video is under way in this process.

        Args:
            key: The video.

        Returns:
            True while its task waits for the render slot or renders.
        """
        return key in self._runs

    def mark_rendering(self, key: GenerationKey) -> None:
        """
        Note that a generation holds the render slot: its maximum duration counts from now.

        Args:
            key: The video.
        """
        run = self._runs.get(key)
        if run is not None:
            run.rendering_since = self._clock()

    def has_overrun(self, key: GenerationKey, limit_seconds: float) -> bool:
        """
        Whether a generation has been rendering for longer than a limit.

        Args:
            key: The video.
            limit_seconds: The longest a render may take.

        Returns:
            True when the render started more than ``limit_seconds`` ago; False while it waits for the slot.
        """
        run = self._runs.get(key)
        if run is None or run.rendering_since is None:
            return False
        return self._clock() - run.rendering_since > limit_seconds

    def cancel(self, key: GenerationKey) -> None:
        """
        Stop a generation under way, if any (its task gets a cancellation at its next pause).

        Args:
            key: The video.
        """
        run = self._runs.get(key)
        if run is not None:
            run.task.cancel()

    def _forget(self, key: GenerationKey, task: asyncio.Task[None]) -> None:
        """
        Drop a finished generation, logging the exception its task died with (asyncio would only report it at exit).

        Args:
            key: The video.
            task: The finished task.
        """
        run = self._runs.get(key)
        if run is not None and run.task is task:
            del self._runs[key]
        if not task.cancelled() and task.exception() is not None:
            logger.error("Video generation %s died", key, exc_info=task.exception())


generation_runs = GenerationRuns()


def naive_utc_now() -> datetime:
    """Current time as naive UTC, the storage convention."""
    return datetime.now(UTC).replace(tzinfo=None)


def available_memory_mb() -> float | None:
    """
    Available system memory in MB, read from Linux ``/proc/meminfo``.

    Returns:
        The available memory in MB, or None when it cannot be read (e.g. on a
        non-Linux host, where the server-side capture never runs anyway).
    """
    try:
        with open("/proc/meminfo", encoding="ascii") as meminfo:
            for line in meminfo:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / 1024
    except (OSError, ValueError):
        return None
    return None


def guard_memory(floor_mb: float, verb: str, advice: str = "Réessayez.") -> None:
    """
    Refuse a heavy step when the box is low on memory (an OOM kill takes down the API).

    Args:
        floor_mb: The minimum free memory (MB) required for the step.
        verb: The action, inserted into the user-facing message (e.g. ``"générer"``, ``"assembler"``).
        advice: What the user can do instead, which ends the message.

    Raises:
        VideoGenerationError: when available memory is below ``floor_mb``.
    """
    available = available_memory_mb()
    if available is not None and available < floor_mb:
        raise VideoGenerationError(
            f"Serveur momentanément trop chargé pour {verb} la vidéo ({available:.0f} Mo libres). {advice}"
        )


async def resolve_presenter_file(presenter: PresenterVideo, work_dir: Path) -> Path:
    """
    Materialise the presenter clip as a local file for ffmpeg.

    Clips live on R2 under ``videos/presenter/…``; rows written before the R2
    migration still hold a local disk path and keep working.

    Args:
        presenter: The user's presenter clip row.
        work_dir: Temp directory receiving the download.

    Returns:
        Path to a readable local file.

    Raises:
        VideoGenerationError: when the clip cannot be resolved.
    """
    stored = str(presenter.file_path or "").strip()
    if not stored:
        raise VideoGenerationError("Clip de présentation introuvable.")

    if stored.startswith(r2_storage.VIDEOS_PRESENTER_PREFIX):
        try:
            return await r2_storage.download_to_path_async(stored, work_dir / "presenter.mp4")
        except Exception as exc:
            raise VideoGenerationError("Clip de présentation illisible sur le stockage (R2).") from exc

    legacy = Path(stored)
    if legacy.is_file():
        return legacy
    raise VideoGenerationError("Clip de présentation introuvable.")


async def resolve_presenter_photo(db: Session, user_id: int, work_dir: Path) -> Path | None:
    """
    Materialise the user's profile photo (thumbnail bubble) as a local file.

    The photo is optional and must never fail a generation: any resolution
    problem just means a thumbnail without the bubble.

    Args:
        db: Active database session.
        user_id: Owner of the photo.
        work_dir: Temp directory receiving the download.

    Returns:
        Path to a readable local file, or None when the user has no photo.
    """
    from models.user import User

    user = db.query(User).filter(User.id == user_id).first()
    stored = str(user.profile_photo_path or "").strip() if user else ""
    if not stored:
        return None
    try:
        return await r2_storage.download_to_path_async(stored, work_dir / "presenter-photo.jpg")
    except Exception:
        logger.warning("Presenter photo unavailable for user=%s — thumbnail without bubble", user_id)
        return None


def resolve_first_name(db: Session, prospect_id: int | None) -> str | None:
    """
    First name of the resolved decision-maker for a prospect (None when unknown).

    Args:
        db: Active database session.
        prospect_id: The prospect whose decision-maker to resolve (None → None).

    Returns:
        The decision-maker's first name, or None.
    """
    if not prospect_id:
        return None
    from services.email_variables import EmailVariables

    first, _last, _gender = EmailVariables.resolved_contact(db, prospect_id)
    return first or None
