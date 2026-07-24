"""Background cleanup for expired demo websites."""

from __future__ import annotations

import asyncio
import logging

from core.database import SessionLocal
from services.demo_site_service import demo_site_service

logger = logging.getLogger(__name__)


class DemoSiteCleanupRunner:
    """Runs periodic expiry passes for demo sites past their TTL."""

    @staticmethod
    async def run_loop(interval_seconds: int = 3600) -> None:
        """
        Periodically delete demo sites past their expiry date.

        Args:
            interval_seconds: Delay between cleanup passes.
        """
        while True:
            db = SessionLocal()
            try:
                cleaned: int = await demo_site_service.expire_due_sites(db)
                if cleaned:
                    logger.info("Expired demo sites cleaned: %s", cleaned)
            except Exception as exc:
                logger.exception("Demo site cleanup failed: %s", exc)
            finally:
                db.close()

            await asyncio.sleep(interval_seconds)


async def run_demo_site_cleanup_loop(interval_seconds: int = 3600) -> None:
    """Backward-compatible entrypoint used by the API lifespan."""
    await DemoSiteCleanupRunner.run_loop(interval_seconds)
