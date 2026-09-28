"""Periodic pass that fails the prospection videos no generation can finish, and stops the renders running too long."""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy.orm import Session

from services.assistant_video_service import assistant_video_service
from services.demo_video_service import demo_video_service
from services.video_pipeline import MAXIMUM_GENERATION_MINUTES

logger = logging.getLogger(__name__)

# A render stuck past the maximum duration is stopped at most this long after it.
_CHECK_INTERVAL_SECONDS = 120


class VideoGenerationWatchdog:
    """Runs the reconcile pass of the site and receptionist videos at startup, then on a fixed interval."""

    def check(self, db: Session) -> int:
        """
        Fail the unfinished videos of both kinds that cannot finish or ran too long.

        Args:
            db: Active database session.

        Returns:
            The number of videos marked failed.
        """
        failed_count = demo_video_service.reconcile_orphaned(db) + assistant_video_service.reconcile_orphaned(db)
        if failed_count:
            logger.info("[VideoWatchdog] %d video generation(s) marked failed", failed_count)
        return failed_count

    async def run_forever(self) -> None:
        """Check right away (a restart orphans every generation), then every interval; an error never stops the loop."""
        from core.database import SessionLocal

        logger.info(
            "[VideoWatchdog] Started — interval=%ds, maximum render=%dmin",
            _CHECK_INTERVAL_SECONDS,
            MAXIMUM_GENERATION_MINUTES,
        )
        while True:
            db: Session = SessionLocal()
            try:
                self.check(db)
            except Exception:
                logger.exception("[VideoWatchdog] check failed")
            finally:
                db.close()
            await asyncio.sleep(_CHECK_INTERVAL_SECONDS)


video_generation_watchdog = VideoGenerationWatchdog()
