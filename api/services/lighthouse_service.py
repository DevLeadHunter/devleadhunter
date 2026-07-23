"""
Lighthouse audit of a prospect's EXISTING website via Google PageSpeed Insights.

Product goal: when a prospect already has a website, know whether it is weak
enough to pitch a REDESIGN instead of a creation. The audit runs on demand from
the prospect drawer, is slow (PSI takes 30–60 s), and its result is persisted on
the prospect (``lighthouse_json`` / ``lighthouse_at``).

The PSI API is free; ``PAGESPEED_API_KEY`` is optional (higher quota when set).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

_PSI_URL: str = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
_CATEGORIES: tuple[str, ...] = ("PERFORMANCE", "ACCESSIBILITY", "BEST_PRACTICES", "SEO")
# Below this score on any category the existing site is considered a redesign target.
IMPROVABLE_THRESHOLD: int = 60


class LighthouseAuditError(Exception):
    """Raised when the PSI audit cannot be run or parsed."""


def _normalize_url(website: str) -> str:
    """Ensure the audited URL has a scheme (prospects often store bare domains)."""
    url = website.strip()
    if not url.lower().startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


class LighthouseService:
    """Runs PageSpeed Insights audits and shapes the stored result."""

    async def audit_website(self, website: str) -> dict[str, Any]:
        """Audit a website (mobile strategy, 4 categories) and return the stored shape.

        Args:
            website: The prospect's website URL (scheme optional).

        Returns:
            ``{scores: {performance, accessibility, bestPractices, seo}, is_improvable, strategy, final_url, fetched_at}`` — scores are 0-100 integers, ``None`` when PSI could not compute a category.

        Raises:
            LighthouseAuditError: When PSI fails or returns no Lighthouse result.
        """
        url = _normalize_url(website)
        params: list[tuple[str, str]] = [
            ("url", url),
            ("strategy", "mobile"),
            *[("category", category) for category in _CATEGORIES],
        ]
        api_key: Optional[str] = getattr(settings, "pagespeed_api_key", None)
        if api_key:
            params.append(("key", api_key))

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.get(_PSI_URL, params=params)
            except httpx.HTTPError as exc:
                raise LighthouseAuditError(f"PageSpeed Insights injoignable : {exc}") from exc

        if response.status_code == 429:
            # The anonymous shared PSI quota runs out quickly — a free API key
            # switches to a personal 25k/day quota.
            raise LighthouseAuditError(
                "Quota PageSpeed Insights atteint — réessayez plus tard ou configurez PAGESPEED_API_KEY (clé gratuite)."
            )
        if response.status_code != 200:
            detail = response.text[:300]
            logger.warning("PSI %s for %s: %s", response.status_code, url, detail)
            raise LighthouseAuditError(
                f"PageSpeed Insights a refusé l'audit ({response.status_code}) — le site est-il accessible ?"
            )

        payload: dict[str, Any] = response.json()
        lighthouse: dict[str, Any] = payload.get("lighthouseResult") or {}
        categories: dict[str, Any] = lighthouse.get("categories") or {}
        if not categories:
            raise LighthouseAuditError("Résultat Lighthouse vide — le site n'a pas pu être analysé.")

        def score_of(key: str) -> Optional[int]:
            raw = (categories.get(key) or {}).get("score")
            return round(raw * 100) if isinstance(raw, (int, float)) else None

        scores: dict[str, Optional[int]] = {
            "performance": score_of("performance"),
            "accessibility": score_of("accessibility"),
            "bestPractices": score_of("best-practices"),
            "seo": score_of("seo"),
        }
        known_scores = [value for value in scores.values() if value is not None]
        is_improvable = bool(known_scores) and min(known_scores) < IMPROVABLE_THRESHOLD

        return {
            "scores": scores,
            "is_improvable": is_improvable,
            "strategy": "mobile",
            "final_url": lighthouse.get("finalDisplayedUrl") or url,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }


lighthouse_service = LighthouseService()
