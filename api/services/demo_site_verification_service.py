"""Verify that a demo site is actually reachable end-to-end."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

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
    local_demo_url: Optional[str]
    local_demo_url_live: bool
    message: str


class DemoSiteVerificationService:
    """Checks API public payload and demo-host HTTP availability."""

    async def _check_url(self, url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                return response.status_code < 400
        except Exception as exc:  # noqa: BLE001
            logger.info("Demo URL check failed for %s: %s", url, exc)
            return False

    async def verify(self, db: Session, site: DemoSite) -> DemoSiteVerificationResult:
        """
        Verify content exists and the demo host serves the slug on demo.dibodev.fr.

        Retries the public demo URL a few times to allow CDN/propagation delay.
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

        public_api_url: str = (
            f"{settings.api_base_url.rstrip('/')}{settings.api_prefix}/demo-sites/public/{site.slug}"
        )
        public_api_ok: bool = await self._check_url(public_api_url)
        if not public_api_ok:
            return DemoSiteVerificationResult(
                public_api_ok=False,
                demo_url_live=False,
                local_demo_url=None,
                local_demo_url_live=False,
                message="Public API payload is not available. Check that the API is running.",
            )

        demo_url: str = site.demo_url or ""
        demo_url_live: bool = False
        if demo_url:
            for attempt in range(settings.demo_site_verify_retries):
                if await self._check_url(demo_url):
                    demo_url_live = True
                    break
                if attempt < settings.demo_site_verify_retries - 1:
                    await asyncio.sleep(settings.demo_site_verify_retry_delay_seconds)

        if demo_url_live:
            return DemoSiteVerificationResult(
                public_api_ok=True,
                demo_url_live=True,
                local_demo_url=None,
                local_demo_url_live=False,
                message="Demo site is live and reachable.",
            )

        return DemoSiteVerificationResult(
            public_api_ok=True,
            demo_url_live=False,
            local_demo_url=None,
            local_demo_url_live=False,
            message=(
                f"Demo URL is not reachable at {demo_url}. "
                "Deploy demo-host to Vercel and ensure demo.dibodev.fr is configured."
            ),
        )


demo_site_verification_service = DemoSiteVerificationService()
