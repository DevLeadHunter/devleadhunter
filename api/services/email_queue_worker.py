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
        while True:
            try:
                await self.run_tick()
            except Exception as exc:  # noqa: BLE001
                logger.error("[QueueWorker] Unhandled error in tick: %s", exc, exc_info=True)
            await asyncio.sleep(self.TICK_INTERVAL_SECONDS)

    async def run_tick(self) -> None:
        """
        Process every queue item that is currently due, in a single session.

        A fresh `SessionLocal` is opened per tick so no ORM state leaks from the previous one.
        """
        from core.database import SessionLocal
        from services.campaign_queue_service import CampaignQueueService

        db = SessionLocal()
        try:
            service = CampaignQueueService(db)
            sent_count: int = 0
            while sent_count < self.MAX_SENDS_PER_TICK:
                dispatched = await service.process_next()
                if not dispatched:
                    break
                sent_count += 1
            if sent_count:
                logger.info("[QueueWorker] Sent %d email(s) this tick", sent_count)
        finally:
            db.close()


email_queue_worker = EmailQueueWorker()
