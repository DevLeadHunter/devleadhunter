"""Presenter (webcam) source clip management.

One clip per user, either uploaded as a file from the app settings page or
recorded in-app with the teleprompter (three takes concatenated here). The
clip is the generic voice/webcam track (« Bonjour, moi c'est Léo… ») reused
by every generated prospection video — see ``demo_video_service``.
"""
from __future__ import annotations

import asyncio
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from models.presenter_video import PresenterVideo
from services import r2_storage_service

logger = logging.getLogger(__name__)

# Formats acceptés pour le clip webcam (conteneurs lisibles par ffmpeg).
_ALLOWED_EXTENSIONS: dict[str, str] = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
    "video/x-matroska": ".mkv",
}

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d{2}):(\d{2})\.(\d+)")
# Dernière ligne de progression d'un décodage complet (`-f null -`), utilisée
# quand l'en-tête ne porte pas la durée.
_PROGRESS_TIME_RE = re.compile(r"time=\s*(\d+):(\d{2}):(\d{2})\.(\d+)")

# Bornes de durée du clip présentateur : trop court = pas de place pour le
# site, trop long = personne ne regarde (cible 30-45 s).
MIN_PRESENTER_SECONDS = 12.0
MAX_PRESENTER_SECONDS = 90.0

# Bornes d'un segment enregistré dans l'app (intro / milieu / outro). L'intro
# et l'outro deviennent `intro_seconds`/`outro_seconds`, que le montage borne
# déjà à un tiers du clip — inutile d'accepter plus long ici.
MIN_SEGMENT_SECONDS = 1.0
MAX_SEGMENT_SECONDS = 60.0

# La prise du milieu porte le défilement du site : elle doit couvrir au moins
# ``demo_video_service._MIN_SCROLL_SECONDS``, sinon chaque génération échouera.
MIN_MIDDLE_SECONDS = 6.0

# Canvas de sortie du clip enregistré, aligné sur celui du montage final
# (``demo_video_service``) pour qu'aucune mise à l'échelle ne se perde.
_RECORDING_WIDTH = 1280
_RECORDING_HEIGHT = 720
_RECORDING_FPS = 30


