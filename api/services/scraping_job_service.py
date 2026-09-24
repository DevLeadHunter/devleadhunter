"""
Scraping job service for managing async scraping tasks.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime
from uuid import uuid4

from core.database import SessionLocal
from enums.country import normalize_country
from enums.website_status import WebsiteStatus
from models.prospect import Prospect, ProspectCreate
from models.scraping_job import JobStatus, ScrapingJob, ScrapingJobCreate
from services.enrichment_service import enrichment_service
from services.facebook_exclusion_service import facebook_exclusion_service
from services.organization_service import organization_service
from services.prospect_service import prospect_service
from services.scrape_progress import ScrapeProgressReporter
from services.scraper_service import scraper_service
from services.scraping_job_stream_hub import scraping_job_stream_hub
from services.website_equipment_service import website_equipment_service

logger = logging.getLogger(__name__)

MAX_JOB_LOGS = 300


class ScrapingJobService:
    """Service for managing scraping jobs with live WebSocket progress."""

    def __init__(self) -> None:
        self._jobs: dict[str, ScrapingJob] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}
        # Per-job cooperative cancellation flags. A threading.Event is used
        # because should_stop() is polled from the scraper (nodriver) thread.
        self._cancel_events: dict[str, threading.Event] = {}

    def create_job(self, user_id: int, job_data: ScrapingJobCreate) -> ScrapingJob:
        job_id = f"job_{uuid4().hex[:12]}"
        job = ScrapingJob(
            id=job_id,
            user_id=user_id,
            status=JobStatus.PENDING,
            category=job_data.category,
            city=job_data.city,
            country=normalize_country(job_data.country),
            max_results=job_data.max_results,
            source=job_data.source,
            skip_duplicates=job_data.skip_duplicates,
            only_without_website=job_data.only_without_website,
            parent_job_id=job_data.parent_job_id,
        )
        self._jobs[job_id] = job
        logger.info("Created job %s for user %s", job_id, user_id)
        return job

    def get_job(self, job_id: str) -> ScrapingJob | None:
        return self._jobs.get(job_id)

    def get_user_jobs(self, user_id: int) -> list[ScrapingJob]:
        return [job for job in self._jobs.values() if job.user_id == user_id]

    async def _append_log(self, job: ScrapingJob, message: str) -> None:
        timestamp = datetime.utcnow().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        job.logs.append(line)
        if len(job.logs) > MAX_JOB_LOGS:
            job.logs = job.logs[-MAX_JOB_LOGS:]
        await scraping_job_stream_hub.broadcast(job.id, {"type": "log", "message": line})

    async def _emit_progress(self, job: ScrapingJob) -> None:
        await scraping_job_stream_hub.broadcast(
            job.id,
            {
                "type": "progress",
                "current": job.progress.current,
                "total": job.progress.total,
                "percentage": job.progress.percentage,
                "current_prospect": job.progress.current_prospect,
                "estimated_time_remaining": job.progress.estimated_time_remaining,
            },
        )

    async def execute_job(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            logger.error("Job %s not found", job_id)
            return

        db = SessionLocal()
        saved_count = 0
        skipped_count = 0
        seen_keys: set[tuple[str, str]] = set()
        # Saved prospects with a live site: scanned for a chat widget / contact form once the job ends.
        live_site_ids: list[int] = []
        start_time = time.time()
        stop_scraping = False
        state_lock = threading.Lock()
        main_loop = asyncio.get_running_loop()
        # Cooperative cancellation: cancel_job() sets this event; the scraper
        # stops gracefully at the next should_stop() check.
        cancel_event = self._cancel_events.setdefault(job_id, threading.Event())
        # Facebook overshoot: the match filter (email present, website per the checkbox)
        # only runs AFTER the desktop enrichment reads each page, so the job gathers more
        # candidates than asked — the desktop keeps the first max_results matches and
        # removes the rest. Candidates are internal plumbing: the user asked for N usable
        # prospects, so for Facebook the journal and progress stay quiet about candidates
        # (the desktop match loop reports usable-prospect progress instead).
        is_facebook = (job.source or "").lower() == "facebook"
        save_cap = job.max_results * 3 if is_facebook else job.max_results

        async def on_log(message: str) -> None:
            await self._append_log(job, message)

        async def on_prospect(prospect_data: ProspectCreate) -> None:
            nonlocal saved_count, skipped_count, stop_scraping
            with state_lock:
                if stop_scraping or cancel_event.is_set() or saved_count >= save_cap:
                    stop_scraping = True
                    return

            # Stamped at the single save chokepoint so no scraper has to carry the field itself.
            prospect_data.country = job.country

            key = (prospect_data.name.lower(), (prospect_data.city or "").lower())
            if key in seen_keys:
                return
            seen_keys.add(key)

            fb_url = (prospect_data.facebook_url or "").strip()
            if fb_url:
                # Pages already rejected by the match filter are never re-tested —
                # each test costs a full desktop enrichment of the page. Quiet skip:
                # candidates are internal, the user never asked to hear about them.
                if facebook_exclusion_service.is_excluded(db, job.user_id, fb_url):
                    job.known_pages_skipped += 1
                    logger.info("Job %s: candidate skipped (excluded page) %s", job_id, fb_url)
                    return
                # Page-URL duplicate check — sharper than name+city for Facebook, whose
                # names come from SERP titles and vary from one search to the next.
                if job.skip_duplicates and await prospect_service.facebook_url_exists(db, fb_url, job.user_id):
                    skipped_count += 1
                    job.skipped_duplicates = skipped_count
                    await scraping_job_stream_hub.broadcast(
                        job.id,
                        {"type": "duplicate_skipped", "name": prospect_data.name},
                    )
                    return

            if not is_facebook:
                job.progress.current_prospect = prospect_data.name
                await self._emit_progress(job)

            if job.skip_duplicates:
                is_duplicate = await prospect_service.check_duplicate(
                    db=db,
                    name=prospect_data.name,
                    city=prospect_data.city,
                    user_id=job.user_id,
                )
                if is_duplicate:
                    skipped_count += 1
                    job.skipped_duplicates = skipped_count
                    if not is_facebook:
                        await self._append_log(job, f"Doublon ignoré : {prospect_data.name}")
                    await scraping_job_stream_hub.broadcast(
                        job.id,
                        {"type": "duplicate_skipped", "name": prospect_data.name},
                    )
                    return

            try:
                created = await prospect_service.create_prospect(
                    db=db,
                    prospect=prospect_data,
                    user_id=job.user_id,
                    organization_id=organization_service.user_org_id(db, job.user_id),
                )
            except Exception as exc:
                logger.error("Job %s: failed to save %s: %s", job_id, prospect_data.name, exc)
                await self._append_log(job, f"Erreur enregistrement {prospect_data.name}: {exc}")
                return

            saved_count += 1
            job.results.append(created.id)
            prospect_payload = Prospect.model_validate(created).model_dump(mode="json")
            # The match loop reads the candidates from here even in quiet Facebook mode.
            job.live_prospects.append(prospect_payload)

            if is_facebook:
                # Candidate saved silently: no journal line, no prospect broadcast, no
                # per-candidate progress — and no contact resolution either (it runs
                # during the match enrichment, and most candidates get discarded).
                logger.info("Job %s: facebook candidate %s saved (%d)", job_id, created.name, saved_count)
            else:
                # Decision-maker name resolves in the background while the job keeps scraping.
                enrichment_service.schedule_contact_resolution([created.id])
                if created.website_status == WebsiteStatus.LIVE.value:
                    live_site_ids.append(created.id)
                job.progress.current = saved_count
                job.progress.total = max(job.progress.total, save_cap)
                job.progress.percentage = min(100.0, (saved_count / save_cap) * 100)

                elapsed = time.time() - start_time
                if saved_count > 0:
                    avg = elapsed / saved_count
                    job.progress.estimated_time_remaining = int(avg * max(save_cap - saved_count, 0))

                await scraping_job_stream_hub.broadcast(
                    job.id,
                    {"type": "prospect", "prospect": prospect_payload},
                )
                await self._append_log(job, f"Prospect ajouté : {created.name} ({created.city or '—'})")
                await self._emit_progress(job)

            if saved_count >= save_cap:
                with state_lock:
                    stop_scraping = True

        progress = ScrapeProgressReporter(
            on_log=on_log,
            on_prospect=on_prospect,
            main_loop=main_loop,
        )

        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.utcnow()
            # The user-facing total is what was asked; the Facebook overshoot stays internal.
            job.progress.total = job.max_results
            await self._append_log(
                job,
                f"Démarrage — {job.category or '?'} à {job.city or '?'} "
                f"(max {job.max_results}, source={job.source or 'all'})",
            )
            await self._emit_progress(job)
            # Let the client WebSocket connect before nodriver work starts.
            await asyncio.sleep(0.05)

            def should_stop() -> bool:
                if cancel_event.is_set():
                    return True
                with state_lock:
                    return stop_scraping or saved_count >= save_cap

            await scraper_service.scrape_all(
                category=job.category or "",
                city=job.city or "",
                max_results=save_cap,
                country=job.country,
                source_filter=job.source,
                only_without_website=job.only_without_website,
                progress=progress,
                should_stop=should_stop,
                user_id=job.user_id,
            )

            cancelled = cancel_event.is_set()
            job.status = JobStatus.CANCELLED if cancelled else JobStatus.COMPLETED
            job.completed_at = datetime.utcnow()
            job.skipped_duplicates = skipped_count
            job.progress.current = saved_count
            job.progress.percentage = 100.0
            job.progress.estimated_time_remaining = 0
            job.progress.current_prospect = None

            if cancelled:
                await self._append_log(
                    job,
                    f"Annulé — {saved_count} prospect(s) déjà ajouté(s) conservé(s)",
                )
                await scraping_job_stream_hub.broadcast(
                    job.id,
                    {
                        "type": "cancelled",
                        "summary": {"added": saved_count, "skipped_duplicates": skipped_count},
                    },
                )
            else:
                if is_facebook:
                    await self._append_log(
                        job,
                        "Recherche de pages terminée — vérification des prospects utilisables sur votre poste…",
                    )
                else:
                    await self._append_log(
                        job,
                        f"Terminé — {saved_count} prospect(s) ajouté(s), {skipped_count} doublon(s) ignoré(s)",
                    )
                await scraping_job_stream_hub.broadcast(
                    job.id,
                    {
                        "type": "done",
                        "summary": {
                            "added": saved_count,
                            "skipped_duplicates": skipped_count,
                            "status": job.status.value,
                        },
                    },
                )
            await self._emit_progress(job)
            logger.info(
                "Job %s %s: %s prospects, %s skipped",
                job_id,
                "cancelled" if cancelled else "completed",
                saved_count,
                skipped_count,
            )

        except Exception as exc:
            logger.error("Job %s failed: %s", job_id, exc, exc_info=True)
            job.status = JobStatus.FAILED
            job.error = str(exc)
            job.completed_at = datetime.utcnow()
            await self._append_log(job, f"Échec : {exc}")
            await scraping_job_stream_hub.broadcast(
                job.id,
                {"type": "error", "message": str(exc)},
            )
        finally:
            # Runs on completion, cancellation and failure alike: whatever was saved gets scanned.
            website_equipment_service.schedule_refresh(live_site_ids)
            db.close()
            self._running_tasks.pop(job_id, None)
            self._cancel_events.pop(job_id, None)

    def cancel_job(self, job_id: str) -> bool:
        """Request a graceful cancellation of a running job.

        Sets the job's cancel flag; the scraper stops at the next check and the
        job ends in ``CANCELLED`` (prospects already found are kept). No-op with
        ``False`` when the job is unknown or already finished.
        """
        job = self._jobs.get(job_id)
        if job is None or job.status not in (JobStatus.PENDING, JobStatus.RUNNING):
            return False
        self._cancel_events.setdefault(job_id, threading.Event()).set()
        logger.info("Cancellation requested for job %s", job_id)
        return True

    def start_job(self, job_id: str) -> None:
        if job_id in self._running_tasks:
            logger.warning("Job %s is already running", job_id)
            return
        task = asyncio.create_task(self.execute_job(job_id))
        self._running_tasks[job_id] = task
        logger.info("Started background task for job %s", job_id)

    def delete_job(self, job_id: str) -> bool:
        if job_id not in self._jobs:
            return False
        if job_id in self._running_tasks:
            self._running_tasks[job_id].cancel()
            del self._running_tasks[job_id]
        self._cancel_events.pop(job_id, None)
        del self._jobs[job_id]
        scraping_job_stream_hub.clear(job_id)
        logger.info("Deleted job %s", job_id)
        return True

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        now = datetime.utcnow()
        deleted_count = 0
        jobs_to_delete = [
            job_id
            for job_id, job in self._jobs.items()
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]
            and (now - job.created_at).total_seconds() / 3600 > max_age_hours
        ]
        for job_id in jobs_to_delete:
            if self.delete_job(job_id):
                deleted_count += 1
        if deleted_count > 0:
            logger.info("Cleaned up %s old jobs", deleted_count)
        return deleted_count


scraping_job_service = ScrapingJobService()
