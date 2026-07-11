"""
Prospect enrichment scraper (Google Maps place details).

Deliberately separate from the prospect *search* scrapers: this runs only on
demand (enrichment button / before site generation), so discovery stays fast.
It reuses the shared nodriver infrastructure but never touches the search
scrapers' code paths.

The DOM selectors target Google Maps place panels and are best-effort: every
extraction step is isolated so a partial failure still returns whatever data
could be gathered. Selectors may need tuning over time against live Maps.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import quote

from scrappers.google_scraper import GoogleScraper
from scrappers.nodriver_browser import NODRIVER_AVAILABLE, NodriverBrowser
from scrappers.nodriver_dom import NodriverDom
from scrappers.nodriver_executor import run_nodriver_task
from scrappers.osm_enrichment import enrich_from_osm
from scrappers.resilient_extract import parse_ld_json_blocks
from scrappers import scrape_signals

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentData:
    """Structured rich data gathered for a prospect."""

    source: str = "google"
    logo_url: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    description: Optional[str] = None
    photos: list[str] = field(default_factory=list)
    reviews: list[dict[str, Any]] = field(default_factory=list)
    opening_hours: list[dict[str, str]] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    social_links: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (matches the ProspectEnrichment columns)."""
        return {
            "source": self.source,
            "logo_url": self.logo_url,
            "rating": self.rating,
            "reviews_count": self.reviews_count,
            "description": self.description,
            "photos": self.photos,
            "reviews": self.reviews,
            "opening_hours": self.opening_hours,
            "services": self.services,
            "social_links": self.social_links,
        }


# JS executed in the place page to gather everything in one round trip.
_EXTRACT_JS = r"""
(() => {
    const out = {
        rating: null, reviews_count: null, description: null,
        photos: [], reviews: [], opening_hours: [], ld: [], social: {}
    };
    const txt = (el) => (el ? (el.innerText || el.textContent || '').trim() : '');

    // JSON-LD (schema.org) — the most stable anchor; parsed in Python as a fallback
    // for description / rating / reviews_count when the DOM selectors miss.
    try {
        out.ld = Array.from(document.querySelectorAll('script[type="application/ld+json"]'))
            .map(s => s.textContent || '').filter(Boolean);
    } catch (e) {}

    // Social profile links present anywhere on the panel.
    try {
        const nets = { facebook: 'facebook.com/', instagram: 'instagram.com/', linkedin: 'linkedin.com/', tiktok: 'tiktok.com/', youtube: 'youtube.com/' };
        document.querySelectorAll('a[href]').forEach((a) => {
            const href = a.getAttribute('href') || '';
            for (const [net, needle] of Object.entries(nets)) {
                if (!out.social[net] && href.toLowerCase().includes(needle)) out.social[net] = href;
            }
        });
    } catch (e) {}

    // Rating + reviews count (F7nice block: "4,9  (132)")
    try {
        const block = document.querySelector('div.F7nice');
        if (block) {
            const spans = block.querySelectorAll('span');
            const ratingTxt = spans[0] ? txt(spans[0]).replace(',', '.') : '';
            const r = parseFloat(ratingTxt);
            if (!isNaN(r)) out.rating = r;
            const countMatch = txt(block).match(/\(?\s*([\d\s.,]+)\s*\)?\s*(avis|reviews)?/i);
            const aria = block.querySelector('[aria-label]');
            const ariaTxt = aria ? aria.getAttribute('aria-label') : '';
            const numMatch = (ariaTxt + ' ' + txt(block)).match(/([\d][\d\s.,]*)\s*(avis|reviews)/i);
            if (numMatch) {
                const n = parseInt(numMatch[1].replace(/[^\d]/g, ''), 10);
                if (!isNaN(n)) out.reviews_count = n;
            }
        }
    } catch (e) {}

    // Description / about (meta description as fallback)
    try {
        const meta = document.querySelector('meta[name="description"], meta[property="og:description"]');
        if (meta) out.description = (meta.getAttribute('content') || '').trim() || null;
    } catch (e) {}

    // Photos (large googleusercontent images, deduplicated)
    try {
        const seen = new Set();
        document.querySelectorAll('img').forEach((img) => {
            let src = img.getAttribute('src') || '';
            if (!src || src.indexOf('googleusercontent') === -1) return;
            // keep only reasonably large images (skip tiny avatars)
            if (/=s\d{1,2}-/.test(src) || /=w\d{1,2}-/.test(src)) return;
            // normalize size to a large variant
            src = src.replace(/=w\d+-h\d+.*$/, '=w1200-h800').replace(/=s\d+.*$/, '=s1200');
            if (!seen.has(src)) { seen.add(src); out.photos.push(src); }
        });
        out.photos = out.photos.slice(0, 12);
    } catch (e) {}

    // Opening hours (table rows: day + hours)
    try {
        const rows = document.querySelectorAll('table tr');
        rows.forEach((tr) => {
            const cells = tr.querySelectorAll('td, th');
            if (cells.length >= 2) {
                const day = txt(cells[0]);
                const hours = txt(cells[1]);
                if (day && hours && day.length < 20 && hours.length < 40) {
                    out.opening_hours.push({ day, hours });
                }
            }
        });
        out.opening_hours = out.opening_hours.slice(0, 7);
    } catch (e) {}

    // Reviews snippets present in the panel
    try {
        const blocks = document.querySelectorAll('div.jftiEf, div[data-review-id]');
        blocks.forEach((b) => {
            const author = txt(b.querySelector('.d4r55, .TSUbDb'));
            const text = txt(b.querySelector('.wiI7pd, .MyEned'));
            const ratingEl = b.querySelector('[aria-label*="étoile"], [aria-label*="star"], .kvMYJc');
            let rating = null;
            if (ratingEl) {
                const m = (ratingEl.getAttribute('aria-label') || '').match(/([\d.,]+)/);
                if (m) rating = parseFloat(m[1].replace(',', '.'));
            }
            if (text) out.reviews.push({ author: author || 'Client', text, rating });
        });
        out.reviews = out.reviews.slice(0, 6);
    } catch (e) {}

    return out;
})()
"""


