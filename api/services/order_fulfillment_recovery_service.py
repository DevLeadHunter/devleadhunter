"""Background recovery for post-payment fulfilment.

Closes the fire-and-forget gap: the Stripe webhook kicks off fulfilment in a
detached task, so if that task dies (server restart, transient Vercel/Storyblok
outage) the paid order would stay silently undelivered. This loop periodically
retries such orders — bounded by ``MAX_FULFILMENT_ATTEMPTS`` and age — so a client
who paid is not left without a site.
"""
from __future__ import annotations

import asyncio
import logging

from core.database import SessionLocal
from services.order_service import order_service

logger = logging.getLogger(__name__)


async def run_order_fulfillment_recovery_loop(interval_seconds: int = 600) -> None:
    """
    Periodically retry website orders that were paid but never fully delivered.

    Args:
        interval_seconds: Delay between recovery passes (default 10 min).
    """
    while True:
        db = SessionLocal()
        try:
            order_ids: list[int] = order_service.list_stuck_fulfilment_order_ids(db)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Fulfilment recovery scan failed: %s", exc)
            order_ids = []
        finally:
            db.close()

        for order_id in order_ids:
            try:
                await order_service.fulfill_order_async(order_id)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Fulfilment recovery retry failed for order_id=%s: %s", order_id, exc)

        if order_ids:
            logger.info("Fulfilment recovery pass retried %s stuck order(s)", len(order_ids))

        await asyncio.sleep(interval_seconds)
