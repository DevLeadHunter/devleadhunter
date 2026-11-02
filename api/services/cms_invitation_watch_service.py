"""Background watch of the Storyblok invitations a client has not accepted yet.

Nothing else re-reads an invitation once sent: without this loop the owner only learns that a client joined their
editing space by clicking « Vérifier s'il a rejoint ». Each pass re-reads every pending invitation through
``demo_site_service.refresh_cms_collaborator_status``, which notifies the owner on the first ``joined``.
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import select

from core.database import SessionLocal
from enums.demo_site_status import DemoSiteStatus
from enums.storyblok_collaborator_status import StoryblokCollaboratorStatus
from models.demo_site import DemoSite
from services.demo_site_service import demo_site_service

logger = logging.getLogger(__name__)

_CHECK_INTERVAL_SECONDS: int = 900


class CmsInvitationWatchService:
    """Re-reads the pending Storyblok invitations, so the owner hears when a client joins their space."""

    async def check_pending_invitations(self) -> None:
        """Re-read each pending invitation in its own short session; one site's failure never skips the next ones."""
        for demo_site_id in self._pending_invitation_site_ids():
            db = SessionLocal()
            try:
                demo_site = db.get(DemoSite, demo_site_id)
                if demo_site is not None:
                    await demo_site_service.refresh_cms_collaborator_status(db, demo_site)
            except Exception:
                logger.warning(
                    "[CmsInvitationWatch] Invitation check failed for demo site %s", demo_site_id, exc_info=True
                )
            finally:
                db.close()

    async def run_loop(self) -> None:
        """Check the pending invitations every 15 minutes, forever (errors never stop the loop)."""
        while True:
            try:
                await self.check_pending_invitations()
            except Exception:
                logger.warning("[CmsInvitationWatch] Pass failed", exc_info=True)
            await asyncio.sleep(_CHECK_INTERVAL_SECONDS)

    @staticmethod
    def _pending_invitation_site_ids() -> list[int]:
        """Ids of the live demo sites whose client was invited to Storyblok and has not joined yet."""
        db = SessionLocal()
        try:
            return list(
                db.execute(
                    select(DemoSite.id)
                    .where(
                        DemoSite.status != DemoSiteStatus.DELETED.value,
                        DemoSite.storyblok_invite_sent.is_(True),
                        DemoSite.storyblok_collaborator_status == StoryblokCollaboratorStatus.PENDING.value,
                    )
                    .order_by(DemoSite.id)
                ).scalars()
            )
        finally:
            db.close()


cms_invitation_watch_service = CmsInvitationWatchService()
