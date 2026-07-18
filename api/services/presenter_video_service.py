"""Presenter (webcam) source clip management.

One clip per user, uploaded from the app settings drawer. The clip is the
generic voice/webcam track (« Bonjour, moi c'est Léo… ») reused by every
generated prospection video — see ``demo_video_service``.
"""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from models.presenter_video import PresenterVideo

logger = logging.getLogger(__name__)

# Formats acceptés pour le clip webcam (conteneurs lisibles par ffmpeg).
_ALLOWED_EXTENSIONS: dict[str, str] = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/x-matroska": ".mkv",
}

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d{2}):(\d{2})\.(\d+)")

# Bornes de durée du clip présentateur : trop court = pas de place pour le
# site, trop long = personne ne regarde (cible 30-45 s).
MIN_PRESENTER_SECONDS = 12.0
MAX_PRESENTER_SECONDS = 90.0


async def probe_media_duration(file_path: str) -> float:
    """
    Return a media file's duration in seconds using ffmpeg.

    Parses the ``Duration: HH:MM:SS.cc`` line from ``ffmpeg -i`` stderr so it
    works with the bundled ffmpeg builds that ship without ffprobe.

    @param file_path - Absolute or repo-relative media path.
    @returns Duration in seconds (0.0 when it cannot be determined).
    """
    try:
        process = await asyncio.create_subprocess_exec(
            settings.ffmpeg_path,
            "-hide_banner",
            "-i",
            file_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(process.communicate(), timeout=30)
    except (FileNotFoundError, asyncio.TimeoutError) as exc:
        logger.warning("ffmpeg probe failed for %s: %s", file_path, exc)
        return 0.0

    match = _DURATION_RE.search(stderr.decode("utf-8", errors="replace"))
    if not match:
        return 0.0
    hours, minutes, seconds, fraction = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + float(f"0.{fraction}")


class PresenterVideoService:
    """CRUD for the per-user presenter clip (file on disk + DB row)."""

    def get_for_user(self, db: Session, user_id: int) -> Optional[PresenterVideo]:
        """Return the user's presenter clip row, or None."""
        return db.execute(
            select(PresenterVideo).where(PresenterVideo.user_id == user_id)
        ).scalar_one_or_none()

    async def store_upload(
        self,
        db: Session,
        user_id: int,
        file: UploadFile,
        intro_seconds: float,
        outro_seconds: float,
    ) -> PresenterVideo:
        """
        Persist the uploaded presenter clip (replaces any previous one).

        @param db - Active database session.
        @param user_id - Owner of the clip.
        @param file - Uploaded video file (mp4 / webm / mov / mkv).
        @param intro_seconds - Full-screen webcam seconds at the start.
        @param outro_seconds - Full-screen webcam seconds at the end.
        @returns The up-to-date ``PresenterVideo`` row.
        @throws HTTPException 400/413 on invalid format, size or duration.
        """
        content_type = (file.content_type or "").lower()
        extension = _ALLOWED_EXTENSIONS.get(content_type)
        if extension is None:
            # Certains navigateurs envoient un content-type générique : on
            # retombe sur l'extension du nom de fichier.
            suffix = Path(file.filename or "").suffix.lower()
            if suffix in _ALLOWED_EXTENSIONS.values():
                extension = suffix
        if extension is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format vidéo non supporté. Formats acceptés : MP4, WebM, MOV, MKV.",
            )

        data = await file.read()
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier vidéo vide.")
        max_bytes = settings.presenter_video_max_mb * 1024 * 1024
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"La vidéo dépasse {settings.presenter_video_max_mb} MB.",
            )

        base_dir = Path(settings.presenter_video_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        target_path = base_dir / f"user-{user_id}{extension}"

        # Purger les anciens fichiers du user (l'extension peut changer).
        for old in base_dir.glob(f"user-{user_id}.*"):
            try:
                old.unlink()
            except OSError:
                pass

        target_path.write_bytes(data)

        duration = await probe_media_duration(str(target_path))
        if duration <= 0:
            target_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de lire cette vidéo (fichier corrompu ?).",
            )
        if not (MIN_PRESENTER_SECONDS <= duration <= MAX_PRESENTER_SECONDS):
            target_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Durée du clip : {duration:.0f}s. Attendu entre {MIN_PRESENTER_SECONDS:.0f}s "
                    f"et {MAX_PRESENTER_SECONDS:.0f}s (cible : 30-45s)."
                ),
            )

        record = self.get_for_user(db, user_id)
        if record is None:
            record = PresenterVideo(user_id=user_id, file_path=str(target_path))
            db.add(record)
        record.file_path = str(target_path)
        record.original_filename = file.filename or f"presenter{extension}"
        record.duration_seconds = duration
        record.intro_seconds = self._clamp_segment(intro_seconds, duration)
        record.outro_seconds = self._clamp_segment(outro_seconds, duration)
        db.commit()
        db.refresh(record)
        return record

    def update_timings(
        self, db: Session, record: PresenterVideo, intro_seconds: float, outro_seconds: float
    ) -> PresenterVideo:
        """Update the intro/outro full-screen segments of an existing clip."""
        record.intro_seconds = self._clamp_segment(intro_seconds, record.duration_seconds)
        record.outro_seconds = self._clamp_segment(outro_seconds, record.duration_seconds)
        db.commit()
        db.refresh(record)
        return record

    def delete_for_user(self, db: Session, user_id: int) -> bool:
        """Delete the user's presenter clip (file + row). Returns True if one existed."""
        record = self.get_for_user(db, user_id)
        if record is None:
            return False
        try:
            Path(record.file_path).unlink(missing_ok=True)
        except OSError:
            pass
        db.delete(record)
        db.commit()
        return True

    @staticmethod
    def _clamp_segment(value: float, duration: float) -> float:
        """Keep an intro/outro segment sane: ≥0 and ≤ a third of the clip."""
        upper = max(duration / 3.0, 1.0) if duration > 0 else 10.0
        return round(min(max(value, 0.0), upper), 1)


presenter_video_service = PresenterVideoService()
