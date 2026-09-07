"""Background worker that drives the cold-email send queue."""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


class EmailQueueWorker:
    """
    Dispatches the queue items that are due, on a fixed tick.

    Rate limiting lives in the queue itself: each `EmailQueue` row carries a `scheduled_at`
    spaced by `campaign.send_delay_minutes`, so the worker only picks the next eligible row and
    never sleeps between sends. The per-tick cap stops a runaway catch-up after a long downtime.
    """

    TICK_INTERVAL_SECONDS: int = 60
    MAX_SENDS_PER_TICK: int = 10

    async def run_forever(self) -> None:
        """
        Run the worker loop indefinitely.

        An error inside a tick is logged and swallowed — the loop always reaches the next tick.
        """
        logger.info("[QueueWorker] Started — tick interval=%ds", self.TICK_INTERVAL_SECONDS)
        await self.reclaim_orphaned_sending()
        while True:
            try:
                await self.run_tick()
            except Exception as exc:
                logger.error("[QueueWorker] Unhandled error in tick: %s", exc, exc_info=True)
            await asyncio.sleep(self.TICK_INTERVAL_SECONDS)

    async def reclaim_orphaned_sending(self) -> None:
        """
        Recover queue items a previous process left mid-dispatch, once, before dispatching.

        Runs before the first tick so no row this process is actively sending can be touched: any
        ``sending`` row at startup belongs to a dead process. Errors are swallowed — a failed reclaim
        must never stop the worker from starting its send loop.
        """
        from core.database import SessionLocal
        from services.campaign_queue_service import CampaignQueueService

        db = SessionLocal()
        try:
            CampaignQueueService(db).reclaim_orphaned_sending()
        except Exception as exc:
            logger.error("[QueueWorker] Orphan reclaim failed at startup: %s", exc, exc_info=True)
            db.rollback()
        finally:
            db.close()

    async def run_tick(self) -> None:
        """
        Process every queue item that is currently due, in a single session.

        A fresh `SessionLocal` is opened per tick so no ORM state leaks from the previous one.
        """
        from core.database import SessionLocal
        from services.campaign_queue_service import CampaignQueueService

        db = SessionLocal()
        try:
            try:
                from services.storyblok_preswap_service import storyblok_preswap_service

                await storyblok_preswap_service.run_preswap_pass(db)
            except Exception as exc:
                # The pre-swap is best-effort: its failure must never block the send loop.
                logger.error("[QueueWorker] Storyblok pre-swap pass failed, sending anyway: %s", exc, exc_info=True)
                db.rollback()
            service = CampaignQueueService(db)
            sent_count: int = 0
            while sent_count < self.MAX_SENDS_PER_TICK:
                dispatched = await service.process_next()
                if not dispatched:
                    break
                sent_count += 1
            if sent_count:
                logger.info("[QueueWorker] Sent %d email(s) this tick", sent_count)
            try:
                service.complete_drained_campaigns()
            except Exception as exc:
                # Completion is bookkeeping: its failure must never stop the send loop.
                logger.error("[QueueWorker] Campaign completion sweep failed: %s", exc, exc_info=True)
                db.rollback()
        finally:
            db.close()


email_queue_worker = EmailQueueWorker()
