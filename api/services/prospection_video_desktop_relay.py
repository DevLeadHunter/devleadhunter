"""
Desktop relay of the prospection videos — every video, of a demo site or a receptionist, is built by the owner's PC.

The server renders nothing: only the desktop app can film a site together with its Storyblok editor, and it montages
the clips without loading the server. Any device leaves a request on the site or the receptionist; the desktop app,
which looks for requests in the background, takes each one, builds the video and publishes it. A site waits for its
Storyblok space before it is handed over.
"""

from __future__ import annotations

import logging
from typing import Generic

from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from enums.demo_video_status import DemoVideoStatus
from services.assistant_video_service import assistant_video_service
from services.demo_video_service import demo_video_service
from services.presenter_video_service import presenter_video_service
from services.prospection_video_service import (
    ALREADY_BUILDING_MESSAGE,
    MAXIMUM_ERROR_MESSAGE_LENGTH,
    ProspectionVideoService,
    VideoSubjectT,
)

logger = logging.getLogger(__name__)

NO_REQUEST_MESSAGE = "Aucune demande de vidéo n'attend l'ordinateur."


class ProspectionVideoDesktopRelay(Generic[VideoSubjectT]):
    """Keeps the videos of one kind (demo sites or receptionists) waiting for the desktop app, and hands them over."""

    def __init__(self, video_service: ProspectionVideoService[VideoSubjectT]) -> None:
        """
        Relay the videos of one kind.

        Args:
            video_service: The video service of that kind, which checks the video and knows the builds under way.
        """
        self._video_service = video_service

    def request(self, db: Session, subject: VideoSubjectT, user_id: int) -> VideoSubjectT:
        """
        Leave a video request for the owner's desktop app.

        Args:
            db: Active database session.
            subject: The demo site or receptionist, owned by the user.
            user_id: Owner, whose presenter clip the video uses.

        Returns:
            The subject, waiting for the desktop app. A video already published stays online meanwhile.

        Raises:
            ValueError: when the video cannot be asked now (subject not ready, no presenter clip, build under way).
        """
        self._video_service.ensure_generation_can_start(db, subject, user_id)
        subject.video_desktop_requested_at = naive_utc_now()
        db.commit()
        db.refresh(subject)
        self._video_service.forget_desktop_build(subject)
        return subject

    def request_if_auto_generating(self, db: Session, subject: VideoSubjectT, user_id: int) -> bool:
        """
        Leave a request for a freshly created demo site or receptionist when its module's take generates on its own.

        Fires only when the user has a presenter clip for this kind of video with ``auto_generate`` enabled; never
        raises (a video problem must not fail the creation). A site without its Storyblok space yet still gets its
        request, which waits for the space.

        Args:
            db: Active database session.
            subject: The freshly created demo site or receptionist.
            user_id: Owner, whose presenter clip the video uses.

        Returns:
            True when a request was left.
        """
        try:
            presenter = presenter_video_service.get_for_user(db, user_id, self._video_service.presenter_module)
            if presenter is None or not presenter.auto_generate:
                return False
            self.request(db, subject, user_id)
            logger.info("Auto %s video asked from the desktop app for slug=%s", self._video_service.kind, subject.slug)
            return True
        except ValueError as exc:
            logger.info("Auto %s video skipped for slug=%s: %s", self._video_service.kind, subject.slug, exc)
            return False
        except Exception:
            logger.exception("Auto %s video hook failed for slug=%s", self._video_service.kind, subject.slug)
            return False

    def clear_request(self, db: Session, subject: VideoSubjectT) -> VideoSubjectT:
        """
        Close a request: withdrawn by the user, or fulfilled.

        Args:
            db: Active database session.
            subject: The demo site or receptionist.

        Returns:
            The subject, without a waiting request.
        """
        self._video_service.forget_desktop_build(subject)
        if subject.video_desktop_requested_at is not None:
            subject.video_desktop_requested_at = None
            db.commit()
            db.refresh(subject)
        return subject

    def waiting_subjects(self, db: Session, user_id: int) -> list[VideoSubjectT]:
        """
        The user's videos the desktop app can build now, oldest request first.

        Args:
            db: Active database session.
            user_id: Owner of the demo sites or receptionists.

        Returns:
            The requested subjects ready to be filmed that no desktop app is building.
        """
        subject_model = self._video_service.subject_model
        requested: list[VideoSubjectT] = (
            db.query(subject_model)
            .filter(subject_model.user_id == user_id, subject_model.video_desktop_requested_at.is_not(None))
            .order_by(subject_model.video_desktop_requested_at.asc(), subject_model.id.asc())
            .all()
        )
        return [
            subject
            for subject in requested
            if self._video_service.is_ready_to_film(subject)
            and not self._video_service.is_desktop_build_started(subject)
        ]

    def claim(self, subject: VideoSubjectT) -> None:
        """
        Record that a desktop app starts building the video, so no other look takes it.

        Args:
            subject: The demo site or receptionist.

        Raises:
            ValueError: when no request waits for this video, or a desktop app is already building it.
        """
        if subject.video_desktop_requested_at is None:
            raise ValueError(NO_REQUEST_MESSAGE)
        if self._video_service.is_desktop_build_started(subject):
            raise ValueError(ALREADY_BUILDING_MESSAGE)
        self._video_service.mark_desktop_build_started(subject)

    def record_failure(self, db: Session, subject: VideoSubjectT, message: str) -> VideoSubjectT:
        """
        Close a request the desktop app could not fulfil, with the reason the dashboard shows.

        Args:
            db: Active database session.
            subject: The demo site or receptionist.
            message: Why the desktop app gave up.

        Returns:
            The subject: marked failed, unless a video already published stays valid.

        Raises:
            ValueError: when no request waits for this video.
        """
        if subject.video_desktop_requested_at is None:
            raise ValueError(NO_REQUEST_MESSAGE)
        self._video_service.forget_desktop_build(subject)
        subject.video_desktop_requested_at = None
        subject.video_error = message[:MAXIMUM_ERROR_MESSAGE_LENGTH]
        if subject.video_status != DemoVideoStatus.READY.value:
            subject.video_status = DemoVideoStatus.FAILED.value
        db.commit()
        db.refresh(subject)
        return subject


demo_video_desktop_relay = ProspectionVideoDesktopRelay(demo_video_service)
assistant_video_desktop_relay = ProspectionVideoDesktopRelay(assistant_video_service)
