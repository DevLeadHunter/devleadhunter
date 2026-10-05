"""Presenter (webcam) takes management.

A user keeps several takes per sellable module, each either uploaded as a file
from the app settings page or recorded in-app with the teleprompter (three
parts concatenated here). A take is the generic voice/webcam track
(« Bonjour, moi c'est Léo… ») reused by every generated prospection video —
see ``demo_video_service``. A new take never replaces an older one: the user
compares their example videos and picks the take the videos are built with.
"""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from core.config import settings
from models.presenter_video import PresenterVideo
from services.r2_storage_service import r2_storage

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
# ``video_pipeline.MIN_SCROLL_SECONDS``, sinon chaque génération échouera.
MIN_MIDDLE_SECONDS = 6.0

# Canvas de sortie du clip enregistré, aligné sur celui du montage final
# (``demo_video_service``) pour qu'aucune mise à l'échelle ne se perde.
_RECORDING_WIDTH = 1280
_RECORDING_HEIGHT = 720
_RECORDING_FPS = 30

# FLOAT columns read back with noise (4.3 comes back as 4.300000190734863): below this gap, a cut point has not moved.
_CUT_POINT_TOLERANCE_SECONDS = 0.01


class FfmpegUnavailableError(RuntimeError):
    """Raised when the ffmpeg binary is missing — a server fault, not a bad upload."""


class PresenterTakeInUseError(Exception):
    """Raised when deleting the take in use while the module keeps others: the videos must never switch silently."""


def _ffmpeg_missing_error() -> HTTPException:
    """Build the 500 returned when ffmpeg cannot be executed at all."""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=(
            f"Traitement vidéo indisponible : ffmpeg introuvable sur le serveur ({settings.ffmpeg_path}). "
            "Installez-le ou configurez FFMPEG_PATH."
        ),
    )


