"""Background cleanup for expired demo websites."""
from __future__ import annotations

import asyncio
import logging

from core.database import SessionLocal
from services.demo_site_service import demo_site_service

logger = logging.getLogger(__name__)


async def run_demo_site_cleanup_loop(interval_seconds: int = 3600) -> None:
    """
    Periodically delete demo sites past their expiry date.

    @param interval_seconds - Delay between cleanup passes.
    """
    while True:
        db = SessionLocal()
        try:
            cleaned: int = await demo_site_service.expire_due_sites(db)
            if cleaned:
                logger.info("Expired demo sites cleaned: %s", cleaned)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Demo site cleanup failed: %s", exc)
        finally:
            db.close()

        await asyncio.sleep(interval_seconds)
