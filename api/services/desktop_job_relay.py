"""
Desktop job relay — work a device without the desktop app leaves for the owner's computer.

Some work only runs on the user's computer: reading Google and Facebook with the computer's Chrome (datacenter
addresses are blocked), filming a site with its Storyblok editor… A tablet or a phone leaves a job here; the
desktop app, which looks for jobs in the background, takes each one, does the work, saves the result through the
usual routes and closes the job. The dashboard follows the job and tells whether the computer is on.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from enums.desktop_job import DesktopJobKind, DesktopJobStatus
from enums.enrichment_status import EnrichmentStatus
from models.desktop_job import DesktopJob
from models.prospect_db import ProspectDB
from services.enrichment_service import enrichment_service

# An enrichment takes about a minute and the desktop app gives it up after four. Past this delay the app is taken
# for closed mid-work, and the job is offered again.
_CLAIM_LIFETIME: timedelta = timedelta(minutes=15)
_MAXIMUM_ERROR_MESSAGE_LENGTH = 1000
_UNFINISHED_STATUSES: tuple[str, ...] = (DesktopJobStatus.WAITING.value, DesktopJobStatus.RUNNING.value)

ALREADY_RUNNING_MESSAGE = "Votre PC fait déjà ce travail."
NOT_WAITING_MESSAGE = "Ce travail n'attend plus le PC."
UNKNOWN_SUBJECT_MESSAGE = "Fiche introuvable."


class DesktopJobRelay:
    """Keeps the jobs waiting for the desktop app, which ones it does, and how they ended."""

    def __init__(self, claim_lifetime: timedelta = _CLAIM_LIFETIME) -> None:
        self._claim_lifetime = claim_lifetime

    def request(self, db: Session, user_id: int, kind: DesktopJobKind, subject_id: int) -> DesktopJob:
        """
        Leave a job for the owner's desktop app, or return the one already waiting for the same work.

        Args:
            db: Active database session.
            user_id: Owner, whose desktop app does the work.
            kind: What to do.
            subject_id: The record the work is about, owned by the user.

        Returns:
            The job, waiting for the desktop app (or already taken by it).

        Raises:
            ValueError: when the record does not exist or is not the user's.
        """
        existing = self.active_job(db, user_id, kind, subject_id)
        if existing is not None:
            return existing
        payload = self._payload_for(db, user_id, kind, subject_id)
        job = DesktopJob(user_id=user_id, kind=kind.value, subject_id=subject_id, payload=payload)
        db.add(job)
        db.flush()
        self._on_requested(db, job)
        db.commit()
        db.refresh(job)
        return job

    def active_job(self, db: Session, user_id: int, kind: DesktopJobKind, subject_id: int) -> DesktopJob | None:
        """
        The unfinished job of a record, if any.

        Args:
            db: Active database session.
            user_id: Owner of the job.
            kind: What the job does.
            subject_id: The record the work is about.

        Returns:
            The waiting or running job, or None.
        """
        return (
            db.query(DesktopJob)
            .filter(
                DesktopJob.user_id == user_id,
                DesktopJob.kind == kind.value,
                DesktopJob.subject_id == subject_id,
                DesktopJob.status.in_(_UNFINISHED_STATUSES),
            )
            .order_by(DesktopJob.requested_at.desc())
            .first()
        )

    def active_jobs(self, db: Session, user_id: int, kind: DesktopJobKind | None = None) -> list[DesktopJob]:
        """
        The user's unfinished jobs, oldest first, for the dashboard to show what waits for the computer.

        Args:
            db: Active database session.
            user_id: Owner of the jobs.
            kind: Only this kind of work, or every kind when None.

        Returns:
            The waiting and running jobs.
        """
        query = db.query(DesktopJob).filter(DesktopJob.user_id == user_id, DesktopJob.status.in_(_UNFINISHED_STATUSES))
        if kind is not None:
            query = query.filter(DesktopJob.kind == kind.value)
        return query.order_by(DesktopJob.requested_at.asc()).all()

    def get_for_user(self, db: Session, user_id: int, job_id: int) -> DesktopJob | None:
        """
        A job owned by the user.

        Args:
            db: Active database session.
            user_id: Owner of the job.
            job_id: The job.

        Returns:
            The job, or None when it does not exist or belongs to someone else.
        """
        return db.query(DesktopJob).filter(DesktopJob.id == job_id, DesktopJob.user_id == user_id).first()

    def waiting_jobs(self, db: Session, user_id: int) -> list[DesktopJob]:
        """
        The jobs a desktop app of the user should take, oldest first: waiting, or abandoned by a closed app.

        Args:
            db: Active database session.
            user_id: Owner of the jobs.

        Returns:
            The jobs no desktop app is doing.
        """
        return [job for job in self.active_jobs(db, user_id) if not self.is_running(job)]

    def is_running(self, job: DesktopJob) -> bool:
        """
        Whether a desktop app took the job recently enough to still be doing it.

        Args:
            job: The job.

        Returns:
            True while the work is taken for running.
        """
        if job.status != DesktopJobStatus.RUNNING.value or job.claimed_at is None:
            return False
        return naive_utc_now() - job.claimed_at <= self._claim_lifetime

    def claim(self, db: Session, job: DesktopJob) -> DesktopJob:
        """
        Record that a desktop app starts the job, so no other look takes it.

        Args:
            db: Active database session.
            job: The job.

        Returns:
            The job, running.

        Raises:
            ValueError: when the job no longer waits, or a desktop app is already doing it.
        """
        if job.status not in _UNFINISHED_STATUSES:
            raise ValueError(NOT_WAITING_MESSAGE)
        if self.is_running(job):
            raise ValueError(ALREADY_RUNNING_MESSAGE)
        job.status = DesktopJobStatus.RUNNING.value
        job.claimed_at = naive_utc_now()
        db.commit()
        db.refresh(job)
        return job

    def complete(self, db: Session, job: DesktopJob) -> DesktopJob:
        """
        Close a job whose result the desktop app saved.

        Args:
            db: Active database session.
            job: The job.

        Returns:
            The job, done.

        Raises:
            ValueError: when the job was already closed.
        """
        if job.status not in _UNFINISHED_STATUSES:
            raise ValueError(NOT_WAITING_MESSAGE)
        job.status = DesktopJobStatus.DONE.value
        job.finished_at = naive_utc_now()
        db.commit()
        db.refresh(job)
        return job

    def fail(self, db: Session, job: DesktopJob, message: str) -> DesktopJob:
        """
        Close a job the desktop app could not do, with the reason the dashboard shows.

        Args:
            db: Active database session.
            job: The job.
            message: Why the desktop app gave up.

        Returns:
            The job, failed.

        Raises:
            ValueError: when the job was already closed.
        """
        if job.status not in _UNFINISHED_STATUSES:
            raise ValueError(NOT_WAITING_MESSAGE)
        job.status = DesktopJobStatus.FAILED.value
        job.error_message = message[:_MAXIMUM_ERROR_MESSAGE_LENGTH]
        job.finished_at = naive_utc_now()
        self._on_failed(db, job)
        db.commit()
        db.refresh(job)
        return job

    def cancel(self, db: Session, job: DesktopJob) -> DesktopJob:
        """
        Withdraw a job before a desktop app takes it.

        Args:
            db: Active database session.
            job: The job.

        Returns:
            The job, cancelled.

        Raises:
            ValueError: when a desktop app is doing it (it would save its result anyway), or it was already closed.
        """
        if job.status not in _UNFINISHED_STATUSES:
            raise ValueError(NOT_WAITING_MESSAGE)
        if self.is_running(job):
            raise ValueError(ALREADY_RUNNING_MESSAGE)
        job.status = DesktopJobStatus.CANCELLED.value
        job.finished_at = naive_utc_now()
        self._on_cancelled(db, job)
        db.commit()
        db.refresh(job)
        return job

    def _payload_for(self, db: Session, user_id: int, kind: DesktopJobKind, subject_id: int) -> dict[str, Any]:
        """
        What the desktop app needs to do the work, read from the record so the asking device sends nothing else.

        Args:
            db: Active database session.
            user_id: Owner of the record.
            kind: What to do.
            subject_id: The record the work is about.

        Returns:
            The payload the desktop app hands to its local tools.

        Raises:
            ValueError: when the record does not exist or is not the user's.
        """
        if kind is DesktopJobKind.PROSPECT_ENRICHMENT:
            prospect = enrichment_service.get_prospect_for_user(db, user_id, subject_id)
            if prospect is None:
                raise ValueError(UNKNOWN_SUBJECT_MESSAGE)
            return self._enrichment_payload(prospect)
        raise ValueError(UNKNOWN_SUBJECT_MESSAGE)

    @staticmethod
    def _enrichment_payload(prospect: ProspectDB) -> dict[str, Any]:
        """
        What the computer's scraper needs to read a prospect's pages (the same fields the desktop drawer sends).

        Args:
            prospect: The prospect to enrich.

        Returns:
            The scraper request.
        """
        return {
            "business_name": prospect.name,
            "city": prospect.city,
            "google_maps_url": prospect.google_maps_url,
            "facebook_url": prospect.facebook_url,
            "country": prospect.country or "FR",
        }

    def _on_requested(self, db: Session, job: DesktopJob) -> None:
        """
        Show the pending work on the record itself, so every screen reads « en cours » without knowing the job.

        Args:
            db: Active database session.
            job: The job just created.
        """
        if job.kind == DesktopJobKind.PROSPECT_ENRICHMENT.value and job.subject_id is not None:
            record = enrichment_service.get_or_create(db, job.user_id, job.subject_id)
            job.payload = {**(job.payload or {}), "previous_status": record.status}
            record.status = EnrichmentStatus.ENRICHING.value
            record.error_message = None

    def _on_failed(self, db: Session, job: DesktopJob) -> None:
        """
        Carry the failure onto the record, where the dashboard already shows enrichment errors.

        Args:
            db: Active database session.
            job: The failed job.
        """
        if job.kind == DesktopJobKind.PROSPECT_ENRICHMENT.value and job.subject_id is not None:
            record = enrichment_service.get_or_create(db, job.user_id, job.subject_id)
            if record.status == EnrichmentStatus.ENRICHING.value:
                record.status = EnrichmentStatus.FAILED.value
                record.error_message = job.error_message

    def _on_cancelled(self, db: Session, job: DesktopJob) -> None:
        """
        Give the record back the status it had before the work was asked.

        Args:
            db: Active database session.
            job: The cancelled job.
        """
        if job.kind == DesktopJobKind.PROSPECT_ENRICHMENT.value and job.subject_id is not None:
            record = enrichment_service.get_or_create(db, job.user_id, job.subject_id)
            if record.status == EnrichmentStatus.ENRICHING.value:
                previous = (job.payload or {}).get("previous_status")
                record.status = previous if isinstance(previous, str) else EnrichmentStatus.PENDING.value


desktop_job_relay = DesktopJobRelay()