class EnrichmentScraper:
    """Gathers rich Google Maps place data for a single prospect."""

    async def enrich(
        self,
        *,
        business_name: str,
        city: Optional[str] = None,
        google_maps_url: Optional[str] = None,
    ) -> EnrichmentData:
        """Fetch enrichment for a business: Google Maps (rich) + OpenStreetMap (stable gap-filler).

        Google is the primary source (photos, reviews, rating); OpenStreetMap fills the fields
        Google is weak/blocked on (opening hours, social links, description) via a plain HTTP API.
        OSM runs even when nodriver is unavailable, so enrichment degrades gracefully instead of
        returning nothing.
        """
        data = EnrichmentData()
        if NODRIVER_AVAILABLE:

            async def task() -> EnrichmentData:
                return await self._enrich_nodriver(business_name, city, google_maps_url)

            data = await run_nodriver_task(task, timeout=180)
        else:
            logger.warning("nodriver not available — Google enrichment skipped, OSM only")

        # Complementary OpenStreetMap enrichment (plain HTTP, no browser, never blocked).
        try:
            osm = await enrich_from_osm(business_name, city)
        except Exception as exc:  # noqa: BLE001
            logger.info("OSM enrichment failed for %s: %s", business_name, exc)
            osm = {}
        self._merge_osm(data, osm)
        return data

    @staticmethod
    def _merge_osm(data: EnrichmentData, osm: dict[str, Any]) -> None:
        """Fill gaps in the Google-sourced data with OSM's stable fields (Google wins where present)."""
        if not osm:
            return
        if not data.opening_hours and isinstance(osm.get("opening_hours"), list):
            data.opening_hours = osm["opening_hours"]
        if isinstance(osm.get("social_links"), dict) and osm["social_links"]:
            data.social_links = {**osm["social_links"], **(data.social_links or {})}
        if not data.description and osm.get("description"):
            data.description = str(osm["description"]).strip() or None
        if data.source == "google":
            data.source = "google+osm"

    async def _enrich_nodriver(
        self,
        business_name: str,
        city: Optional[str],
        google_maps_url: Optional[str],
    ) -> EnrichmentData:
        """nodriver implementation: open the place panel and extract rich data."""
        browser = NodriverBrowser(ephemeral=True)
        try:
            if google_maps_url and GoogleScraper.is_maps_url(google_maps_url):
                url = GoogleScraper.normalize_maps_url(google_maps_url)
            else:
                query = GoogleScraper.build_business_query(business_name, city)
                url = f"https://www.google.com/maps/search/{query}"

            tab = await browser.get_tab(url)
            await GoogleScraper.accept_cookies(tab)
            await GoogleScraper.accept_web_modal(tab)

            # If we landed on a results feed, open the first place.
            current = NodriverDom.tab_url(tab)
            if "/maps/place/" not in current:
                await NodriverDom.evaluate(
                    tab,
                    """
                    (() => {
                        const link = document.querySelector("div[role='feed'] a[href*='/maps/place/']");
                        if (link) { link.removeAttribute('target'); link.click(); return true; }
                        return false;
                    })()
                    """,
                    by_value=True,
                )

            if not await NodriverDom.wait_for_selector(tab, "h1", timeout_s=12.0):
                logger.info("Enrichment: place panel not found for %s", business_name)
                try:
                    page_html = await NodriverDom.evaluate(
                        tab, "document.documentElement.outerHTML", by_value=True
                    )
                except Exception:  # noqa: BLE001
                    page_html = None
                scrape_signals.note_block(
                    "enrichment",
                    reason="place panel not found (blocked/consent)",
                    html=page_html if isinstance(page_html, str) else None,
                )
                return EnrichmentData()

            # Best-effort: try to reveal the full opening-hours table.
            try:
                await NodriverDom.click_by_text(tab, "button", "horaires")
            except Exception:  # noqa: BLE001
                pass

            raw = await NodriverDom.evaluate(tab, f"JSON.stringify({_EXTRACT_JS})", by_value=True)
            data = json.loads(raw) if isinstance(raw, str) else {}
            return self._build_from_raw(data)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Enrichment scrape failed for %s: %s", business_name, exc)
            return EnrichmentData()
        finally:
            await browser.close()

    @staticmethod
    def _build_from_raw(data: dict[str, Any]) -> EnrichmentData:
        """Coerce the raw JS payload into a typed EnrichmentData.

        DOM selectors first, then JSON-LD (schema.org) as a stable fallback for
        description / rating / reviews_count when the obfuscated classes miss.
        """
        if not isinstance(data, dict):
            return EnrichmentData()

        def _as_float(value: Any) -> Optional[float]:
            try:
                return float(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        def _as_int(value: Any) -> Optional[int]:
            try:
                return int(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        photos = [str(p) for p in data.get("photos", []) if isinstance(p, str)]
        reviews = [r for r in data.get("reviews", []) if isinstance(r, dict)]
        hours = [h for h in data.get("opening_hours", []) if isinstance(h, dict)]
        social = {
            str(k): str(v)
            for k, v in (data.get("social") or {}).items()
            if isinstance(v, str) and v.strip()
        }

        # JSON-LD fallback (Google Maps place pages sometimes ship schema.org data).
        business = parse_ld_json_blocks(data.get("ld"))

        rating = _as_float(data.get("rating"))
        if rating is None and business:
            rating = _as_float(business.get("rating"))

        reviews_count = _as_int(data.get("reviews_count"))
        if reviews_count is None and business:
            reviews_count = _as_int(business.get("reviews_count"))

        dom_description = (
            str(data["description"]).strip() if data.get("description") else None
        ) or None
        description = dom_description
        if business and business.get("description"):
            # Prefer a JSON-LD description over the generic meta description fallback.
            description = str(business["description"]).strip() or dom_description

        return EnrichmentData(
            source="google",
            rating=rating,
            reviews_count=reviews_count,
            description=description,
            photos=photos,
            reviews=reviews,
            opening_hours=hours,
            social_links=social,
        )


enrichment_scraper = EnrichmentScraper()
