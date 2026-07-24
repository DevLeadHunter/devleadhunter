"""Verify that a demo site is actually reachable end-to-end."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from core.config import settings
from models.demo_site import DemoSite

logger = logging.getLogger(__name__)


@dataclass
class DemoSiteVerificationResult:
    """Outcome of post-provisioning checks."""

    public_api_ok: bool
    demo_url_live: bool
    local_demo_url: str | None
    local_demo_url_live: bool
    message: str


class DemoSiteVerificationService:
    """Checks API public payload and demo-host HTTP availability."""

    LOCAL_DEMO_HOST_FALLBACK: str = "http://localhost:3001"

    async def _check_url(self, url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                return response.status_code < 400
        except Exception as exc:
            logger.info("Demo URL check failed for %s: %s", url, exc)
            return False

    async def _check_url_with_retries(self, url: str) -> bool:
        """Retry a demo-host URL check (CDN / dev server warm-up)."""
        if not url:
            return False
        for attempt in range(settings.demo_site_verify_retries):
            if await self._check_url(url):
                return True
            if attempt < settings.demo_site_verify_retries - 1:
                await asyncio.sleep(settings.demo_site_verify_retry_delay_seconds)
        return False

    async def check_domain_live(self, domain: str) -> bool:
        """
        Return True when the client's custom domain serves a page (HTTP < 400).

        Accepts a bare host or a full URL. Tries HTTPS first, then HTTP, each with
        the standard retry policy so a freshly-attached domain (propagating DNS)
        gets a fair chance before delivery is verified.

        Args:
            domain: The client's domain (e.g. "monsite.fr") or a full URL.

        Returns:
            True if the domain responds with a non-error status.
        """
        if not domain:
            return False
        host: str = domain.strip().rstrip("/")
        if host.startswith(("http://", "https://")):
            return await self._check_url_with_retries(host)
        if await self._check_url_with_retries(f"https://{host}"):
            return True
        return await self._check_url_with_retries(f"http://{host}")

    def _is_local_host_url(self, url: str) -> bool:
        lowered: str = url.lower()
        return "localhost" in lowered or "127.0.0.1" in lowered

    def _configured_demo_host_is_local(self) -> bool:
        return self._is_local_host_url(settings.demo_host_base_url)

    def _public_api_urls(self, slug: str) -> list[str]:
        """Return public API URLs to try when verifying demo site content."""
        urls: list[str] = [
            f"{settings.api_base_url.rstrip('/')}{settings.api_prefix}/demo-sites/public/{slug}",
            f"http://127.0.0.1:{settings.port}{settings.api_prefix}/demo-sites/public/{slug}",
        ]
        if settings.is_production:
            internal_url: str = f"http://127.0.0.1:{settings.port}{settings.api_prefix}/demo-sites/public/{slug}"
            if internal_url not in urls:
                urls.append(internal_url)
        deduped: list[str] = []
        for url in urls:
            if url not in deduped:
                deduped.append(url)
        return deduped

    def _local_demo_url_for_slug(self, slug: str) -> str:
        """Build the local demo-host URL used as a dev fallback."""
        base: str = settings.demo_host_base_url.rstrip("/")
        if self._configured_demo_host_is_local():
            return f"{base}/{slug}"
        return f"{self.LOCAL_DEMO_HOST_FALLBACK.rstrip('/')}/{slug}"

    async def verify(self, db: Session, site: DemoSite) -> DemoSiteVerificationResult:
        """
        Verify content exists and the demo host serves the slug.

        In development, accepts a reachable local demo-host (localhost:3001) even when
        ``demo_url`` still points at production.
        """
        del db  # reserved for future DB-backed checks

        if not site.content_json:
            return DemoSiteVerificationResult(
                public_api_ok=False,
                demo_url_live=False,
                local_demo_url=None,
                local_demo_url_live=False,
                message="Site content was not generated. Provisioning may have failed.",
            )

        public_api_ok: bool = False
        for candidate_url in self._public_api_urls(site.slug):
            if await self._check_url(candidate_url):
                public_api_ok = True
                break

        if not public_api_ok:
            return DemoSiteVerificationResult(
                public_api_ok=False,
                demo_url_live=False,
                local_demo_url=None,
                local_demo_url_live=False,
                message=(
                    "Public API payload is not available. "
                    f"Check GET {settings.api_prefix}/demo-sites/public/{site.slug} on the API."
                ),
            )

        demo_url: str = site.demo_url or self._local_demo_url_for_slug(site.slug)
        local_demo_url: str = self._local_demo_url_for_slug(site.slug)

        demo_url_live: bool = await self._check_url_with_retries(demo_url)
        local_demo_url_live: bool = False

        if demo_url_live:
            message = "Demo site is live and reachable."
            if self._is_local_host_url(demo_url):
                local_demo_url = demo_url
                local_demo_url_live = True
                message = "Demo site is live on the local demo-host."
            return DemoSiteVerificationResult(
                public_api_ok=True,
                demo_url_live=True,
                local_demo_url=local_demo_url if local_demo_url_live else None,
                local_demo_url_live=local_demo_url_live,
                message=message,
            )

        if not settings.is_production and local_demo_url != demo_url:
            local_demo_url_live = await self._check_url_with_retries(local_demo_url)
            if local_demo_url_live:
                return DemoSiteVerificationResult(
                    public_api_ok=True,
                    demo_url_live=False,
                    local_demo_url=local_demo_url,
                    local_demo_url_live=True,
                    message=(
                        f"Demo reachable locally at {local_demo_url}. "
                        "Set DEMO_HOST_BASE_URL=http://localhost:3001 in api/.env for prod-like URLs."
                    ),
                )

        if self._configured_demo_host_is_local():
            return DemoSiteVerificationResult(
                public_api_ok=True,
                demo_url_live=False,
                local_demo_url=local_demo_url,
                local_demo_url_live=False,
                message=(
                    f"Local demo-host is not reachable at {demo_url}. Run: cd demo-host && npm run dev (port 3001)."
                ),
            )

        return DemoSiteVerificationResult(
            public_api_ok=True,
            demo_url_live=False,
            local_demo_url=local_demo_url if not settings.is_production else None,
            local_demo_url_live=False,
            message=(
                f"Demo URL is not reachable at {demo_url}. "
                "Deploy demo-host to Vercel and ensure demo.dibodev.fr is configured."
            ),
        )


demo_site_verification_service = DemoSiteVerificationService()
