"""
The prospection video, whatever it presents: a demo site or a receptionist.

Both videos are made the same way: the owner's presenter clip full-screen for the intro and the outro, a capture of
the product in the middle, the picture-in-picture montage of :mod:`services.video_montage`, an email thumbnail, and
both files published on R2. :class:`ProspectionVideoService` runs that whole life (request, background render,
publication, failure, reset); its two subclasses only say what the capture films, where the files live and how the
dashboard names the video (:mod:`services.demo_video_service`, :mod:`services.assistant_video_service`).
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, ClassVar, Generic, TypeVar

from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from core.config import settings
from enums.demo_video_status import DemoVideoStatus
from models.ai_assistant import AiAssistant
from models.demo_site import DemoSite
from models.presenter_video import PresenterVideo
from services import video_montage, video_pipeline
from services.r2_storage_service import r2_storage
from services.video_pipeline import GenerationKey, VideoGenerationError

logger = logging.getLogger(__name__)

VideoSubjectT = TypeVar("VideoSubjectT", DemoSite, AiAssistant)

INTERRUPTED_MESSAGE = "Génération interrompue (redémarrage du serveur) — relancez-la."
VIDEO_UPLOAD_FAILED_MESSAGE = "L'envoi de la vidéo sur le stockage a échoué. Relancez la génération."
THUMBNAIL_UPLOAD_FAILED_MESSAGE = (
    "L'envoi de la vignette sur le stockage a échoué : la vidéo a été retirée. Relancez la génération."
)
INVALID_DESKTOP_ARCHIVE_MESSAGE = "Archive vidéo invalide (video.mp4 + thumbnail.jpg attendus)."

_UNFINISHED_STATUSES = (DemoVideoStatus.PENDING.value, DemoVideoStatus.GENERATING.value)
_MAXIMUM_ERROR_MESSAGE_LENGTH = 1000
_CAPTURE_MEMORY_ADVICE = "Générez-la depuis l'application desktop, ou réessayez plus tard."
_MONTAGE_MEMORY_ADVICE = "Réessayez dans quelques minutes."
_DESKTOP_VIDEO_NAME = "video.mp4"
_DESKTOP_THUMBNAIL_NAME = "thumbnail.jpg"


@dataclass(frozen=True)
class CapturedSegment:
    """What a capture hands to the montage: its recording, where the useful part starts, and the thumbnail still."""

    recording_path: Path
    start_seconds: float
    screenshot_path: Path


def reenqueue_campaigns_after_video_ready(db: Session, prospect_id: int | None, user_id: int) -> None:
    """
    Best-effort: pull a prospect into its active campaigns once its prospection video is ready.

    A prospect skipped at campaign launch for lacking a video gets no queue row and nothing
    reconsiders it — the send queue is built once. When the video finishes the prospect can finally
    be emailed, so we re-run the per-prospect enqueue here. Never raises: a queue hiccup must not
    undo a finished video.

    Args:
        db: Active database session.
        prospect_id: The prospect whose video just became ready (None for a site with no prospect).
        user_id: Owner of the prospect's campaigns.
    """
    if not prospect_id:
        return
    try:
        from services.campaign_queue_service import CampaignQueueService

        added: int = CampaignQueueService(db).enqueue_ready_prospect(prospect_id, user_id)
        if added:
            logger.info(
                "[Video] Video ready for prospect %d — auto-enqueued into %d active campaign send(s)",
                prospect_id,
                added,
            )
    except Exception:
        logger.warning("[Video] Auto re-enqueue after video ready failed for prospect %s", prospect_id, exc_info=True)


class ProspectionVideoService(ABC, Generic[VideoSubjectT]):
    """
    Generates, publishes and resets the prospection video of a demo site or a receptionist.

    Attributes:
        subject_model: The model the video belongs to.
        kind: The kind of video in logs and in the generations of this process (``site``, ``assistant``).
        presenter_module: The module of the presenter clip the video uses.
        shown_subject: What the middle of the video shows, as the dashboard names it (« le site »).
        already_running_message: The refusal when a generation is already under way.
        missing_presenter_message: The refusal when the owner has no presenter clip for this kind of video.
        thumbnail_label: The words after « Bonjour {Prénom} » on the email thumbnail.
        pip_corner: The bottom corner of the webcam bubble, clear of what the capture shows.
    """

    subject_model: type[VideoSubjectT]
    kind: ClassVar[str]
    presenter_module: ClassVar[str]
    shown_subject: ClassVar[str]
    already_running_message: ClassVar[str]
    missing_presenter_message: ClassVar[str]
    thumbnail_label: ClassVar[str]
    pip_corner: ClassVar[str]

    def request_generation(self, db: Session, subject: VideoSubjectT, user_id: int) -> VideoSubjectT:
        """
        Validate, mark pending and start the background generation of a video.

        Args:
            db: Active database session (request-scoped).
            subject: The demo site or receptionist, owned by the user.
            user_id: Owner, whose presenter clip the video uses.

        Returns:
            The subject, its ``video_status`` set to ``pending``.

        Raises:
            ValueError: when the subject or the presenter clip is not ready, or a generation is already under way.
        """
        self.ensure_generation_can_start(db, subject, user_id)
        run_key = self._run_key(subject.id)

        subject.video_status = DemoVideoStatus.PENDING.value
        subject.video_error = None
        db.commit()
        db.refresh(subject)

        video_pipeline.generation_runs.start(run_key, self._run_generation(subject.id, user_id))
        return subject

    def ensure_generation_can_start(self, db: Session, subject: VideoSubjectT, user_id: int) -> None:
        """
        Refuse a video that cannot be generated now, wherever it is about to be built (server or desktop app).

        Args:
            db: Active database session.
            subject: The demo site or receptionist, owned by the user.
            user_id: Owner, whose presenter clip the video uses.

        Raises:
            ValueError: when the subject or the presenter clip is not ready, or a generation is already under way.
        """
        from services.presenter_video_service import presenter_video_service

        self._check_can_generate(subject)
        run_key = self._run_key(subject.id)
        if subject.video_status in _UNFINISHED_STATUSES or video_pipeline.generation_runs.is_in_progress(run_key):
            raise ValueError(self.already_running_message)
        presenter = presenter_video_service.get_for_user(db, user_id, self.presenter_module)
        if presenter is None:
            raise ValueError(self.missing_presenter_message)
        middle_seconds = self._middle_seconds(presenter)
        if middle_seconds < video_pipeline.MIN_SCROLL_SECONDS:
            raise ValueError(
                f"Intro + outro trop longues : il reste {middle_seconds:.0f}s pour montrer {self.shown_subject} "
                f"(minimum {video_pipeline.MIN_SCROLL_SECONDS:.0f}s)."
            )

    def maybe_start_auto_generation(self, db: Session, subject: VideoSubjectT, user_id: int) -> bool:
        """
        Best-effort auto-generation hook, called right after a demo site or a receptionist is created.

        Fires only when the user has a presenter clip for this kind of video with ``auto_generate`` enabled; never
        raises (a video failure must not fail the creation).

        Args:
            db: Active database session.
            subject: The freshly created demo site or receptionist.
            user_id: Owner, whose presenter clip the video uses.

        Returns:
            True when a generation was started.
        """
        from services.presenter_video_service import presenter_video_service

        try:
            presenter = presenter_video_service.get_for_user(db, user_id, self.presenter_module)
            if presenter is None or not presenter.auto_generate:
                return False
            self.request_generation(db, subject, user_id)
            logger.info("Auto %s video generation started for slug=%s", self.kind, subject.slug)
            return True
        except ValueError as exc:
            logger.info("Auto %s video generation skipped for slug=%s: %s", self.kind, subject.slug, exc)
            return False
        except Exception:
            logger.exception("Auto %s video generation hook failed for slug=%s", self.kind, subject.slug)
            return False

    def reconcile_orphaned(self, db: Session) -> int:
        """
        Fail the unfinished videos no generation of this process can finish, and abandon the ones rendering too long.

        A generation lives only in memory: after a restart (crash, OOM kill, deploy) its video would stay pending
        forever, and :meth:`request_generation` refuses to restart it. A render stuck for more than
        ``video_pipeline.MAXIMUM_GENERATION_MINUTES`` is cancelled. Run at startup, then periodically
        (:mod:`services.video_generation_watchdog`).

        Args:
            db: Active database session.

        Returns:
            The number of videos marked failed.
        """
        unfinished: list[VideoSubjectT] = (
            db.query(self.subject_model).filter(self.subject_model.video_status.in_(_UNFINISHED_STATUSES)).all()
        )
        overrun_keys: list[GenerationKey] = []
        failed_count = 0
        for subject in unfinished:
            run_key = self._run_key(subject.id)
            if not video_pipeline.generation_runs.is_in_progress(run_key):
                failure_message = INTERRUPTED_MESSAGE
            elif video_pipeline.generation_runs.has_overrun(run_key, video_pipeline.MAXIMUM_GENERATION_SECONDS):
                failure_message = video_pipeline.GENERATION_OVERRUN_MESSAGE
                overrun_keys.append(run_key)
            else:
                continue
            subject.video_status = DemoVideoStatus.FAILED.value
            subject.video_error = failure_message
            failed_count += 1
        if failed_count:
            db.commit()
        for run_key in overrun_keys:
            video_pipeline.generation_runs.cancel(run_key)
        return failed_count

    def purge_video(self, subject: VideoSubjectT) -> None:
        """
        Abandon a generation under way, delete the video's files and reset its state, left for the caller to commit.

        Args:
            subject: The demo site or receptionist.
        """
        video_pipeline.generation_runs.cancel(self._run_key(subject.id))
        self._delete_files(subject.slug)
        subject.video_status = None
        subject.video_error = None
        subject.video_generated_at = None

    def clear_video(self, db: Session, subject: VideoSubjectT) -> VideoSubjectT:
        """
        Delete the generated video files and reset the video's state.

        Args:
            db: Active database session.
            subject: The demo site or receptionist.

        Returns:
            The subject, without a video.
        """
        self.purge_video(subject)
        db.commit()
        db.refresh(subject)
        return subject

    async def store_desktop_video(self, db: Session, subject: VideoSubjectT, archive: BinaryIO) -> VideoSubjectT:
        """
        Publish a video the desktop app rendered, then mark it ready.

        The sidecar montages the whole clip on the PC and sends a zip of ``video.mp4`` + ``thumbnail.jpg``: the VPS
        only stores them.

        Args:
            db: Active database session.
            subject: The demo site or receptionist, owned by the caller.
            archive: The uploaded zip.

        Returns:
            The subject, its video ready.

        Raises:
            ValueError: when the archive does not hold both files (nothing changes then).
            VideoGenerationError: when the storage refused them (the video is then marked failed).
        """
        slug = subject.slug
        work_dir = Path(tempfile.mkdtemp(prefix=f"{self.kind}-video-final-{slug}-"))
        try:
            video_path, thumbnail_path = self._unpack_desktop_archive(archive, work_dir)
            await self._publish(slug, video_path, thumbnail_path)
        except VideoGenerationError as exc:
            self._record_failure(db, subject, str(exc), slug)
            raise
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
        self._mark_ready(db, subject)
        reenqueue_campaigns_after_video_ready(db, subject.prospect_id, subject.user_id)
        return subject

    @abstractmethod
    def _check_can_generate(self, subject: VideoSubjectT) -> None:
        """
        Refuse a subject whose video cannot be made (not active, no public page…).

        Args:
            subject: The demo site or receptionist.

        Raises:
            ValueError: with the reason the dashboard shows.
        """

    @abstractmethod
    async def _capture_middle(self, subject: VideoSubjectT, middle_seconds: float, work_dir: Path) -> CapturedSegment:
        """
        Film the middle of the video (blocking work runs off the event loop).

        Args:
            subject: The demo site or receptionist.
            middle_seconds: The time between the intro and the outro of the presenter clip.
            work_dir: The generation's temporary folder.

        Returns:
            The recording and its thumbnail still.

        Raises:
            VideoGenerationError: when the capture fails.
        """

    @abstractmethod
    def _video_key(self, slug: str) -> str:
        """
        The R2 key of the video.

        Args:
            slug: The subject's slug.

        Returns:
            The object key.
        """

    @abstractmethod
    def _thumbnail_key(self, slug: str) -> str:
        """
        The R2 key of the email thumbnail.

        Args:
            slug: The subject's slug.

        Returns:
            The object key.
        """

    @abstractmethod
    def _delete_files(self, slug: str) -> None:
        """
        Delete every R2 file of the video (best effort, never raises).

        Args:
            slug: The subject's slug.
        """

    async def _run_generation(self, subject_id: int, user_id: int) -> None:
        """
        Background task: wait for the render slot, then generate the video in a database session of its own.

        Args:
            subject_id: The demo site or receptionist.
            user_id: Owner, whose presenter clip the video uses.
        """
        from core.database import SessionLocal

        async with video_pipeline.generation_semaphore:
            db: Session = SessionLocal()
            try:
                subject = db.query(self.subject_model).filter(self.subject_model.id == subject_id).first()
                # Reset, deleted or published from the desktop while it waited: nothing left to generate.
                if subject is None or subject.video_status != DemoVideoStatus.PENDING.value:
                    return
                video_pipeline.generation_runs.mark_rendering(self._run_key(subject_id))
                await self._generate_and_record(db, subject, user_id)
            finally:
                db.close()

    async def _generate_and_record(self, db: Session, subject: VideoSubjectT, user_id: int) -> None:
        """
        Render and publish the video, then record the outcome: every failure ends in ``failed`` with its reason.

        Args:
            db: The generation's database session.
            subject: The demo site or receptionist, pending.
            user_id: Owner, whose presenter clip the video uses.
        """
        from services.presenter_video_service import presenter_video_service

        slug = subject.slug
        try:
            presenter = presenter_video_service.get_for_user(db, user_id, self.presenter_module)
            if presenter is None:
                raise VideoGenerationError(self.missing_presenter_message)
            subject.video_status = DemoVideoStatus.GENERATING.value
            db.commit()
            has_published = await self._render_and_publish(db, subject, presenter, user_id)
            if not has_published:
                logger.info("The %s video of slug=%s was reset while it rendered: nothing published", self.kind, slug)
                return
            self._mark_ready(db, subject)
        except VideoGenerationError as exc:
            logger.warning("%s video generation failed for slug=%s: %s", self.kind.capitalize(), slug, exc)
            self._record_failure(db, subject, str(exc), slug)
            return
        except Exception as exc:
            logger.exception("%s video generation crashed for slug=%s", self.kind.capitalize(), slug)
            self._record_failure(db, subject, f"Erreur inattendue : {exc}", slug)
            return
        logger.info("Prospection video ready for %s slug=%s", self.kind, slug)
        # A video-only campaign skipped this prospect at launch: the finished video lets it in now.
        reenqueue_campaigns_after_video_ready(db, subject.prospect_id, user_id)

    async def _render_and_publish(
        self, db: Session, subject: VideoSubjectT, presenter: PresenterVideo, user_id: int
    ) -> bool:
        """
        Capture the middle, compose the video and its thumbnail, then publish both on R2.

        Args:
            db: The generation's database session.
            subject: The demo site or receptionist, generating.
            presenter: The owner's presenter clip.
            user_id: Owner of the presenter clip and photo.

        Returns:
            True once published; False when the video was reset or deleted while it rendered (nothing is published).

        Raises:
            VideoGenerationError: when a step fails, with the message the dashboard shows.
        """
        first_name = video_pipeline.resolve_first_name(db, subject.prospect_id)
        work_dir = Path(tempfile.mkdtemp(prefix=f"{self.kind}-video-{subject.slug}-"))
        try:
            presenter_path = await video_pipeline.resolve_presenter_file(presenter, work_dir)
            presenter_photo_path = await video_pipeline.resolve_presenter_photo(db, user_id, work_dir)
            middle_seconds = self._middle_seconds(presenter)
            segment = await self._capture_middle(subject, middle_seconds, work_dir)
            output_path = work_dir / "output.mp4"
            thumbnail_path = work_dir / "thumbnail.jpg"
            self._guard_montage_memory()
            try:
                await asyncio.to_thread(
                    video_montage.compose_final,
                    ffmpeg_path=settings.ffmpeg_path,
                    presenter_duration=presenter.duration_seconds,
                    presenter_intro=presenter.intro_seconds,
                    presenter_outro=presenter.outro_seconds,
                    presenter_path=presenter_path,
                    capture_path=segment.recording_path,
                    scroll_offset=segment.start_seconds,
                    scroll_seconds=middle_seconds,
                    first_name=first_name,
                    screenshot_path=segment.screenshot_path,
                    output_video=output_path,
                    output_thumbnail=thumbnail_path,
                    presenter_photo_path=presenter_photo_path,
                    thumbnail_label=self.thumbnail_label,
                    pip_corner=self.pip_corner,
                )
            except video_montage.VideoMontageError as exc:
                raise VideoGenerationError(str(exc)) from exc
            if not self._is_still_generating(db, subject):
                return False
            await self._publish(subject.slug, output_path, thumbnail_path)
            return True
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    async def _publish(self, slug: str, video_path: Path, thumbnail_path: Path) -> None:
        """
        Upload the video, then its thumbnail; when the thumbnail fails, take the video back down.

        Args:
            slug: The subject's slug.
            video_path: The finished mp4.
            thumbnail_path: The email thumbnail.

        Raises:
            VideoGenerationError: when an upload fails, nothing of the new video being left online.
        """
        video_key = self._video_key(slug)
        thumbnail_key = self._thumbnail_key(slug)
        try:
            await r2_storage.upload_file_async(video_path, video_key, "video/mp4")
        except Exception as exc:
            logger.warning("[Video] %s video upload failed for slug=%s", self.kind, slug, exc_info=True)
            raise VideoGenerationError(VIDEO_UPLOAD_FAILED_MESSAGE) from exc
        try:
            await r2_storage.upload_file_async(thumbnail_path, thumbnail_key, "image/jpeg")
        except Exception as exc:
            logger.warning("[Video] %s thumbnail upload failed for slug=%s", self.kind, slug, exc_info=True)
            # The new video would stay online without its thumbnail, or under the previous one.
            await self._withdraw_files(slug, [video_key, thumbnail_key])
            raise VideoGenerationError(THUMBNAIL_UPLOAD_FAILED_MESSAGE) from exc

    async def _withdraw_files(self, slug: str, keys: list[str]) -> None:
        """
        Delete what a failed publication left on R2 (best effort: a storage error is logged, never raised).

        Args:
            slug: The subject's slug, for the log.
            keys: The objects to delete.
        """
        try:
            await asyncio.to_thread(r2_storage.delete_many, keys)
        except Exception:
            logger.warning("[Video] could not withdraw the %s video files of slug=%s", self.kind, slug, exc_info=True)

    def _run_key(self, subject_id: int) -> GenerationKey:
        """
        The key of a video among the generations of this process.

        Args:
            subject_id: The demo site or receptionist.

        Returns:
            The kind of video and the subject's id.
        """
        return (self.kind, subject_id)

    @staticmethod
    def _middle_seconds(presenter: PresenterVideo) -> float:
        """
        The time the capture fills: the presenter clip without its intro and its outro.

        Args:
            presenter: The owner's presenter clip.

        Returns:
            The middle's duration in seconds.
        """
        return presenter.duration_seconds - presenter.intro_seconds - presenter.outro_seconds

    @staticmethod
    def _guard_capture_memory() -> None:
        """
        Refuse a server-side headless capture when the box is low on memory: an OOM kill takes the API down.

        Raises:
            VideoGenerationError: when available memory is below the capture floor.
        """
        video_pipeline.guard_memory(video_pipeline.MIN_FREE_MEMORY_MB_FOR_CAPTURE, "générer", _CAPTURE_MEMORY_ADVICE)

    @staticmethod
    def _guard_montage_memory() -> None:
        """
        Refuse the ffmpeg montage when the box is low on memory: it runs on the VPS even in the desktop path.

        Raises:
            VideoGenerationError: when available memory is below the montage floor.
        """
        video_pipeline.guard_memory(video_pipeline.MIN_FREE_MEMORY_MB_FOR_MONTAGE, "assembler", _MONTAGE_MEMORY_ADVICE)

    @staticmethod
    def _is_still_generating(db: Session, subject: VideoSubjectT) -> bool:
        """
        Whether the video is still expected: no reset, expiry or deletion happened while it rendered.

        Args:
            db: The generation's database session.
            subject: The demo site or receptionist.

        Returns:
            True when its row still says ``generating``.
        """
        db.refresh(subject)
        return subject.video_status == DemoVideoStatus.GENERATING.value

    @staticmethod
    def _mark_ready(db: Session, subject: VideoSubjectT) -> None:
        """
        Mark the video ready, dated in naive UTC like every stored instant.

        Args:
            db: Active database session.
            subject: The demo site or receptionist.
        """
        subject.video_status = DemoVideoStatus.READY.value
        subject.video_error = None
        subject.video_generated_at = naive_utc_now()
        db.commit()
        db.refresh(subject)

    @staticmethod
    def _record_failure(db: Session, subject: VideoSubjectT, message: str, slug: str) -> None:
        """
        Mark the video failed with the reason the dashboard shows; a database error here is logged, never raised.

        Args:
            db: Active database session, possibly left unusable by the failure.
            subject: The demo site or receptionist.
            message: The reason.
            slug: The subject's slug, for the log.
        """
        try:
            db.rollback()
            subject.video_status = DemoVideoStatus.FAILED.value
            subject.video_error = message[:_MAXIMUM_ERROR_MESSAGE_LENGTH]
            db.commit()
        except Exception:
            logger.exception("[Video] could not record the failed video of slug=%s", slug)

    @staticmethod
    def _unpack_desktop_archive(archive: BinaryIO, work_dir: Path) -> tuple[Path, Path]:
        """
        Extract ``video.mp4`` and ``thumbnail.jpg`` from the zip the desktop app sends.

        Args:
            archive: The uploaded zip.
            work_dir: The temporary folder receiving the files.

        Returns:
            The video and thumbnail paths.

        Raises:
            ValueError: when the archive is not a zip holding both files.
        """
        zip_path = work_dir / "bundle.zip"
        with zip_path.open("wb") as buffer:
            shutil.copyfileobj(archive, buffer)
        video_path = work_dir / _DESKTOP_VIDEO_NAME
        thumbnail_path = work_dir / _DESKTOP_THUMBNAIL_NAME
        try:
            with zipfile.ZipFile(zip_path) as bundle:
                video_path.write_bytes(bundle.read(_DESKTOP_VIDEO_NAME))
                thumbnail_path.write_bytes(bundle.read(_DESKTOP_THUMBNAIL_NAME))
        except (zipfile.BadZipFile, KeyError) as exc:
            raise ValueError(INVALID_DESKTOP_ARCHIVE_MESSAGE) from exc
        return video_path, thumbnail_path