def _probe_media_duration_sync(file_path: str) -> float:
    """Blocking ffmpeg probe — run it via ``asyncio.to_thread`` only."""
    try:
        result = subprocess.run(
            [settings.ffmpeg_path, "-hide_banner", "-i", file_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.warning("ffmpeg probe failed for %s: %s", file_path, exc)
        return 0.0

    match = _DURATION_RE.search(result.stderr.decode("utf-8", errors="replace"))
    if not match:
        return 0.0
    hours, minutes, seconds, fraction = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + float(f"0.{fraction}")


def _measure_media_duration_sync(file_path: str) -> float:
    """
    Blocking, decode-based duration measurement — ``asyncio.to_thread`` only.

    Slower than reading the header, but it is the only way to size a WebM
    produced by the browser's ``MediaRecorder``: that container is written as
    a live stream, so its header carries no duration at all and ffmpeg prints
    ``Duration: N/A``. Decoding to the null muxer makes ffmpeg walk the whole
    file and report the real end timestamp on its last progress line.
    """
    try:
        result = subprocess.run(
            [settings.ffmpeg_path, "-hide_banner", "-i", file_path, "-f", "null", "-"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=120,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        logger.warning("ffmpeg decode-probe failed for %s: %s", file_path, exc)
        return 0.0

    matches = _PROGRESS_TIME_RE.findall(result.stderr.decode("utf-8", errors="replace"))
    if not matches:
        return 0.0
    hours, minutes, seconds, fraction = matches[-1]
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + float(f"0.{fraction}")


async def probe_media_duration(file_path: str) -> float:
    """
    Return a media file's duration in seconds using ffmpeg.

    Parses the ``Duration: HH:MM:SS.cc`` line from ``ffmpeg -i`` stderr so it
    works with the bundled ffmpeg builds that ship without ffprobe, and falls
    back to a full decode when the header has no duration (any WebM recorded
    by a browser).

    ⚠️ Runs ffmpeg in a worker thread (``subprocess.run``), never through
    ``asyncio.create_subprocess_exec``: the uvicorn reload worker may run a
    SelectorEventLoop on Windows, where asyncio subprocess support raises
    ``NotImplementedError``.

    @param file_path - Absolute or repo-relative media path.
    @returns Duration in seconds (0.0 when it cannot be determined).
    """
    duration = await asyncio.to_thread(_probe_media_duration_sync, file_path)
    if duration > 0:
        return duration
    return await asyncio.to_thread(_measure_media_duration_sync, file_path)


def _has_audio_stream_sync(file_path: str) -> bool:
    """Blocking check for an audio track — ``asyncio.to_thread`` only."""
    try:
        result = subprocess.run(
            [settings.ffmpeg_path, "-hide_banner", "-i", file_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return "Audio:" in result.stderr.decode("utf-8", errors="replace")


async def has_audio_stream(file_path: str) -> bool:
    """
    Tell whether a media file carries an audio track.

    Guards the concat filtergraph: it maps ``[n:a]`` for every input, so one
    silent segment (mic muted or grabbed by another app mid-take) would fail
    the whole render with an opaque ffmpeg error instead of a clear message.

    @param file_path - Absolute or repo-relative media path.
    @returns True when ffmpeg reports at least one audio stream.
    """
    return await asyncio.to_thread(_has_audio_stream_sync, file_path)


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
        auto_generate: bool = True,
    ) -> PresenterVideo:
        """
        Persist the uploaded presenter clip (replaces any previous one).

        @param db - Active database session.
        @param user_id - Owner of the clip.
        @param file - Uploaded video file (mp4 / webm / mov / mkv).
        @param intro_seconds - Full-screen webcam seconds at the start.
        @param outro_seconds - Full-screen webcam seconds at the end.
        @param auto_generate - Auto-generate the video for every new demo site.
        @returns The up-to-date ``PresenterVideo`` row.
        @throws HTTPException 400/413 on invalid format, size or duration.
        """
        extension = self._resolve_extension(file)

        data = await file.read()
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier vidéo vide.")
        max_bytes = settings.presenter_video_max_mb * 1024 * 1024
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"La vidéo dépasse {settings.presenter_video_max_mb} MB.",
            )

        work_dir = Path(tempfile.mkdtemp(prefix=f"presenter-upload-{user_id}-"))
        try:
            source_path = work_dir / f"source{extension}"
            source_path.write_bytes(data)

            duration = await probe_media_duration(str(source_path))
            if duration <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Impossible de lire cette vidéo (fichier corrompu ?).",
                )
            if not (MIN_PRESENTER_SECONDS <= duration <= MAX_PRESENTER_SECONDS):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Durée du clip : {duration:.0f}s. Attendu entre {MIN_PRESENTER_SECONDS:.0f}s "
                        f"et {MAX_PRESENTER_SECONDS:.0f}s (cible : 30-45s)."
                    ),
                )

            # Normalisation sur le canvas du montage : sans perte visible (le
            # montage y redimensionne de toute façon), mais source homogène,
            # rendu plus fiable et stockage divisé par 10 à 20.
            normalized_path = work_dir / "presenter.mp4"
            await self._normalize_clip(source_path, normalized_path)
            object_key = await self._publish(user_id, normalized_path)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

        record = self.get_for_user(db, user_id)
        if record is None:
            record = PresenterVideo(user_id=user_id, file_path=object_key)
            db.add(record)
        record.file_path = object_key
        record.original_filename = file.filename or f"presenter{extension}"
        record.duration_seconds = duration
        record.intro_seconds = self._clamp_segment(intro_seconds, duration)
        record.outro_seconds = self._clamp_segment(outro_seconds, duration)
        record.auto_generate = auto_generate
        record.source = "upload"
        db.commit()
        db.refresh(record)
        return record

    async def store_recorded_segments(
        self,
        db: Session,
        user_id: int,
        intro: UploadFile,
        middle: UploadFile,
        outro: UploadFile,
        auto_generate: bool = True,
    ) -> PresenterVideo:
        """
        Assemble the three in-app takes into the single presenter clip.

        Unlike :meth:`store_upload`, the cut points are not guessed: each take
        *is* a segment, so ``intro_seconds``/``outro_seconds`` are exactly the
        measured durations of the first and last take. The three files are
        concatenated and re-encoded into one normalised MP4 (the browser hands
        us WebM, and the takes are levelled with ``loudnorm`` so the two cuts
        are not audible).

        @param db - Active database session.
        @param user_id - Owner of the clip.
        @param intro - Full-screen greeting take.
        @param middle - Take played over the prospect's scrolling site.
        @param outro - Full-screen call-to-action take.
        @param auto_generate - Auto-generate the video for every new demo site.
        @returns The up-to-date ``PresenterVideo`` row.
        @throws HTTPException 400/413 on invalid format, size or duration.
        """
        uploads = (intro, middle, outro)
        labels = ("intro", "milieu", "outro")
        extensions = [self._resolve_extension(upload) for upload in uploads]

        payloads: list[bytes] = []
        for upload, label in zip(uploads, labels):
            data = await upload.read()
            if not data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Le segment « {label} » est vide.",
                )
            payloads.append(data)

        max_bytes = settings.presenter_video_max_mb * 1024 * 1024
        if sum(len(payload) for payload in payloads) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"L'enregistrement dépasse {settings.presenter_video_max_mb} MB.",
            )

        # Le rendu final vit dans son propre dossier temporaire : `work_dir` est
        # purgé dans le `finally` avant qu'on ait pu publier sur R2.
        out_dir = Path(tempfile.mkdtemp(prefix=f"presenter-out-{user_id}-"))
        target_path = out_dir / "presenter.mp4"
        work_dir = Path(tempfile.mkdtemp(prefix=f"presenter-{user_id}-"))

        try:
            segment_paths: list[Path] = []
            durations: list[float] = []
            for index, (payload, extension, label) in enumerate(zip(payloads, extensions, labels)):
                segment_path = work_dir / f"{index}{extension}"
                segment_path.write_bytes(payload)
                segment_paths.append(segment_path)

                duration = await probe_media_duration(str(segment_path))
                if duration <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Le segment « {label} » est illisible (enregistrement interrompu ?).",
                    )
                if not (MIN_SEGMENT_SECONDS <= duration <= MAX_SEGMENT_SECONDS):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Segment « {label} » : {duration:.0f}s. Attendu entre "
                            f"{MIN_SEGMENT_SECONDS:.0f}s et {MAX_SEGMENT_SECONDS:.0f}s."
                        ),
                    )
                if not await has_audio_stream(str(segment_path)):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Le segment « {label} » n'a aucun son. Vérifiez que le bon "
                            "micro est sélectionné, puis refaites cette prise."
                        ),
                    )
                durations.append(duration)

            intro_seconds, middle_seconds, outro_seconds = durations
            total = sum(durations)
            if not (MIN_PRESENTER_SECONDS <= total <= MAX_PRESENTER_SECONDS):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Durée totale : {total:.0f}s. Attendu entre {MIN_PRESENTER_SECONDS:.0f}s "
                        f"et {MAX_PRESENTER_SECONDS:.0f}s (cible : 30-45s)."
                    ),
                )
            # Le montage refuse un segment « site » plus court que 6 s : autant le
            # dire ici plutôt que de laisser échouer chaque génération plus tard.
            if middle_seconds < MIN_MIDDLE_SECONDS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"La prise du milieu ne dure que {middle_seconds:.0f}s : c'est elle qui "
                        f"couvre le défilement du site, il lui faut au moins {MIN_MIDDLE_SECONDS:.0f}s."
                    ),
                )

            await self._concat_segments(segment_paths, target_path)
            duration = await probe_media_duration(str(target_path))
        finally:
            # Le ménage ne doit jamais masquer l'erreur d'origine : sous Windows
            # ffmpeg peut encore tenir un handle sur un segment au moment du
            # rmdir, et ce OSError remplacerait le message utile.
            try:
                for leftover in work_dir.glob("*"):
                    leftover.unlink(missing_ok=True)
                work_dir.rmdir()
            except OSError:
                logger.warning("[Presenter] temp dir not fully cleaned: %s", work_dir)

        try:
            object_key = await self._publish(user_id, target_path)
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

        record = self.get_for_user(db, user_id)
        if record is None:
            record = PresenterVideo(user_id=user_id, file_path=object_key)
            db.add(record)
        record.file_path = object_key
        record.original_filename = "enregistrement-devleadhunter.mp4"
        record.duration_seconds = duration if duration > 0 else total
        record.intro_seconds = round(intro_seconds, 2)
        record.outro_seconds = round(outro_seconds, 2)
        record.auto_generate = auto_generate
        record.source = "recorded"
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    async def _publish(user_id: int, local_path: Path) -> str:
        """
        Push the normalised clip to R2 and return its object key.

        @param user_id - Owner of the clip.
        @param local_path - Normalised MP4 to upload.
        @returns The R2 key stored on the row (``videos/presenter/{user_id}.mp4``).
        @throws HTTPException 500 when the storage rejects the upload.
        """
        key = r2_storage_service.presenter_key(user_id)
        try:
            await r2_storage_service.upload_file_async(local_path, key, "video/mp4")
        except Exception as exc:  # noqa: BLE001 — surfaced as a readable API error
            logger.exception("[Presenter] R2 upload failed for user=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Impossible d'enregistrer le clip sur le stockage. Réessayez.",
            ) from exc
        return key

    async def _normalize_clip(self, source_path: Path, output_path: Path) -> None:
        """
        Re-encode an uploaded clip onto the composition canvas.

        The montage scales the presenter to the same canvas anyway (and to a
        260 px bubble for the PiP), so this costs no visible quality while
        making every source homogeneous: faster and more reliable renders, and
        a fraction of the storage. The audio track is optional here — the
        upload path does not require one.

        @param source_path - Raw uploaded clip.
        @param output_path - Destination MP4.
        @throws HTTPException 400 when ffmpeg is missing or fails.
        """
        command = [
            settings.ffmpeg_path,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source_path),
            "-vf",
            (
                f"scale={_RECORDING_WIDTH}:{_RECORDING_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={_RECORDING_WIDTH}:{_RECORDING_HEIGHT},setsar=1,fps={_RECORDING_FPS},"
                f"format=yuv420p"
            ),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "21",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "44100",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=600,
            )
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ffmpeg introuvable ({settings.ffmpeg_path}). Installez-le ou configurez FFMPEG_PATH.",
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La préparation du clip a dépassé le temps imparti.",
            ) from exc

        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace").strip()[-300:]
            logger.error("[Presenter] normalize failed: %s", detail)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de préparer cette vidéo. Réessayez avec un autre fichier.",
            )
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La préparation du clip n'a produit aucun fichier.",
            )

    async def _concat_segments(self, segment_paths: list[Path], output_path: Path) -> None:
        """
        Concatenate the takes into one normalised MP4.

        Uses the concat *filter* rather than the demuxer: the takes come from
        the browser as WebM and have to be re-encoded anyway, and the filter
        tolerates the small format drifts (timebase, sample rate) that a
        stream copy would not. ``loudnorm`` runs once on the joined audio so a
        take recorded slightly louder than the others does not betray the cut.

        @param segment_paths - Takes, in playback order.
        @param output_path - Destination MP4.
        @throws HTTPException 400 when ffmpeg is missing or fails.
        """
        count = len(segment_paths)
        chains: list[str] = []
        for index in range(count):
            chains.append(
                f"[{index}:v]scale={_RECORDING_WIDTH}:{_RECORDING_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={_RECORDING_WIDTH}:{_RECORDING_HEIGHT},setsar=1,fps={_RECORDING_FPS},"
                f"format=yuv420p[v{index}];"
            )
            chains.append(
                f"[{index}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo,"
                f"aresample=async=1:first_pts=0[a{index}];"
            )
        streams = "".join(f"[v{index}][a{index}]" for index in range(count))
        chains.append(f"{streams}concat=n={count}:v=1:a=1[vout][araw];")
        chains.append("[araw]loudnorm=I=-16:TP=-1.5:LRA=11[aout]")
        filter_complex = "".join(chains)

        command = [settings.ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error"]
        for segment_path in segment_paths:
            command += ["-i", str(segment_path)]
        command += [
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "22",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "44100",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        # ffmpeg via subprocess.run dans un thread — jamais asyncio subprocess
        # (NotImplementedError sur le SelectorEventLoop du worker uvicorn Windows).
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=300,
            )
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ffmpeg introuvable ({settings.ffmpeg_path}). Installez-le ou configurez FFMPEG_PATH.",
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le montage des prises a dépassé le temps imparti.",
            ) from exc

        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace").strip()[-300:]
            logger.error("[Presenter] concat failed: %s", detail)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible d'assembler les trois prises. Réessayez l'enregistrement.",
            )
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'assemblage n'a produit aucun fichier.",
            )

    @staticmethod
    def _resolve_extension(file: UploadFile) -> str:
        """
        Map an upload to a container extension ffmpeg can read.

        @param file - Incoming video upload.
        @returns The matching extension (e.g. ``.webm``).
        @throws HTTPException 400 when the container is not supported.
        """
        content_type = (file.content_type or "").lower().split(";")[0].strip()
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
        return extension

    def update_settings(
        self,
        db: Session,
        record: PresenterVideo,
        intro_seconds: float,
        outro_seconds: float,
        auto_generate: bool,
    ) -> PresenterVideo:
        """Update the intro/outro segments + auto-generation toggle of an existing clip."""
        record.intro_seconds = self._clamp_segment(intro_seconds, record.duration_seconds)
        record.outro_seconds = self._clamp_segment(outro_seconds, record.duration_seconds)
        record.auto_generate = auto_generate
        db.commit()
        db.refresh(record)
        return record

    def delete_for_user(self, db: Session, user_id: int) -> bool:
        """Delete the user's presenter clip (object + row). Returns True if one existed."""
        record = self.get_for_user(db, user_id)
        if record is None:
            return False
        stored = str(record.file_path or "")
        try:
            if stored.startswith(r2_storage_service.VIDEOS_PRESENTER_PREFIX):
                r2_storage_service.delete(stored)
            elif stored:
                # Ligne écrite avant la migration R2 : fichier encore sur disque.
                Path(stored).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001 — never block the delete on storage
            logger.warning("[Presenter] clip cleanup failed for user=%s", user_id, exc_info=True)
        db.delete(record)
        db.commit()
        return True

    @staticmethod
    def _clamp_segment(value: float, duration: float) -> float:
        """Keep an intro/outro segment sane: ≥0 and ≤ a third of the clip."""
        upper = max(duration / 3.0, 1.0) if duration > 0 else 10.0
        return round(min(max(value, 0.0), upper), 1)


presenter_video_service = PresenterVideoService()
