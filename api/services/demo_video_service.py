"""Prospection video generation for demo sites.

The owner's PC assembles, per prospect, a short (~30-45 s) video from:
  - the user's generic presenter clip (webcam + voice, uploaded once —
    see ``presenter_video_service``), full-screen for the intro/outro;
  - a capture of the prospect's OWN generated demo site, filmed by the owner's desktop app:
    the site scroll, then its Storyblok editor (which needs the owner's session and the
    site's Storyblok space);
  - a text greeting « Bonjour {Prénom} » overlaid on the intro (text, not
    cloned voice — decision from the reflection ticket);
  - a personalised email thumbnail (site screenshot + play button) used by
    the ``{vignette_video}`` template variable.

Timeline (D = presenter clip duration):
  0 ─ intro ──────────── D-outro ───────── D
  webcam plein écran │ site + webcam PiP │ webcam plein écran (CTA)

The voice stays 100 % generic — personalisation is visual only (his site,
his first name) so ONE recording works for every prospect.

The checks, the publication and the statuses are shared with the receptionist's video in
:class:`services.prospection_video_service.ProspectionVideoService`. The mp4 + jpg live on Cloudflare R2
(``videos/websites/{slug}.mp4`` / ``images/websites/{slug}.jpg``), served straight from Cloudflare — the VPS
never streams a byte. The player page lives on the demo host at ``/v/{slug}`` (PostHog-tracked, same identity
as the demo).
"""

from __future__ import annotations

import logging
from datetime import datetime

from core.config import settings
from enums.demo_site_status import DemoSiteStatus
from enums.demo_video_status import DemoVideoStatus
from models.demo_site import DemoSite
from services.prospection_video_service import ProspectionVideoService
from services.r2_storage_service import r2_storage

logger = logging.getLogger(__name__)

# The presenter clip the site video uses (the generic speech about the site).
SITE_PRESENTER_MODULE = "websites"


def video_object_key(slug: str) -> str:
    """R2 key of a demo site's generated prospection video."""
    return r2_storage.website_video_key(slug)


def thumbnail_object_key(slug: str) -> str:
    """R2 key of a demo site's email thumbnail."""
    return r2_storage.website_thumbnail_key(slug)


def video_page_url(slug: str) -> str:
    """Public player-page URL on the demo host (PostHog-tracked)."""
    return f"{settings.demo_host_base_url.rstrip('/')}/v/{slug}"


def public_video_file_url(slug: str) -> str:
    """Public R2 URL of the mp4 (served by Cloudflare, never by the API)."""
    return r2_storage.public_url(video_object_key(slug))


def public_thumbnail_url(slug: str, generated_at: datetime | None = None) -> str:
    """Public R2 URL of the email thumbnail (absolute — embedded in emails).

    The R2 key never changes for a site, so a regenerated thumbnail kept showing the previous
    image from the browser cache: the generation instant is appended as a version query so every
    regeneration yields a new URL.
    """
    url = r2_storage.public_url(thumbnail_object_key(slug))
    if generated_at is None:
        return url
    return f"{url}?v={int(generated_at.timestamp())}"


def has_ready_video(site: DemoSite) -> bool:
    """
    True when the site's prospection video is generated.

    Objects live on R2, so this trusts the DB status rather than doing a network
    round-trip on every email render; deletions go through
    :func:`delete_files_for_slug`, whose callers also reset the status.
    """
    return site.video_status == DemoVideoStatus.READY.value


def delete_files_for_slug(slug: str) -> None:
    """Remove the generated video + thumbnail from R2 (best effort)."""
    try:
        r2_storage.delete_many(
            [video_object_key(slug), thumbnail_object_key(slug), r2_storage.website_background_key(slug)]
        )
    except Exception:
        logger.warning("[Video] R2 cleanup failed for slug=%s", slug, exc_info=True)


class DemoVideoService(ProspectionVideoService[DemoSite]):
    """The prospection video of a demo site: what its capture needs (the site's Storyblok space) and its files."""

    subject_model = DemoSite
    kind = "site"
    presenter_module = SITE_PRESENTER_MODULE
    shown_subject = "le site"
    missing_presenter_message = (
        "Aucun clip de présentation. Enregistrez d'abord votre vidéo webcam "
        "(voix générique) dans « Vidéo de présentation »."
    )

    def is_ready_to_film(self, site: DemoSite) -> bool:
        """
        Whether the desktop app can film the site now: its video ends on the Storyblok editor of its space.

        Args:
            site: The demo site.

        Returns:
            True when the site is active, online and has its Storyblok space.
        """
        return super().is_ready_to_film(site) and bool(site.storyblok_space_id)

    @staticmethod
    def is_waiting_for_storyblok_space(site: DemoSite) -> bool:
        """
        Whether the site's video, asked from the PC, waits for the Storyblok space the worker creates later.

        Args:
            site: The demo site.

        Returns:
            True while a request waits on a site without its space.
        """
        return site.video_desktop_requested_at is not None and not site.storyblok_space_id

    def _check_can_generate(self, site: DemoSite) -> None:
        """
        Refuse a site that is not active or has no public page.

        Args:
            site: The demo site.

        Raises:
            ValueError: with the reason the dashboard shows.
        """
        if site.status != DemoSiteStatus.ACTIVE.value:
            raise ValueError("La vidéo ne peut être générée que pour un site démo actif.")
        if not site.demo_url:
            raise ValueError("Ce site démo n'a pas d'URL publique.")

    def _video_key(self, slug: str) -> str:
        """
        The R2 key of the site video.

        Args:
            slug: The site's slug.

        Returns:
            The object key.
        """
        return video_object_key(slug)

    def _thumbnail_key(self, slug: str) -> str:
        """
        The R2 key of the site video's email thumbnail.

        Args:
            slug: The site's slug.

        Returns:
            The object key.
        """
        return thumbnail_object_key(slug)

    def _delete_files(self, slug: str) -> None:
        """
        Delete the site video's files, its desktop background included.

        Args:
            slug: The site's slug.
        """
        delete_files_for_slug(slug)


demo_video_service = DemoVideoService()