def _probe_media_duration_sync(file_path: str) -> float:
    """Blocking ffmpeg probe — run it via ``asyncio.to_thread`` only.

    Raises:
        FfmpegUnavailableError: The ffmpeg binary cannot be executed.
    """
    try:
        result = subprocess.run(
            [settings.ffmpeg_path, "-hide_banner", "-i", file_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except FileNotFoundError as exc:
        # Sans ce cas distinct, une durée nulle ferait passer une panne serveur
        # pour une vidéo corrompue.
        raise FfmpegUnavailableError(settings.ffmpeg_path) from exc
    except subprocess.TimeoutExpired as exc:
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

    Raises:
        FfmpegUnavailableError: The ffmpeg binary cannot be executed.
    """
    try:
        result = subprocess.run(
            [settings.ffmpeg_path, "-hide_banner", "-i", file_path, "-f", "null", "-"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=120,
        )
    except FileNotFoundError as exc:
        raise FfmpegUnavailableError(settings.ffmpeg_path) from exc
    except subprocess.TimeoutExpired as exc:
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

    Args:
        file_path: Absolute or repo-relative media path.

    Returns:
        Duration in seconds (0.0 when it cannot be determined).

    Raises:
        HTTPException: 500 when ffmpeg is not installed on the server.
    """
    try:
        duration = await asyncio.to_thread(_probe_media_duration_sync, file_path)
        if duration > 0:
            return duration
        return await asyncio.to_thread(_measure_media_duration_sync, file_path)
    except FfmpegUnavailableError as exc:
        logger.error("[Presenter] ffmpeg is not installed (%s)", settings.ffmpeg_path)
        raise _ffmpeg_missing_error() from exc


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

    Args:
        file_path: Absolute or repo-relative media path.

    Returns:
        True when ffmpeg reports at least one audio stream.
    """
    return await asyncio.to_thread(_has_audio_stream_sync, file_path)


class PresenterVideoService:
    """Presenter takes of each user and module: clips on R2, rows in ``presenter_videos``."""

    def get_for_user(self, db: Session, user_id: int, module: str = "websites") -> PresenterVideo | None:
        """Return the take the module's prospection videos are built with, or None when the module has no take."""
        statement = (
            select(PresenterVideo)
            .where(
                PresenterVideo.user_id == user_id,
                PresenterVideo.module == module,
                PresenterVideo.is_active.is_(True),
            )
            .order_by(PresenterVideo.id.desc())
        )
        return db.execute(statement).scalars().first()

    def list_takes(self, db: Session, user_id: int, module: str) -> list[PresenterVideo]:
        """Return the module's takes, the oldest first."""
        statement = (
            select(PresenterVideo)
            .where(PresenterVideo.user_id == user_id, PresenterVideo.module == module)
            .order_by(PresenterVideo.take_number, PresenterVideo.id)
        )
        return list(db.execute(statement).scalars().all())

    def get_take(self, db: Session, user_id: int, take_id: int) -> PresenterVideo | None:
        """Return one of the user's takes, or None when it does not exist or belongs to someone else."""
        statement = select(PresenterVideo).where(PresenterVideo.id == take_id, PresenterVideo.user_id == user_id)
        return db.execute(statement).scalar_one_or_none()

    def is_module_auto_generating(self, db: Session, user_id: int, module: str) -> bool:
        """Whether every new demo of the module gets its video on its own; on by default before the first take."""
        take_in_use = self.get_for_user(db, user_id, module)
        return take_in_use.auto_generate if take_in_use is not None else True

    def activate_take(self, db: Session, take: PresenterVideo) -> PresenterVideo:
        """
        Make this take the one the module's prospection videos are built with.

        Videos already generated keep the take they were made with.

        Args:
            db: Active database session.
            take: The user's take to use from now on.

        Returns:
            The take, now in use.
        """
        for candidate in self.list_takes(db, take.user_id, take.module):
            candidate.is_active = candidate.id == take.id
        db.commit()
        db.refresh(take)
        return take

    def set_auto_generate(self, db: Session, user_id: int, module: str, auto_generate: bool) -> None:
        """
        Turn the module's automatic video generation on or off.

        The setting belongs to the module: it is written on each of its takes so whichever take is chosen carries it.

        Args:
            db: Active database session.
            user_id: Owner of the takes.
            module: The sellable module.
            auto_generate: Whether every new demo of the module gets its video on its own.
        """
        for take in self.list_takes(db, user_id, module):
            take.auto_generate = auto_generate
        db.commit()

    def update_take_timings(
        self,
        db: Session,
        take: PresenterVideo,
        intro_seconds: float,
        outro_seconds: float,
        site_seconds: float | None,
    ) -> PresenterVideo:
        """
        Adjust the cut points of one take.

        An example video built with the previous cut points no longer shows what prospects would receive, so it is
        dropped when they move.

        Args:
            db: Active database session.
            take: The user's take.
            intro_seconds: Full-screen webcam seconds at the start.
            outro_seconds: Full-screen webcam seconds at the end.
            site_seconds: Length of the site-scroll part inside the middle (the Storyblok sequence gets the rest);
                None restores the automatic split.

        Returns:
            The up-to-date take.
        """
        if self._apply_timings(take, intro_seconds, outro_seconds, site_seconds):
            self._drop_example(take)
        db.commit()
        db.refresh(take)
        return take

    def delete_take(self, db: Session, take: PresenterVideo) -> None:
        """
        Delete a take: its clip, its example video and its row.

        Args:
            db: Active database session.
            take: The user's take.

        Raises:
            PresenterTakeInUseError: The take is in use and the module keeps other takes — choose one of them first.
        """
        has_other_takes = any(candidate.id != take.id for candidate in self.list_takes(db, take.user_id, take.module))
        if take.is_active and has_other_takes:
            raise PresenterTakeInUseError(
                "Cette prise sert aux vidéos : choisissez-en une autre avant de la supprimer."
            )
        self._delete_stored_files(take)
        db.delete(take)
        db.commit()

    async def store_example(
        self,
        db: Session,
        take: PresenterVideo,
        video: UploadFile,
        subject_id: int,
        subject_name: str,
    ) -> PresenterVideo:
        """
        Keep the example video a take gives on one of the user's demos, in place of its previous one.

        The desktop app builds it (the editor sequence needs the owner's Storyblok session) and sends it here only to
        be kept: nothing is published, the demo's own video is untouched.

        Args:
            db: Active database session.
            take: The user's take the example was built with.
            video: The finished MP4.
            subject_id: The demo site or receptionist filmed.
            subject_name: Its business name, shown under the example.

        Returns:
            The take with its new example.

        Raises:
            HTTPException: 400/413 when the file is empty, not an MP4 or too heavy; 500 when the storage refuses it.
        """
        if self._resolve_extension(video) != ".mp4":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La vidéo d'exemple doit être un MP4.")
        data = await video.read()
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vidéo d'exemple vide.")
        if len(data) > settings.presenter_video_max_mb * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"La vidéo d'exemple dépasse {settings.presenter_video_max_mb} MB.",
            )

        key = r2_storage.presenter_example_key(take.user_id)
        try:
            await r2_storage.upload_bytes_async(key, data, "video/mp4")
        except Exception as exc:
            logger.exception("[Presenter] example upload failed for take=%s", take.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Impossible d'enregistrer la vidéo d'exemple sur le stockage. Réessayez.",
            ) from exc

        replaced_key = take.example_video_key
        take.example_video_key = key
        take.example_subject_id = subject_id
        take.example_subject_name = subject_name
        take.example_generated_at = naive_utc_now()
        db.commit()
        db.refresh(take)
        if replaced_key:
            self._delete_object(replaced_key)
        return take

    @staticmethod
    def find_missing_clips(takes: list[PresenterVideo]) -> set[int]:
        """
        Return the ids of the takes whose clip is gone from the storage. Blocking: run it in a worker thread.

        Storage left unconfigured (tests, a misconfigured server) reports nothing rather than every clip missing.

        Args:
            takes: Takes to check.

        Returns:
            The ids of the takes no video can be built with.
        """
        if not r2_storage.is_configured():
            return set()
        missing: set[int] = set()
        for take in takes:
            stored = str(take.file_path or "")
            try:
                if stored.startswith(r2_storage.VIDEOS_PRESENTER_PREFIX):
                    is_present = r2_storage.exists(stored)
                else:
                    # Ligne écrite avant la migration R2 : fichier encore sur disque.
                    is_present = Path(stored).is_file()
            except Exception:
                logger.warning("[Presenter] clip check failed for take=%s", take.id, exc_info=True)
                continue
            if not is_present:
                missing.add(take.id)
        return missing

    async def store_upload(
        self,
        db: Session,
        user_id: int,
        file: UploadFile,
        intro_seconds: float,
        outro_seconds: float,
        auto_generate: bool = True,
        module: str = "websites",
    ) -> PresenterVideo:
        """
        Keep an uploaded clip as a new take of the module, next to the older ones.

        Args:
            db: Active database session.
            user_id: Owner of the take.
            file: Uploaded video file (mp4 / webm / mov / mkv).
            intro_seconds: Full-screen webcam seconds at the start.
            outro_seconds: Full-screen webcam seconds at the end.
            auto_generate: Auto-generate the video for every new demo site, when this is the module's first take.
            module: The sellable module the take belongs to.

        Returns:
            The new take, in use only when the module had none.

        Raises:
            HTTPException: 400/413 on invalid format, size or duration.
        """
        extension = self._resolve_extension(file)

        data = await file.read()
        if not data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fichier vidéo vide.")
        max_bytes = settings.presenter_video_max_mb * 1024 * 1024
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
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

        take = self._add_take(db, user_id, module, auto_generate)
        take.file_path = object_key
        take.original_filename = file.filename or f"presenter{extension}"
        take.duration_seconds = duration
        take.intro_seconds = self._clamp_segment(intro_seconds, duration)
        take.outro_seconds = self._clamp_segment(outro_seconds, duration)
        take.source = "upload"
        db.commit()
        db.refresh(take)
        return take

    async def store_recorded_segments(
        self,
        db: Session,
        user_id: int,
        intro: UploadFile,
        middle: UploadFile,
        outro: UploadFile,
        auto_generate: bool = True,
        module: str = "websites",
    ) -> PresenterVideo:
        """
        Assemble the three parts filmed in-app into a new take of the module, next to the older ones.

        Unlike :meth:`store_upload`, the cut points are not guessed: each part
        *is* a segment, so ``intro_seconds``/``outro_seconds`` are exactly the
        measured durations of the first and last part. The three files are
        concatenated and re-encoded into one normalised MP4 (the browser hands
        us WebM, and the parts are levelled with ``loudnorm`` so the two cuts
        are not audible).

        Args:
            db: Active database session.
            user_id: Owner of the take.
            intro: Full-screen greeting part.
            middle: Part played over the prospect's scrolling site.
            outro: Full-screen call-to-action part.
            auto_generate: Auto-generate the video for every new demo site, when this is the module's first take.
            module: The sellable module the take belongs to.

        Returns:
            The new take, in use only when the module had none.

        Raises:
            HTTPException: 400/413 on invalid format, size or duration.
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
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
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

        take = self._add_take(db, user_id, module, auto_generate)
        take.file_path = object_key
        take.original_filename = "enregistrement-devleadhunter.mp4"
        take.duration_seconds = duration if duration > 0 else total
        take.intro_seconds = round(intro_seconds, 2)
        take.outro_seconds = round(outro_seconds, 2)
        take.source = "recorded"
        db.commit()
        db.refresh(take)
        return take

    def _add_take(self, db: Session, user_id: int, module: str, auto_generate: bool) -> PresenterVideo:
        """
        Register a new take of the module, still without its file.

        The module's first take is put in use; a later one waits until the user chooses it, so no video is built
        with a take they have not compared yet. Auto-generation stays the module's setting.

        Args:
            db: Active database session.
            user_id: Owner of the take.
            module: The sellable module.
            auto_generate: The auto-generation setting, kept only for the module's first take.

        Returns:
            The new row, added to the session but not committed.
        """
        take_in_use = self.get_for_user(db, user_id, module)
        highest_take_number = db.execute(
            select(func.max(PresenterVideo.take_number)).where(
                PresenterVideo.user_id == user_id, PresenterVideo.module == module
            )
        ).scalar()
        take = PresenterVideo(
            user_id=user_id,
            module=module,
            take_number=(highest_take_number or 0) + 1,
            is_active=take_in_use is None,
            auto_generate=take_in_use.auto_generate if take_in_use is not None else auto_generate,
        )
        db.add(take)
        return take

    @staticmethod
    async def _publish(user_id: int, local_path: Path) -> str:
        """
        Push a normalised take to R2 and return its object key.

        Args:
            user_id: Owner of the take.
            local_path: Normalised MP4 to upload.

        Returns:
            The R2 key stored on the row, new for each take so no older take is ever overwritten.

        Raises:
            HTTPException: 500 when the storage rejects the upload.
        """
        key = r2_storage.presenter_take_key(user_id)
        try:
            await r2_storage.upload_file_async(local_path, key, "video/mp4")
        except Exception as exc:
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

        Args:
            source_path: Raw uploaded clip.
            output_path: Destination MP4.

        Raises:
            HTTPException: 400 when ffmpeg is missing or fails.
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
            raise _ffmpeg_missing_error() from exc
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

        Args:
            segment_paths: Takes, in playback order.
            output_path: Destination MP4.

        Raises:
            HTTPException: 400 when ffmpeg is missing or fails.
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
            raise _ffmpeg_missing_error() from exc
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

        Args:
            file: Incoming video upload.

        Returns:
            The matching extension (e.g. ``.webm``).

        Raises:
            HTTPException: 400 when the container is not supported.
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
        *,
        site_seconds: float | None = None,
    ) -> PresenterVideo:
        """
        Update the cut points of the take in use and the module's auto-generation, as the single-clip form sends them.

        Args:
            db: Active database session.
            record: The module's take in use.
            intro_seconds: Full-screen webcam seconds at the start.
            outro_seconds: Full-screen webcam seconds at the end.
            auto_generate: Whether every new demo of the module gets its video on its own.
            site_seconds: Length of the site-scroll part; None restores the automatic split.

        Returns:
            The up-to-date take.
        """
        for take in self.list_takes(db, record.user_id, record.module):
            take.auto_generate = auto_generate
        return self.update_take_timings(db, record, intro_seconds, outro_seconds, site_seconds)

    def delete_for_user(self, db: Session, user_id: int, module: str = "websites") -> bool:
        """
        Delete the module's take in use, as the single-clip form asks.

        Args:
            db: Active database session.
            user_id: Owner of the takes.
            module: The sellable module.

        Returns:
            Whether the module had a take in use.

        Raises:
            PresenterTakeInUseError: The module keeps other takes — one of them must be chosen first.
        """
        take_in_use = self.get_for_user(db, user_id, module)
        if take_in_use is None:
            return False
        self.delete_take(db, take_in_use)
        return True

    def _apply_timings(
        self,
        take: PresenterVideo,
        intro_seconds: float,
        outro_seconds: float,
        site_seconds: float | None,
    ) -> bool:
        """
        Write clamped cut points on a take, without committing.

        ``site_seconds`` is clamped to the middle so the timeline stays coherent.

        Returns:
            Whether a cut point moved.
        """
        intro = self._clamp_segment(intro_seconds, take.duration_seconds)
        outro = self._clamp_segment(outro_seconds, take.duration_seconds)
        site: float | None = None
        if site_seconds is not None:
            middle = max(0.0, take.duration_seconds - intro - outro)
            site = round(min(max(site_seconds, 0.0), middle), 2)

        has_moved = (
            self._differs(take.intro_seconds, intro)
            or self._differs(take.outro_seconds, outro)
            or self._differs(take.site_seconds, site)
        )
        take.intro_seconds = intro
        take.outro_seconds = outro
        take.site_seconds = site
        return has_moved

    def _drop_example(self, take: PresenterVideo) -> None:
        """Drop a take's example video (object and fields), without committing."""
        if take.example_video_key:
            self._delete_object(take.example_video_key)
        take.example_video_key = None
        take.example_subject_id = None
        take.example_subject_name = None
        take.example_generated_at = None

    def _delete_stored_files(self, take: PresenterVideo) -> None:
        """Delete a take's clip and example video from the storage; a leftover never blocks the deletion."""
        stored = str(take.file_path or "")
        if stored.startswith(r2_storage.VIDEOS_PRESENTER_PREFIX):
            self._delete_object(stored)
        elif stored:
            # Ligne écrite avant la migration R2 : fichier encore sur disque.
            try:
                Path(stored).unlink(missing_ok=True)
            except OSError:
                logger.warning("[Presenter] local clip cleanup failed for take=%s", take.id, exc_info=True)
        if take.example_video_key:
            self._delete_object(take.example_video_key)

    @staticmethod
    def _delete_object(key: str) -> None:
        """Delete one R2 object, logging instead of failing: an orphan file is better than a lost user action."""
        try:
            r2_storage.delete(key)
        except Exception:
            logger.warning("[Presenter] storage cleanup failed for key=%s", key, exc_info=True)

    @staticmethod
    def _differs(stored: float | None, wanted: float | None) -> bool:
        """Whether a cut point really changes, ignoring the noise of FLOAT columns."""
        if stored is None or wanted is None:
            return stored is not wanted
        return abs(stored - wanted) > _CUT_POINT_TOLERANCE_SECONDS

    @staticmethod
    def _clamp_segment(value: float, duration: float) -> float:
        """Keep an intro/outro segment sane: ≥0 and ≤ a third of the clip."""
        upper = max(duration / 3.0, 1.0) if duration > 0 else 10.0
        # To the hundredth, like the measured parts of a filmed take: rounding further would move them at every save.
        return round(min(max(value, 0.0), upper), 2)


presenter_video_service = PresenterVideoService()
