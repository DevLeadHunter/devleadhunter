"""
The prospection video, whatever it presents: a demo site or a receptionist.

Both videos are made the same way, by the owner's PC: the owner's presenter clip full-screen for the intro and the
outro, a capture of the product in the middle, the picture-in-picture montage of :mod:`services.video_montage`, an
email thumbnail, and both files published on R2. :class:`ProspectionVideoService` runs that whole life on the server
(the checks before the PC is asked, the builds it took, publication, failure, reset); its two subclasses only say what
the capture needs, where the files live and how the dashboard names the video (:mod:`services.demo_video_service`,
:mod:`services.assistant_video_service`).
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
import zipfile
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, ClassVar, Generic, TypeVar

from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from enums.demo_video_status import DemoVideoStatus
from models.ai_assistant import AiAssistant
from models.demo_site import DemoSite
from models.presenter_video import PresenterVideo
from services import video_pipeline
from services.presenter_video_service import presenter_video_service
from services.r2_storage_service import r2_storage
from services.video_pipeline import GenerationKey, VideoGenerationError

logger = logging.getLogger(__name__)

VideoSubjectT = TypeVar("VideoSubjectT", DemoSite, AiAssistant)

VIDEO_UPLOAD_FAILED_MESSAGE = "L'envoi de la vidéo sur le stockage a échoué. Relancez la génération."
THUMBNAIL_UPLOAD_FAILED_MESSAGE = (
    "L'envoi de la vignette sur le stockage a échoué : la vidéo a été retirée. Relancez la génération."
)
INVALID_DESKTOP_ARCHIVE_MESSAGE = "Archive vidéo invalide (video.mp4 + thumbnail.jpg attendus)."
ALREADY_BUILDING_MESSAGE = "L'ordinateur génère déjà cette vidéo."

_MAXIMUM_ERROR_MESSAGE_LENGTH = 1000
_DESKTOP_VIDEO_NAME = "video.mp4"
_DESKTOP_THUMBNAIL_NAME = "thumbnail.jpg"


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
    Checks, publishes and resets the prospection video of a demo site or a receptionist, which the owner's PC builds.

    Attributes:
        subject_model: The model the video belongs to.
        kind: The kind of video in logs and in the builds the desktop apps took (``site``, ``assistant``).
        presenter_module: The module of the presenter clip the video uses.
        shown_subject: What the middle of the video shows, as the dashboard names it (« le site »).
        missing_presenter_message: The refusal when the owner has no presenter clip for this kind of video.
    """

    subject_model: type[VideoSubjectT]
    kind: ClassVar[str]
    presenter_module: ClassVar[str]
    shown_subject: ClassVar[str]
    missing_presenter_message: ClassVar[str]

    def ensure_generation_can_start(self, db: Session, subject: VideoSubjectT, user_id: int) -> None:
        """
        Refuse a video that cannot be asked from the owner's PC now.

        Args:
            db: Active database session.
            subject: The demo site or receptionist, owned by the user.
            user_id: Owner, whose presenter clip the video uses.

        Raises:
            ValueError: when the subject or the presenter clip is not ready, or the PC is already building the video.
        """
        self._check_can_generate(subject)
        if self.is_desktop_build_started(subject):
            raise ValueError(ALREADY_BUILDING_MESSAGE)
        presenter = presenter_video_service.get_for_user(db, user_id, self.presenter_module)
        if presenter is None:
            raise ValueError(self.missing_presenter_message)
        middle_seconds = self._middle_seconds(presenter)
        if middle_seconds < video_pipeline.MIN_SCROLL_SECONDS:
            raise ValueError(
                f"Intro + outro trop longues : il reste {middle_seconds:.0f}s pour montrer {self.shown_subject} "
                f"(minimum {video_pipeline.MIN_SCROLL_SECONDS:.0f}s)."
            )

    def is_ready_to_film(self, subject: VideoSubjectT) -> bool:
        """
        Whether the desktop app can film the subject now: the request on a subject that is not ready waits.

        Args:
            subject: The demo site or receptionist.

        Returns:
            True when nothing the capture needs is missing.
        """
        try:
            self._check_can_generate(subject)
        except ValueError:
            return False
        return True

    def is_desktop_build_started(self, subject: VideoSubjectT) -> bool:
        """
        Whether a desktop app took the subject's request recently enough to still be building its video.

        Args:
            subject: The demo site or receptionist.

        Returns:
            True while the build is taken for running.
        """
        if subject.video_desktop_requested_at is None:
            return False
        return video_pipeline.desktop_video_builds.is_running(self._build_key(subject.id))

    def mark_desktop_build_started(self, subject: VideoSubjectT) -> None:
        """
        Record that a desktop app starts building the subject's video.

        Args:
            subject: The demo site or receptionist.
        """
        video_pipeline.desktop_video_builds.start(self._build_key(subject.id))

    def forget_desktop_build(self, subject: VideoSubjectT) -> None:
        """
        Forget the build a desktop app took for the subject: published, given up, withdrawn or asked again.

        Args:
            subject: The demo site or receptionist.
        """
        video_pipeline.desktop_video_builds.forget(self._build_key(subject.id))

    def clip_in_use_since(self, db: Session, user_id: int) -> datetime | None:
        """
        Since when the module's presenter clip in use is the one the videos are built with.

        Args:
            db: Active database session.
            user_id: Owner of the presenter clips.

        Returns:
            The moment that clip was chosen, or None while the module has no clip.
        """
        presenter = presenter_video_service.get_for_user(db, user_id, self.presenter_module)
        return presenter.in_use_since if presenter is not None else None

    @staticmethod
    def is_made_with_older_clip(subject: VideoSubjectT, clip_in_use_since: datetime | None) -> bool:
        """
        Whether the subject's published video was made before the module's presenter clip in use was chosen.

        Args:
            subject: The demo site or receptionist.
            clip_in_use_since: Since when the module's clip in use is the one (:meth:`clip_in_use_since`).

        Returns:
            True for a ready video older than the clip in use.
        """
        if subject.video_status != DemoVideoStatus.READY.value or subject.video_generated_at is None:
            return False
        return clip_in_use_since is not None and subject.video_generated_at < clip_in_use_since

    def purge_video(self, subject: VideoSubjectT) -> None:
        """
        Delete the video's files and reset its state, left for the caller to commit.

        Args:
            subject: The demo site or receptionist.
        """
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

    def _build_key(self, subject_id: int) -> GenerationKey:
        """
        The key of a video among the builds the desktop apps took.

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
