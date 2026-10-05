"""
Desktop relay of the prospection video — a video asked from a tablet or a phone is built by the owner's desktop app.

Only the desktop app can film a site together with its Storyblok editor and montage the clip without loading the
server. A device without it leaves a request on the site; the desktop app, which looks for requests in the
background, takes each one, builds the video and publishes it.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from enums.demo_site_status import DemoSiteStatus
from enums.demo_video_status import DemoVideoStatus
from models.demo_site import DemoSite
from services.demo_video_service import demo_video_service

# A build takes two to three minutes and the desktop app gives it up after twenty. Past this delay the app is
# taken for closed mid-build, and the request is offered again.
_CLAIM_LIFETIME: timedelta = timedelta(minutes=25)
_MAXIMUM_ERROR_MESSAGE_LENGTH = 1000

NO_REQUEST_MESSAGE = "Aucune demande de vidéo n'attend l'ordinateur pour ce site."
ALREADY_BUILDING_MESSAGE = "L'ordinateur génère déjà cette vidéo."


class DemoVideoDesktopRelay:
    """Keeps the videos waiting for the desktop app, and which ones it is building."""

    def __init__(self, claim_lifetime: timedelta = _CLAIM_LIFETIME) -> None:
        self._claim_lifetime = claim_lifetime
        # Kept in the memory of the API process, like the desktop app presence: it runs a single worker.
        # A restart forgets the builds under way, so their requests are simply offered again.
        self._claimed_at: dict[int, datetime] = {}

    def request(self, db: Session, site: DemoSite, user_id: int) -> DemoSite:
        """
        Leave a video request for the owner's desktop app.

        Args:
            db: Active database session.
            site: The demo site, owned by the user.
            user_id: Owner, whose presenter clip the video uses.

        Returns:
            The site, waiting for the desktop app. A video already published stays online meanwhile.

        Raises:
            ValueError: when the video cannot be generated now (site not ready, no presenter clip, generation under way).
        """
        if self.is_build_started(site):
            raise ValueError(ALREADY_BUILDING_MESSAGE)
        demo_video_service.ensure_generation_can_start(db, site, user_id)
        site.video_desktop_requested_at = naive_utc_now()
        db.commit()
        db.refresh(site)
        self._claimed_at.pop(site.id, None)
        return site

    def clear_request(self, db: Session, site: DemoSite) -> DemoSite:
        """
        Close a site's request: withdrawn by the user, replaced by a server generation, or fulfilled.

        Args:
            db: Active database session.
            site: The demo site.

        Returns:
            The site, without a waiting request.
        """
        self._claimed_at.pop(site.id, None)
        if site.video_desktop_requested_at is not None:
            site.video_desktop_requested_at = None
            db.commit()
            db.refresh(site)
        return site

    def waiting_sites(self, db: Session, user_id: int) -> list[DemoSite]:
        """
        The user's sites whose video waits for a desktop app, oldest request first.

        Args:
            db: Active database session.
            user_id: Owner of the sites.

        Returns:
            The sites no desktop app is building.
        """
        requested: list[DemoSite] = (
            db.query(DemoSite)
            .filter(
                DemoSite.user_id == user_id,
                DemoSite.video_desktop_requested_at.is_not(None),
                DemoSite.status != DemoSiteStatus.DELETED.value,
            )
            .order_by(DemoSite.video_desktop_requested_at.asc())
            .all()
        )
        return [site for site in requested if not self.is_build_started(site)]

    def claim(self, site: DemoSite) -> None:
        """
        Record that a desktop app starts building the site's video, so no other look takes it.

        Args:
            site: The demo site.

        Raises:
            ValueError: when no request waits for this site, or a desktop app is already building it.
        """
        if site.video_desktop_requested_at is None:
            raise ValueError(NO_REQUEST_MESSAGE)
        if self.is_build_started(site):
            raise ValueError(ALREADY_BUILDING_MESSAGE)
        self._claimed_at[site.id] = naive_utc_now()

    def is_build_started(self, site: DemoSite) -> bool:
        """
        Whether a desktop app took the site's request recently enough to still be building.

        Args:
            site: The demo site.

        Returns:
            True while the build is taken for running.
        """
        claimed_at = self._claimed_at.get(site.id)
        if site.video_desktop_requested_at is None or claimed_at is None:
            return False
        return naive_utc_now() - claimed_at <= self._claim_lifetime

    def record_failure(self, db: Session, site: DemoSite, message: str) -> DemoSite:
        """
        Close a request the desktop app could not fulfil, with the reason the dashboard shows.

        Args:
            db: Active database session.
            site: The demo site.
            message: Why the desktop app gave up.

        Returns:
            The site: marked failed, unless a video already published stays valid.

        Raises:
            ValueError: when no request waits for this site.
        """
        if site.video_desktop_requested_at is None:
            raise ValueError(NO_REQUEST_MESSAGE)
        self._claimed_at.pop(site.id, None)
        site.video_desktop_requested_at = None
        site.video_error = message[:_MAXIMUM_ERROR_MESSAGE_LENGTH]
        if site.video_status != DemoVideoStatus.READY.value:
            site.video_status = DemoVideoStatus.FAILED.value
        db.commit()
        db.refresh(site)
        return site


demo_video_desktop_relay = DemoVideoDesktopRelay()
