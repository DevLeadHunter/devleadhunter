"""Tells the owner when their client publishes changes to their site from their own Storyblok space.

The publish webhook fires for every publication, the owner's own ones too (generation, dashboard edits, all made with
the Management token): only a publication by another Storyblok account notifies, at most once every 10 minutes per site.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from core.database import SessionLocal
from models.demo_site import DemoSite
from services.notification_service import notification_service
from services.storyblok_service import storyblok_service
from services.templates import registry as template_registry

logger = logging.getLogger(__name__)

_PUBLICATION_MAX_AGE: timedelta = timedelta(minutes=5)
_SECONDS_BETWEEN_NOTIFICATIONS_PER_SITE: float = 600.0


class CmsClientPublicationService:
    """Notifies the owner of the publications their client makes in their editing space."""

    def __init__(self) -> None:
        self._last_notified_at_by_site: dict[int, float] = {}

    async def notify_if_published_by_client(
        self, demo_site_id: int, previous_content: dict[str, Any], published_content: dict[str, Any]
    ) -> None:
        """
        Notify the owner when the latest publication of a site was made by their client, never by the owner.

        A site whose client was never invited is skipped without asking Storyblok: only the owner can publish there.
        A publisher Storyblok cannot tell notifies nobody, and no failure ever reaches the webhook.

        Args:
            demo_site_id: The site the publication landed on.
            previous_content: The site content before the publication.
            published_content: The site content it published.
        """
        try:
            site = self._read_site(demo_site_id)
            if site is None or not site.storyblok_invite_sent or not site.storyblok_space_id:
                return
            if self._was_notified_recently(demo_site_id):
                return
            owner_id: int | None = await storyblok_service.get_token_owner_id()
            publisher_id: int | None = await storyblok_service.get_recent_story_publisher_id(
                site.storyblok_space_id, datetime.now(UTC) - _PUBLICATION_MAX_AGE
            )
            if owner_id is None or publisher_id is None:
                logger.warning("Publisher of demo site %s unknown: no notification", demo_site_id)
                return
            if publisher_id == owner_id:
                return
            self._last_notified_at_by_site[demo_site_id] = time.monotonic()
            changed_section_labels: list[str] = template_registry.changed_section_labels(
                site.template_id, previous_content, published_content
            )
            db = SessionLocal()
            try:
                await notification_service.notify_cms_published(
                    db,
                    user_id=site.user_id,
                    prospect_id=site.prospect_id,
                    fallback_name=site.business_name,
                    demo_site_id=demo_site_id,
                    changed_section_labels=changed_section_labels,
                )
            finally:
                db.close()
        except Exception:
            logger.warning("Client publication check failed for demo site %s", demo_site_id, exc_info=True)

    def _was_notified_recently(self, demo_site_id: int) -> bool:
        """Whether the owner already heard about a publication of this site less than 10 minutes ago."""
        last_notified_at: float | None = self._last_notified_at_by_site.get(demo_site_id)
        return (
            last_notified_at is not None
            and time.monotonic() - last_notified_at < _SECONDS_BETWEEN_NOTIFICATIONS_PER_SITE
        )

    @staticmethod
    def _read_site(demo_site_id: int) -> DemoSite | None:
        """The site, read in a session closed before Storyblok is asked anything."""
        db = SessionLocal()
        try:
            return db.get(DemoSite, demo_site_id)
        finally:
            db.close()


cms_client_publication_service = CmsClientPublicationService()
