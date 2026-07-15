"""
Background worker that drives the cold-email send queue.

Started once at application startup via ``asyncio.create_task(run_queue_worker())``.
Ticks every 60 seconds and dispatches all queue items that are currently due.

The rate limiting is baked into the queue: each ``EmailQueue`` row has a
``scheduled_at`` timestamp spaced by ``campaign.send_delay_minutes``, so the
worker simply picks the next eligible row without any additional sleep logic.
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

_TICK_INTERVAL_SECONDS: int = 60
# Hard cap on emails sent per tick to prevent runaway sends during catch-up
# (e.g. after the server was down for several hours).
_MAX_PER_TICK: int = 10


async def run_queue_worker() -> None:
    """
    Run the email queue worker loop indefinitely.

    On every tick, dispatches all queue items that are currently due (up to
    ``_MAX_PER_TICK``).  Errors inside a tick are logged but never propagate —
    the loop always continues to the next tick.
    """
    logger.info("[QueueWorker] Started — tick interval=%ds", _TICK_INTERVAL_SECONDS)
    while True:
        try:
            await _tick()
        except Exception as exc:  # noqa: BLE001
            logger.error("[QueueWorker] Unhandled error in tick: %s", exc, exc_info=True)
        await asyncio.sleep(_TICK_INTERVAL_SECONDS)


async def _tick() -> None:
    """
    Process all queue items that are currently due in a single DB session.

    Opens a fresh ``SessionLocal`` for the tick so that any ORM state from
    a previous tick is discarded cleanly.
    """
    from core.database import SessionLocal
    from services.campaign_queue_service import CampaignQueueService

    db = SessionLocal()
    try:
        service = CampaignQueueService(db)
        processed = 0
        while processed < _MAX_PER_TICK:
            dispatched = await service.process_next()
            if not dispatched:
                break
            processed += 1
        if processed:
            logger.info("[QueueWorker] Sent %d email(s) this tick", processed)
    finally:
        db.close()
