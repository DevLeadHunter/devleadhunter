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

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from scrappers import scrape_signals
from scrappers.google_scraper import GoogleScraper
from scrappers.maps_search_results import ListedPlace, MapsSearchOutcome, MapsSearchResults
from scrappers.nodriver_browser import NODRIVER_AVAILABLE, NodriverBrowser
from scrappers.nodriver_dom import NodriverDom
from scrappers.nodriver_executor import run_nodriver_task
from scrappers.osm_enrichment import enrich_from_osm
from scrappers.resilient_extract import parse_ld_json_blocks
from services.validation_service import validation_service

logger = logging.getLogger(__name__)


@dataclass
class EnrichmentData:
    """Structured rich data gathered for a prospect."""

    source: str = "google"
    logo_url: str | None = None
    rating: float | None = None
    reviews_count: int | None = None
    description: str | None = None
    website: str | None = None
    photos: list[str] = field(default_factory=list)
    reviews: list[dict[str, Any]] = field(default_factory=list)
    opening_hours: list[dict[str, str]] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    social_links: dict[str, str] = field(default_factory=dict)
    # Contact emails discovered while enriching (e.g. from the linked Facebook page) — folded into the
    # prospect's multi-email list. Usually empty from Google Maps, which rarely exposes an email.
    emails: list[str] = field(default_factory=list)
    # Identity of the Maps place the data was ACTUALLY read from — lets the
    # service reject a homonym's listing instead of silently absorbing it.
    # None on payloads from older desktop sidecars (identity check skipped).
    place_title: str | None = None
    place_city: str | None = None
    place_postal_code: str | None = None
    # Phone found on the page (Facebook « Coordonnées ») — backfills the prospect when it
    # has none. Transport-only: not persisted on the enrichment record (no column).
    phone: str | None = None
    maps_listing_found: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (matches the ProspectEnrichment columns)."""
        return {
            "source": self.source,
            "logo_url": self.logo_url,
            "rating": self.rating,
            "reviews_count": self.reviews_count,
            "description": self.description,
            "website": self.website,
            "photos": self.photos,
            "reviews": self.reviews,
            "opening_hours": self.opening_hours,
            "services": self.services,
            "social_links": self.social_links,
            "emails": self.emails,
            "place_title": self.place_title,
            "place_city": self.place_city,
            "place_postal_code": self.place_postal_code,
        }


# JS executed in the place page to gather everything in one round trip.
_EXTRACT_JS = r"""
(() => {
    const out = {
        rating: null, reviews_count: null, description: null, website: null,
        photos: [], reviews: [], opening_hours: [], ld: [], social: {},
        place_title: null
    };
    const txt = (el) => (el ? (el.innerText || el.textContent || '').trim() : '');

    // Title of the place panel — the name of the business the page is REALLY about.
    try {
        out.place_title = txt(document.querySelector('h1')) || null;
    } catch (e) {}

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
            const blockTxt = txt(block);
            const ratingM = blockTxt.match(/(\d+[.,]\d+)/);
            if (ratingM) { const r = parseFloat(ratingM[1].replace(',', '.')); if (!isNaN(r)) out.rating = r; }
            const aria = block.querySelector('[aria-label]');
            const ariaTxt = aria ? (aria.getAttribute('aria-label') || '') : '';
            // The count lives in parentheses ("(132)") — take it first; fall back to
            // the aria-label ("132 avis"). The old code only matched the aria form.
            let n = null;
            const parenM = blockTxt.match(/\(([\d\s.,  ]+)\)/);
            if (parenM) n = parseInt(parenM[1].replace(/[^\d]/g, ''), 10);
            if (n === null || isNaN(n)) {
                const ariaM = ariaTxt.match(/([\d][\d\s.,  ]*)\s*(avis|reviews|review)/i);
                if (ariaM) n = parseInt(ariaM[1].replace(/[^\d]/g, ''), 10);
            }
            if (n !== null && !isNaN(n)) out.reviews_count = n;
        }
    } catch (e) {}

    // Description / about (meta description as fallback)
    try {
        const meta = document.querySelector('meta[name="description"], meta[property="og:description"]');
        if (meta) out.description = (meta.getAttribute('content') || '').trim() || null;
    } catch (e) {}

    // Website link on the panel (data-item-id="authority", a stable semantic hook):
    // a real site means the prospect is NOT a « no website » target — surfaced so the
    // enrichment can double-check what the search scrapers may have missed.
    try {
        const site = document.querySelector('a[data-item-id="authority"]');
        const href = site ? (site.getAttribute('href') || '') : '';
        if (href && !/google\.[a-z.]+\/maps/i.test(href)) out.website = href.trim() || null;
    } catch (e) {}

    // Photos (large googleusercontent images, deduplicated). Scoped to the place panel: the page also
    // carries « Restaurants à proximité » thumbnails from OTHER businesses, outside div[role="main"].
    try {
        const seen = new Set();
        const scope = document.querySelector('div[role="main"]') || document;
        scope.querySelectorAll('img').forEach((img) => {
            let src = img.getAttribute('src') || '';
            if (!src || src.indexOf('googleusercontent') === -1) return;
            // keep only reasonably large images (skip tiny avatars)
            if (/=s\d{1,2}-/.test(src) || /=w\d{1,2}-/.test(src)) return;
            // normalize the size param to ONE large variant so the same photo — served here as a small
            // panel <img> and in the grid as a background-image thumb — collapses to an identical URL.
            src = /=[\w-]+$/.test(src) ? src.replace(/=[\w-]+$/, '=s1600') : (src + '=s1600');
            if (!seen.has(src)) { seen.add(src); out.photos.push(src); }
        });
        out.photos = out.photos.slice(0, 20);
    } catch (e) {}

    // Opening hours (table rows: day + hours, then div-based fallback)
    try {
        const pushHour = (day, hours) => {
            if (!day || !hours || day.length >= 24 || hours.length >= 48) return;
            const key = day.toLowerCase();
            if (out.opening_hours.some((row) => row.day.toLowerCase() === key)) return;
            out.opening_hours.push({ day, hours });
        };
        document.querySelectorAll('table tr').forEach((tr) => {
            const cells = tr.querySelectorAll('td, th');
            if (cells.length >= 2) pushHour(txt(cells[0]), txt(cells[1]));
        });
        if (out.opening_hours.length < 5) {
            document.querySelectorAll('[role="row"], li').forEach((row) => {
                const parts = txt(row).split('\\n').map((p) => p.trim()).filter(Boolean);
                if (parts.length >= 2) pushHour(parts[0], parts.slice(1).join(' '));
            });
        }
        out.opening_hours = out.opening_hours.slice(0, 7);
    } catch (e) {}

    // Reviews snippets present in the panel — deduplicated by author+text (the same review can be
    // rendered twice in the DOM, e.g. panel + expanded list), and capped generously so enough survive
    // the downstream "positive only" filter.
    try {
        const seenReviews = new Set();
        const blocks = document.querySelectorAll('div.jftiEf, div[data-review-id]');
        blocks.forEach((b) => {
            const author = txt(b.querySelector('.d4r55, .TSUbDb'));
            const text = txt(b.querySelector('.wiI7pd, .MyEned'));
            if (!text) return;
            const key = ((author || '') + '|' + text).toLowerCase().replace(/\\s+/g, ' ').trim();
            if (seenReviews.has(key)) return;
            seenReviews.add(key);
            const ratingEl = b.querySelector('[aria-label*="étoile"], [aria-label*="star"], .kvMYJc');
            let rating = null;
            if (ratingEl) {
                const m = (ratingEl.getAttribute('aria-label') || '').match(/([\d.,]+)/);
                if (m) rating = parseFloat(m[1].replace(',', '.'));
            }
            // « Réponse du propriétaire » — the owner's reply, often signed with a
            // first name (fuels the decision-maker resolution). Selector-free:
            // detected via the localized marker inside the block's inner text.
            let ownerResponse = null;
            try {
                const full = b.innerText || '';
                const marker = full.includes('Réponse du propriétaire')
                    ? 'Réponse du propriétaire'
                    : (full.includes('Response from the owner') ? 'Response from the owner' : null);
                if (marker) {
                    ownerResponse = full.split(marker)[1].replace(/^[\\s:.-]+/, '').trim().slice(0, 400) || null;
                }
            } catch (e) {}
            out.reviews.push({ author: author || 'Client', text, rating, owner_response: ownerResponse });
        });
        out.reviews = out.reviews.slice(0, 24);
    } catch (e) {}

    return out;
})()
"""

# Lightweight readiness probe — wave-2 hydration (review count + weekly hours).
_HYDRATION_READY_JS = r"""
(() => {
    const txt = (el) => (el ? (el.innerText || el.textContent || '').trim() : '');
    let hasReviewCount = false;
    const block = document.querySelector('div.F7nice');
    if (block) {
        const blockTxt = txt(block);
        hasReviewCount = /\([\d\s.,]+/.test(blockTxt);
        if (!hasReviewCount) {
            const aria = block.querySelector('[aria-label]');
            const ariaTxt = aria ? (aria.getAttribute('aria-label') || '') : '';
            hasReviewCount = /\d+\s*(avis|reviews|review)/i.test(ariaTxt);
        }
    }
    let hourRowCount = 0;
    document.querySelectorAll('table tr').forEach((tr) => {
        const cells = tr.querySelectorAll('td, th');
        if (cells.length >= 2 && txt(cells[0]) && txt(cells[1])) hourRowCount++;
    });
    let hasReviewsTab = false;
    for (const el of document.querySelectorAll('[role="tab"], button, [role="button"]')) {
        const label = txt(el).toLowerCase();
        if (label === 'avis' || label.startsWith('avis ') || label.includes('reviews')) {
            hasReviewsTab = true;
            break;
        }
    }
    return { hasReviewCount, hourRowCount, hasReviewsTab };
})()
"""

# Expand the weekly hours table before extraction. We deliberately DO NOT open the reviews
# tab: clicking it now triggers Google's ReviewsService, which demands a sign-in (auth wall)
# and dead-ends the scrape (browser lands on accounts.google.com and closes). Reviews are read
# straight from the main place panel instead — fewer of them, but no wall.
_PREPARE_PANEL_JS = r"""
(() => {
    const txt = (el) => (el ? (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim() : '');
    const clickNeedle = (needles) => {
        for (const el of document.querySelectorAll('button, [role="tab"], [role="button"], div[role="button"]')) {
            const label = txt(el).toLowerCase();
            if (needles.some((needle) => label.includes(needle))) {
                el.click();
                return true;
            }
        }
        return false;
    };
    return {
        hours: clickNeedle(['horaire', 'hours', 'opening']),
    };
})()
"""

# Open the place's photo grid via the hero « Voir les photos » button. The grid is the ONLY reliable
# prospect-scoped source: the panel and the raw page also carry « Restaurants à proximité » thumbnails
# from OTHER businesses, but the gallery shows only THIS place's photos.
_OPEN_PHOTOS_JS = r"""
(() => {
    const hero = document.querySelector('button[aria-label^="Photo de"] img, button[aria-label^="Photo of"] img');
    if (hero && (hero.getAttribute('src') || '').indexOf('streetviewpixels') !== -1) return false;
    const direct = document.querySelector('button.Dx2nRe');
    if (direct) { try { direct.click(); return true; } catch (e) {} }
    for (const el of document.querySelectorAll('button, [role="button"]')) {
        const label = (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim().toLowerCase();
        if (label === 'voir les photos' || label === 'voir toutes les photos' ||
            label.includes('see all photos') || label.includes('all photos') ||
            label.includes('toutes les photos')) {
            try { el.click(); return true; } catch (e) {}
        }
    }
    return false;
})()
"""

_OPEN_PHOTO_CATEGORY_JS = r"""
((labels) => {
    const nameOf = (el) => (el.getAttribute('aria-label') || el.innerText || el.textContent || '').trim().toLowerCase();
    // The reviews' topic filter has a « Tout » chip too: a photo category sits next to its siblings.
    const besidePhotoCategories = (el) => {
        let box = el.parentElement;
        for (let depth = 0; box && depth < 3; depth += 1, box = box.parentElement) {
            for (const other of box.querySelectorAll('button[aria-label], [role="tab"]')) {
                if (other !== el && /^(photos du propriétaire|by owner|street view)/.test(nameOf(other))) return true;
            }
        }
        return false;
    };
    for (const label of labels) {
        for (const el of document.querySelectorAll('button[aria-label], [role="tab"]')) {
            if (nameOf(el) !== label || (!/propriétaire|owner/.test(label) && !besidePhotoCategories(el))) continue;
            try { el.click(); return label; } catch (e) {}
        }
    }
    return null;
})(%s)
"""
_OPEN_PHOTO_COUNT_JS = r"""
(() => {
    for (const el of document.querySelectorAll("div[role='main'] *")) {
        if (el.children.length) continue;
        const text = (el.textContent || '').trim().toLowerCase();
        if (!/^\d[\d\s  .,]*\s+photos?$/.test(text)) continue;
        const target = el.closest('button, a, [role="button"], [jsaction]') || el;
        try { target.click(); return true; } catch (e) {}
    }
    return false;
})()
"""
_PHOTO_COUNT_JS = r"""
(() => {
    for (const el of document.querySelectorAll("div[role='main'] *")) {
        if (el.children.length) continue;
        const text = (el.textContent || '').trim().toLowerCase();
        const match = text.match(/^(\d[\d\s  .,]*)\s+photos?$/);
        if (match) return parseInt(match[1].replace(/\D/g, ''), 10);
    }
    return null;
})()
"""
# Scroll the place panel's own scroll container (not ``div[role=main]`` itself, which never scrolls).
_SCROLL_PLACE_PANEL_JS = r"""
(() => {
    const main = document.querySelector("div[role='main']");
    if (!main) return false;
    const scroller = [main, ...main.querySelectorAll('div')].find(
        (el) => el.scrollHeight > el.clientHeight + 50 && /auto|scroll/.test(getComputedStyle(el).overflowY)
    );
    if (!scroller) return false;
    scroller.scrollTop += 600;
    return true;
})()
"""
_ALL_PHOTOS_LABELS: tuple[str, ...] = ("tout", "all")
_OWNER_PHOTOS_LABELS: tuple[str, ...] = ("photos du propriétaire", "by owner")
_GRID_TILE_SELECTOR: str = "a.MIgS0d[data-photo-index]"
_PHOTO_SECTION_SCROLLS: int = 5
_PLAIN_LAYOUT_PHOTO_CAP: int = 10
_PLAIN_LAYOUT_REDRAWS: int = 3

# Read the OPEN photo grid. Each tile is `<a class="MIgS0d" data-photo-index>` whose picture is a
# `background-image` on an inner div (NOT an <img>). Videos are excluded (aria-label « Vidéo » / a
# `.bKP3Ce` duration badge). URLs are normalised to the same `=s1600` variant so identical shots dedup.
_GRID_PHOTOS_JS = r"""
(() => {
    const urls = [];
    const seen = new Set();
    const norm = (u) => /=[\w-]+$/.test(u) ? u.replace(/=[\w-]+$/, '=s1600') : (u + '=s1600');
    const grab = (bg) => {
        if (!bg || bg === 'none') return '';
        const m = bg.match(/url\((['"]?)(.*?)\1\)/);
        return m ? m[2] : '';
    };
    document.querySelectorAll('a.MIgS0d[data-photo-index]').forEach((a) => {
        const label = (a.getAttribute('aria-label') || '').toLowerCase();
        if (label.indexOf('vidéo') !== -1 || label.indexOf('video') !== -1) return;
        if (a.querySelector('.bKP3Ce')) return;
        const outer = a.querySelector('.aHpZye');
        const inner = a.querySelector('.gCPOGf');
        let src = grab(outer && outer.style.backgroundImage) || grab(inner && inner.style.backgroundImage);
        if (!src || src.indexOf('googleusercontent') === -1) return;
        src = norm(src);
        if (!seen.has(src)) { seen.add(src); urls.push(src); }
    });
    return urls;
})()
"""

# Nudge the grid's own virtualised scroll container down one step, reading after each so unloaded tiles
# are not missed.
_GRID_SCROLL_JS = r"""
(() => {
    const anchors = document.querySelectorAll('a.MIgS0d[data-photo-index]');
    if (!anchors.length) return 0;
    let el = anchors[anchors.length - 1];
    let scroller = null;
    while (el && el !== document.body) {
        if (el.scrollHeight > el.clientHeight + 40) { scroller = el; break; }
        el = el.parentElement;
    }
    if (scroller) scroller.scrollTop = scroller.scrollTop + 1200;
    return anchors.length;
})()
"""

# Close the open photo gallery (its « Retour » / back control) so the place panel comes back WITHOUT a
# page reload. Best-effort: if no control matches, the caller's panel-completeness check re-anchors.
_CLOSE_GALLERY_JS = r"""
(() => {
    const labels = ['retour', 'back', 'fermer', 'close'];
    for (const el of document.querySelectorAll('button, [role="button"], a[aria-label]')) {
        const t = (el.getAttribute('aria-label') || el.innerText || el.textContent || '').trim().toLowerCase();
        if (labels.some((l) => t === l || t.startsWith(l + ' '))) {
            try { el.click(); return true; } catch (e) {}
        }
    }
    return false;
})()
"""

_SEARCH_LANDING_JS = r"""
(() => {
    if (document.querySelector("div[role='feed'] a[href*='/maps/place/'][aria-label]")) return 'results';
    const title = ((document.querySelector('h1') || {}).innerText || '').trim();
    const isResultsHeading = /^(résultats|results)$/i.test(title);
    if (title && !isResultsHeading && !location.hostname.startsWith('consent.')) return 'place';
    return '';
})()
"""

_LISTED_PLACES_JS = r"""
JSON.stringify([...document.querySelectorAll("div[role='feed'] a[href*='/maps/place/'][aria-label]")].map((link) => ({
    name: (link.getAttribute('aria-label') || '').trim(),
    link: link.href,
})))
"""

_PLACE_ADDRESS_SELECTORS: list[str] = ["button[data-item-id='address']", "[data-item-id^='address']"]
_SEARCH_LANDING_TIMEOUT_S: float = 15.0
_RESULTS_LIST_RENDER_DELAY_S: float = 1.0

# A « complete » place panel carries a rating+review count or an « Avis » tab. Google intermittently
# serves logged-out scrapers a STRIPPED panel (no count, only Présentation / À propos) — but that
# render still has the « Voir les photos » button, so the button is NOT a completeness signal (it would
# wrongly pass the stripped panel); the review count / Avis tab are what the stripped render lacks.
_PANEL_COMPLETE_JS = r"""
(() => {
    const f = document.querySelector('div.F7nice');
    if (f && /\([\d\s.,]+\)/.test(f.innerText || f.textContent || '')) return true;
    for (const el of document.querySelectorAll('[role="tab"], button')) {
        const t = (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim().toLowerCase();
        if (t === 'avis' || t.startsWith('avis ') || t.includes('reviews')) return true;
    }
    return false;
})()
"""

# The place's business-name <h1>, read BEFORE the hours are expanded — expanding them swaps this
# heading for « Horaires », which would then masquerade as the place title.
_PLACE_TITLE_JS = r"((document.querySelector('h1') || {}).innerText || '').trim()"

_ENRICHMENT_MAX_ATTEMPTS: int = 4
_ENRICHMENT_POLL_INTERVAL_S: float = 1.5
_ENRICHMENT_MIN_HOUR_ROWS: int = 5

# How many times to reload a STRIPPED Maps panel (no count / gallery) before enriching with what we have.
_MAX_PANEL_RELOADS: int = 2

# Section headers Google Maps promotes to <h1> when a sub-panel (weekly hours, reviews, photos…) is
# open. Read as the place title they never match the business name, so the homonym guard would reject
# the whole enrichment — we drop them and fall back to the real name instead.
_MAPS_SECTION_TITLES: frozenset[str] = frozenset(
    {
        "horaires",
        "avis",
        "photos",
        "à propos",
        "a propos",
        "présentation",
        "presentation",
        "hours",
        "reviews",
        "about",
        "overview",
    }
)


def _clean_place_title(raw: str | None) -> str | None:
    """Return the place title, or None when it is a Google Maps section header.

    Expanding the weekly hours (needed to read them) makes Google insert a « Horaires » <h1>; read as
    the place title it poisons the homonym guard, so a section header is dropped and the caller falls
    back to the real business name.
    """
    title = (raw or "").strip()
    if not title:
        return None
    return None if title.lower() in _MAPS_SECTION_TITLES else title


def _average_hash(image_bytes: bytes) -> int | None:
    """A 64-bit average hash (aHash) of an image — the SAME picture shares it despite re-uploads,
    resizes or CDN params (which a URL/id dedup can't catch). None on decode failure."""
    try:
        from io import BytesIO

        from PIL import Image  # Pillow is already a dependency (brand_color_service).

        image = Image.open(BytesIO(image_bytes)).convert("L").resize((8, 8))
        pixels = list(image.tobytes())
        average = sum(pixels) / len(pixels)
        bits = 0
        for index, pixel in enumerate(pixels):
            if pixel >= average:
                bits |= 1 << index
        return bits
    except Exception:
        return None


@dataclass(frozen=True)
class PhotoTraits:
    """What a gallery photo looks like: its size, its contrast and how much of it is one flat colour."""

    width: int
    height: int
    contrast: float
    flat_colour_share: float
    colour_count: int
    look_hash: int


@dataclass(frozen=True)
class CuratedGallery:
    """The photos that can illustrate a site, and the logo that goes with them."""

    photos: list[str]
    logo_url: str | None


_MIN_PHOTO_SIDE_PX: int = 400
_MIN_PHOTO_CONTRAST: float = 12.0
_GRAPHIC_FLAT_COLOUR_SHARE: float = 0.6
_GRAPHIC_MAX_COLOURS: int = 170
_LOGO_MIN_FLAT_COLOUR_SHARE: float = 0.2
_LOGO_MIN_SQUARENESS: float = 0.8
_LOGO_LOOK_DISTANCE: int = 10
_SAME_PHOTO_LOOK_DISTANCE: int = 4


def _hamming_distance(left: int, right: int) -> int:
    """Number of differing bits between two hashes (0 = identical look)."""
    return bin(left ^ right).count("1")


# Placeholder authors that can legitimately leave several distinct snippets in one scrape.
_GENERIC_REVIEW_AUTHORS = frozenset(
    {
        "client",
        "anonyme",
        "anonymous",
        "google user",
        "a google user",
        "utilisateur google",
    }
)


def _norm_review_value(value: Any) -> str:
    """Collapse whitespace/case so the same snippet scraped twice still matches."""
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _is_distinctive_review_author(author: str) -> bool:
    """True when the author is a real name we can use as a review identity."""
    key = _norm_review_value(author)
    return bool(key) and key not in _GENERIC_REVIEW_AUTHORS


def _dedupe_reviews(reviews: list[Any]) -> list[dict[str, Any]]:
    """Drop duplicate reviews, preserving first-seen order.

    Exact same body (whitespace/case-insensitive) is always collapsed. A named author is
    kept once: Facebook re-emits the same person with a slightly different body (Relay JSON
    vs DOM chrome, or a second enrichment run), and Google's panel + expanded list do the
    same. Generic placeholders like « Client » still keep distinct texts.
    """
    seen_texts: set[str] = set()
    seen_authors: set[str] = set()
    unique: list[dict[str, Any]] = []
    for review in reviews:
        if not isinstance(review, dict):
            continue
        text = _norm_review_value(review.get("text"))
        if not text:
            continue
        author = _norm_review_value(review.get("author"))
        if text in seen_texts:
            continue
        if _is_distinctive_review_author(author) and author in seen_authors:
            continue
        seen_texts.add(text)
        if _is_distinctive_review_author(author):
            seen_authors.add(author)
        unique.append(review)
    return unique


class GalleryCuration:
    """Keeps the photos that can illustrate a site: no logo, flyer, blur or blank banner, no visual duplicate."""

    @staticmethod
    def traits_of(image_bytes: bytes) -> PhotoTraits | None:
        """
        Read what a photo looks like, or ``None`` when the bytes are not an image.

        Args:
            image_bytes: The downloaded image.

        Returns:
            Its size, contrast, flat-colour share, colour count (over 16 levels a channel) and look hash.
        """
        try:
            from collections import Counter
            from io import BytesIO

            from PIL import Image, ImageStat

            image = Image.open(BytesIO(image_bytes)).convert("RGB")
        except Exception:
            return None
        look_hash = _average_hash(image_bytes)
        if look_hash is None:
            return None
        pixels = image.resize((64, 64)).tobytes()
        colours = Counter(
            (pixels[index] // 16, pixels[index + 1] // 16, pixels[index + 2] // 16)
            for index in range(0, len(pixels), 3)
        )
        return PhotoTraits(
            width=image.width,
            height=image.height,
            contrast=ImageStat.Stat(image.convert("L")).stddev[0],
            flat_colour_share=colours.most_common(1)[0][1] / (64 * 64),
            colour_count=len(colours),
            look_hash=look_hash,
        )

    @staticmethod
    def unfit_reason(traits: PhotoTraits) -> str | None:
        """
        Why a photo cannot illustrate a site, or ``None`` when it can.

        Too small under 400 px on its longest side (a Facebook cover kept at 320 px is a blur), blank
        under a grey-level spread of 12, a graphic when one flat colour covers 60 % of it in 170 colours
        or fewer — a logo or a flyer (measured 7 Oct 2026: logos 66-88 % in 42-161 colours, real photos
        5-13 % in 178-374 colours).
        """
        if max(traits.width, traits.height) < _MIN_PHOTO_SIDE_PX:
            return "too small"
        if traits.contrast < _MIN_PHOTO_CONTRAST:
            return "blank"
        if traits.flat_colour_share >= _GRAPHIC_FLAT_COLOUR_SHARE and traits.colour_count <= _GRAPHIC_MAX_COLOURS:
            return "graphic"
        return None

    @staticmethod
    def is_photo(traits: PhotoTraits) -> bool:
        """
        Whether an image is a real photo, never a logo: no flat background.

        Measured 7 Oct 2026 on the Facebook profile pictures taken as logos: a garage front and a tree
        surgeon at work had 13-16 % of one flat colour, real logos 34-77 %. A logo printed on a stone
        texture (15 %) reads as a photo too: no logo beats a photo in the logo's place.
        """
        return traits.flat_colour_share < _LOGO_MIN_FLAT_COLOUR_SHARE

    @staticmethod
    def is_square_graphic(traits: PhotoTraits) -> bool:
        """Whether an image refused as a graphic has a logo's shape: a square or nearly so."""
        squareness = min(traits.width, traits.height) / max(traits.width, traits.height, 1)
        return GalleryCuration.unfit_reason(traits) == "graphic" and squareness >= _LOGO_MIN_SQUARENESS

    @classmethod
    async def curate(cls, urls: list[str], *, logo_url: str | None = None) -> list[str]:
        """
        Keep the photos of a gallery that can illustrate a site, in their order.

        Args:
            urls: The gallery, in order.
            logo_url: The business's logo, whose re-uploads are no gallery photo.

        Returns:
            The kept photos, in their order.
        """
        return (await cls.curate_gallery(urls, logo_url=logo_url)).photos

    @classmethod
    async def curate_gallery(cls, urls: list[str], *, logo_url: str | None = None) -> CuratedGallery:
        """
        Keep the photos of a gallery that can illustrate a site, in their order, and settle its logo.

        Downloads each image once (parallel, best-effort; a ``data:`` URI is decoded in place) and drops
        the ones :meth:`unfit_reason` refuses, the logo re-uploaded as a photo, and visual duplicates. On
        any download/decode failure the URL is kept (never silently dropped). A logo that is in fact a
        photo (a Facebook profile picture of the shop front) is no logo; without a logo, the first square
        graphic of the gallery is (a listing whose only image is its logo).

        The average hash is coarse (8×8), so the SAME image re-served sits at distance ~0-2 while two
        DISTINCT shots of one subject can reach ~6 — a threshold of 6 dropped real, different photos
        (measured on a live listing), so 4 keeps them while still collapsing genuine re-uploads.

        Args:
            urls: The gallery, in order.
            logo_url: The business's logo, whose re-uploads are no gallery photo.

        Returns:
            The kept photos, in their order, and the logo.
        """
        if not urls and not logo_url:
            return CuratedGallery(photos=[], logo_url=None)

        import base64

        import httpx

        semaphore = asyncio.Semaphore(8)

        async def _traits_of(client: httpx.AsyncClient, url: str) -> PhotoTraits | None:
            if url.startswith("data:"):
                try:
                    return cls.traits_of(base64.b64decode(url.split(",", 1)[1]))
                except Exception:
                    return None
            async with semaphore:
                try:
                    response = await client.get(url)
                except Exception:
                    return None
                return cls.traits_of(response.content) if response.status_code == 200 else None

        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                traits = await asyncio.gather(
                    *[_traits_of(client, url) for url in [*urls, *([logo_url] if logo_url else [])]]
                )
        except Exception:
            return CuratedGallery(photos=list(urls), logo_url=logo_url)

        logo_traits = traits.pop() if logo_url else None
        if logo_traits is not None and cls.is_photo(logo_traits):
            logger.info("Enrichment: a photo is no logo: %s", (logo_url or "")[:80])
            logo_url, logo_traits = None, None
        kept: list[str] = []
        kept_look_hashes: list[int] = []
        for url, photo in zip(urls, traits):
            if photo is None:
                kept.append(url)
                continue
            reason = cls.unfit_reason(photo)
            if (
                reason is None
                and logo_traits is not None
                and _hamming_distance(photo.look_hash, logo_traits.look_hash) <= _LOGO_LOOK_DISTANCE
            ):
                reason = "logo"
            if reason is not None:
                if logo_url is None and cls.is_square_graphic(photo):
                    logo_url, logo_traits = url, photo
                logger.info("Enrichment: photo left out of the gallery (%s): %s", reason, url[:80])
                continue
            if any(_hamming_distance(photo.look_hash, seen) <= _SAME_PHOTO_LOOK_DISTANCE for seen in kept_look_hashes):
                continue
            kept.append(url)
            kept_look_hashes.append(photo.look_hash)
        return CuratedGallery(photos=kept, logo_url=logo_url)


class EnrichmentScraper:
    """Gathers rich Google Maps place data for a single prospect."""

    async def enrich(
        self,
        *,
        business_name: str,
        city: str | None = None,
        google_maps_url: str | None = None,
        facebook_url: str | None = None,
        country: str = "FR",
    ) -> EnrichmentData:
        """Fetch enrichment for a business: Google Maps (rich) + OpenStreetMap (stable gap-filler).

        Google is the primary source (photos, reviews, rating); OpenStreetMap fills the fields
        Google is weak/blocked on (opening hours, social links, description) via a plain HTTP API.
        OSM runs even when nodriver is unavailable, so enrichment degrades gracefully instead of
        returning nothing. With no Google listing but a Facebook page, the read is delegated to the
        Facebook scraper instead — Google wins whenever its URL is present. ``country`` is the
        prospect's: it restricts the OSM lookup and tells the Facebook reader which postal code
        and phone shapes to expect.
        """
        # No Google listing to anchor on → read the Facebook page instead (many artisans only have one).
        if not (google_maps_url or "").strip() and (facebook_url or "").strip():
            from scrappers.facebook_enrichment_scraper import facebook_enrichment_scraper

            fb_only = await facebook_enrichment_scraper.enrich(
                business_name=business_name, facebook_url=facebook_url or "", country=country
            )
            gallery = await GalleryCuration.curate_gallery(fb_only.photos, logo_url=fb_only.logo_url)
            fb_only.photos, fb_only.logo_url = gallery.photos, gallery.logo_url
            fb_only.reviews = _dedupe_reviews(fb_only.reviews)
            return fb_only

        data = EnrichmentData()
        if NODRIVER_AVAILABLE:

            async def task() -> EnrichmentData:
                return await self._enrich_nodriver(business_name, city, google_maps_url, country)

            data = await run_nodriver_task(task, timeout=180)
        else:
            logger.warning("nodriver not available — Google enrichment skipped, OSM only")

        # Complementary OpenStreetMap enrichment (plain HTTP, no browser, never blocked).
        try:
            osm = await enrich_from_osm(business_name, city, country)
        except Exception as exc:
            logger.info("OSM enrichment failed for %s: %s", business_name, exc)
            osm = {}
        self._merge_osm(data, osm)

        # Complementary Facebook read: the Maps listing often links a Facebook page that carries
        # opening hours / social links / a contact email Google doesn't expose. Prefer the FB URL
        # found on THIS listing; fall back to the one stored on the prospect (same business), so a
        # manually-added FB page still enriches even when Google links only Instagram or is walled.
        facebook_url = self._facebook_url_from_data(data) or (facebook_url or "").strip() or None
        if facebook_url and NODRIVER_AVAILABLE:
            try:
                from scrappers.facebook_enrichment_scraper import facebook_enrichment_scraper

                facebook = await facebook_enrichment_scraper.enrich(
                    business_name=business_name, facebook_url=facebook_url
                )
                self._merge_facebook(data, facebook)
            except Exception as exc:
                logger.info("Facebook complementary enrichment failed for %s: %s", business_name, exc)

        # Curated once the full set (Google, then Facebook) is assembled, before it reaches the gallery.
        gallery = await GalleryCuration.curate_gallery(data.photos, logo_url=data.logo_url)
        data.photos, data.logo_url = gallery.photos, gallery.logo_url
        data.reviews = _dedupe_reviews(data.reviews)
        return data

    @staticmethod
    def _facebook_url_from_data(data: EnrichmentData) -> str | None:
        """Return a Facebook page URL discovered on the Maps listing (a social link, or the "website"
        link when it points to ``facebook.com``), or None."""
        candidate = (data.social_links or {}).get("facebook")
        if not candidate and "facebook.com/" in (data.website or "").lower():
            candidate = data.website
        candidate = (candidate or "").strip()
        return candidate or None

    @staticmethod
    def _merge_facebook(data: EnrichmentData, facebook: EnrichmentData) -> None:
        """Fill gaps in the Google-sourced data with the linked Facebook page (Google wins where present)."""
        if not data.opening_hours and facebook.opening_hours:
            data.opening_hours = facebook.opening_hours
        if facebook.social_links:
            data.social_links = {**facebook.social_links, **(data.social_links or {})}
        if not data.description and facebook.description:
            data.description = facebook.description
        if not data.services and facebook.services:
            data.services = facebook.services
        if facebook.emails:
            data.emails = [*data.emails, *facebook.emails]
        # Photos: keep Google's first (most relevant), then APPEND Facebook's as a secondary source —
        # better too many than too few; the enrichment panel lets the user reorder / pick the best.
        if facebook.photos:
            from scrappers.facebook_enrichment_scraper import photo_identity

            seen: set[str] = {photo_identity(url) for url in data.photos if url}
            for url in facebook.photos:
                key = photo_identity(url) if url else ""
                if url and key not in seen and len(data.photos) < 40:
                    data.photos.append(url)
                    seen.add(key)
        # Logo: Google Maps never exposes one, so the Facebook profile photo fills it when present.
        if not (data.logo_url or "").strip() and (facebook.logo_url or "").strip():
            data.logo_url = facebook.logo_url
        if "facebook" not in data.source:
            data.source = f"{data.source}+facebook"

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
        city: str | None,
        google_maps_url: str | None,
        country: str,
    ) -> EnrichmentData:
        """nodriver implementation: open the place panel and extract rich data."""
        browser = NodriverBrowser(ephemeral=True)
        try:
            is_search = not (google_maps_url and GoogleScraper.is_maps_url(google_maps_url))
            if is_search:
                query = GoogleScraper.build_business_query(business_name, city)
                url = f"https://www.google.com/maps/search/{query}"
            else:
                url = GoogleScraper.normalize_maps_url(google_maps_url or "")

            tab = await browser.get_tab(url)
            listing = await self._open_listing(
                tab, business_name=business_name, city=city, country=country, is_search=is_search
            )
            if listing is MapsSearchOutcome.NOT_LISTED:
                logger.info("Enrichment: Maps lists no place named like %s in %s", business_name, city)
                return EnrichmentData(maps_listing_found=False)
            if listing is not MapsSearchOutcome.OPENED:
                logger.info("Enrichment: place panel not found for %s", business_name)
                try:
                    page_html = await NodriverDom.evaluate(tab, "document.documentElement.outerHTML", by_value=True)
                except Exception:
                    page_html = None
                scrape_signals.note_block(
                    "enrichment",
                    reason="place panel not found (blocked/consent)",
                    html=page_html if isinstance(page_html, str) else None,
                )
                return EnrichmentData()

            # Google intermittently serves logged-out scrapers a STRIPPED panel (no review count, no
            # photo gallery); reload until it renders the full one so the count and photos survive.
            await self._ensure_complete_panel(tab, url)
            await self._wait_for_maps_hydration(tab)
            # A place opened from its « cid » link may keep that URL: either one reloads the place.
            current_url = NodriverDom.tab_url(tab)
            place_url = current_url if "/maps/place/" in current_url else url
            # Capture the business-name h1 BEFORE extraction expands the hours: expanding them makes
            # Google swap the first h1 for « Horaires », which would then poison the identity guard.
            place_title = await self._read_place_title(tab)

            # Photos come ONLY from the grid (this place's shots; the panel/page also carry « Restaurants
            # à proximité » thumbnails from OTHER businesses). Read it HERE, on the still-fresh panel,
            # before extraction expands the hours and hides the « Voir les photos » button — reading now
            # avoids the ~3s re-anchor reload the button-gone path would need. The gallery is closed after.
            early_photos = await self._read_photo_grid_then_close(tab, place_url=place_url, place_title=place_title)
            # If the fresh-panel read left us off the place panel (gallery still open / navigated away),
            # re-anchor so extraction runs on a real panel — the same reload the old order always paid,
            # now paid only when the gallery didn't close cleanly.
            if (
                NodriverDom.tab_url(tab) != current_url
                or not await self._panel_is_complete(tab)
                or (place_title and await self._read_place_title(tab) != place_title)
            ):
                await NodriverDom.navigate(tab, place_url)
                await self._open_place_panel(tab)

            data = await self._extract_with_retries(tab, business_name=business_name, city=city)
            data.maps_listing_found = True
            if place_title:
                data.place_title = place_title

            if early_photos:
                data.photos = early_photos
            else:
                # The fresh-panel read found nothing; extraction has since hidden the button, so re-anchor
                # to a fresh panel and read the grid the proven way (verified logged-out: 10 tiles).
                data.photos = []
                await NodriverDom.navigate(tab, place_url)
                await self._open_place_panel(tab)
                await self._grab_more_photos(tab, data, place_url=place_url, place_title=place_title)
            return data
        except Exception as exc:
            logger.warning("Enrichment scrape failed for %s: %s", business_name, exc)
            return EnrichmentData()
        finally:
            await browser.close()

    async def _wait_for_maps_hydration(self, tab: Any, *, timeout_s: float = 18.0) -> None:
        """Wait until the place panel's wave-2 data (review count / weekly hours) has settled.

        Returns as soon as EITHER strong signal is present — the review count has rendered, or the
        weekly hours table is full — otherwise as soon as the hour count stops growing. A sparse-hours
        listing (food truck, few open days) never reaches a full week and may have no review count, so
        without the stabilisation exit it would burn the entire timeout every run (the ~30s stall).
        Only a genuinely blank/slow panel now waits the timeout out.
        """
        deadline = asyncio.get_running_loop().time() + timeout_s
        previous_hours = -1
        stable_polls = 0
        while asyncio.get_running_loop().time() < deadline:
            status = await self._read_hydration_status(tab)
            hours = int(status.get("hourRowCount", 0) or 0)
            # The review count is the clearest « panel hydrated » marker (stars show first, the count
            # lands with wave-2); a full week of hours is the other. Either one → done.
            if status.get("hasReviewCount") or hours >= _ENRICHMENT_MIN_HOUR_ROWS:
                return
            # No count yet and only partial hours: stop once the hours stop growing, so we don't wait
            # for a 5th row that will never come.
            if hours > 0 and hours == previous_hours:
                stable_polls += 1
                if stable_polls >= 2:
                    return
            else:
                stable_polls = 0
            previous_hours = hours
            await asyncio.sleep(0.5)

    async def _read_hydration_status(self, tab: Any) -> dict[str, Any]:
        """Return the current hydration markers from the place panel."""
        raw = await NodriverDom.evaluate(tab, f"JSON.stringify({_HYDRATION_READY_JS})", by_value=True)
        if not isinstance(raw, str):
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    async def _read_place_title(self, tab: Any) -> str | None:
        """Read the place panel's business-name h1, dropping any section header.

        Read BEFORE the hours are expanded, so the first h1 is still the business name and not the
        « Horaires » sub-panel header that would otherwise poison the identity guard.
        """
        raw = await NodriverDom.evaluate(tab, _PLACE_TITLE_JS, by_value=True)
        return _clean_place_title(raw if isinstance(raw, str) else None)

    async def _panel_is_complete(self, tab: Any) -> bool:
        """True when the place panel looks fully rendered (photos button / review count / avis tab)."""
        return await NodriverDom.evaluate(tab, _PANEL_COMPLETE_JS, by_value=True) is True

    async def _wait_for_complete_panel(self, tab: Any, *, timeout_s: float = 10.0) -> bool:
        """Poll until the panel is complete, or the timeout signals Google served a stripped render."""
        deadline = asyncio.get_running_loop().time() + timeout_s
        while asyncio.get_running_loop().time() < deadline:
            if await self._panel_is_complete(tab):
                return True
            await asyncio.sleep(0.5)
        return False

    async def _open_place_panel(self, tab: Any) -> bool:
        """Dismiss consent and wait for the place h1."""
        await GoogleScraper.accept_cookies(tab)
        await GoogleScraper.accept_web_modal(tab)
        return await NodriverDom.wait_for_selector(tab, "h1", timeout_s=12.0)

    async def _open_listing(
        self, tab: Any, *, business_name: str, city: str | None, country: str, is_search: bool
    ) -> MapsSearchOutcome:
        """
        Open the business's place, and only it.

        A stored place link opens the place itself. A « nom + ville » search opens a place only when it
        carries the business's name in the business's town: the one Maps opens when it is sure of the
        search, or one of the results it lists when it is not. The list's own heading (« Résultats »)
        is never read as a place.

        Args:
            tab: The tab on the Maps search or place URL.
            business_name: The prospect's business name.
            city: The prospect's town, if known.
            country: The prospect's country, deciding how an address is read.
            is_search: Whether the tab opened a « nom + ville » search rather than a stored place link.

        Returns:
            OPENED when the business's place panel is open, NOT_LISTED when Maps shows no place of that
            name in that town, UNREACHABLE when Maps showed neither a place nor a list.
        """
        await GoogleScraper.accept_cookies(tab)
        await GoogleScraper.accept_web_modal(tab)
        landing = await self._wait_for_search_landing(tab)
        if landing == "place":
            if not is_search:
                return MapsSearchOutcome.OPENED
            title = await self._read_place_title(tab)
            is_business_place = MapsSearchResults.is_named_like(title or "", business_name, town=city) and not (
                MapsSearchResults.is_in_other_town(await self._read_place_address(tab), city=city, country=country)
            )
            if is_business_place:
                return MapsSearchOutcome.OPENED
            logger.info("Enrichment: the place Maps opened (« %s ») is not %s, passed over", title, business_name)
            return MapsSearchOutcome.NOT_LISTED
        if landing != "results":
            return MapsSearchOutcome.UNREACHABLE
        for place in MapsSearchResults.places_named_like(await self._read_listed_places(tab), business_name, town=city):
            await NodriverDom.navigate(tab, place.link)
            if not await self._open_place_panel(tab):
                continue
            address = await self._read_place_address(tab)
            if MapsSearchResults.is_in_other_town(address, city=city, country=country):
                logger.info("Enrichment: listed place « %s » is in another town (%s), passed over", place.name, address)
                continue
            return MapsSearchOutcome.OPENED
        return MapsSearchOutcome.NOT_LISTED

    async def _wait_for_search_landing(self, tab: Any) -> str:
        """
        Wait until the search shows a place or a results list, the list's later cards included.

        Returns:
            « place », « results », or '' when Maps showed neither in time.
        """
        deadline = asyncio.get_running_loop().time() + _SEARCH_LANDING_TIMEOUT_S
        while asyncio.get_running_loop().time() < deadline:
            landing = await NodriverDom.evaluate(tab, _SEARCH_LANDING_JS, by_value=True)
            if landing == "results":
                await asyncio.sleep(_RESULTS_LIST_RENDER_DELAY_S)
                return "results"
            if landing == "place":
                return "place"
            if "consent." in NodriverDom.tab_url(tab):
                await GoogleScraper.accept_cookies(tab)
            await asyncio.sleep(0.5)
        return ""

    @staticmethod
    async def _read_listed_places(tab: Any) -> list[ListedPlace]:
        """The places of the results list on screen, in the list's order, each once."""
        raw = await NodriverDom.evaluate(tab, _LISTED_PLACES_JS, by_value=True)
        try:
            cards = json.loads(raw) if isinstance(raw, str) else []
        except json.JSONDecodeError:
            return []
        places_by_link: dict[str, ListedPlace] = {}
        for card in cards:
            name, link = str(card.get("name") or "").strip(), str(card.get("link") or "").strip()
            if name and link:
                places_by_link.setdefault(link, ListedPlace(name=name, link=link))
        return list(places_by_link.values())

    @staticmethod
    async def _read_place_address(tab: Any) -> str | None:
        """The address the open place's panel shows, or None for a place listed without one."""
        if not await NodriverDom.wait_for_selector(tab, _PLACE_ADDRESS_SELECTORS[0], timeout_s=3.0):
            return None
        return await NodriverDom.inner_text_chain(tab, _PLACE_ADDRESS_SELECTORS)

    async def _ensure_complete_panel(self, tab: Any, url: str) -> str:
        """Reload the place until Google serves the FULL panel, and return the place URL for re-anchors.

        Google intermittently strips a logged-out panel of its review count / photo gallery; re-running
        by hand shows a reload lands on the complete render. The returned URL anchors later re-opens.
        """
        place_url = NodriverDom.tab_url(tab)
        complete = await self._wait_for_complete_panel(tab)
        for reload_index in range(_MAX_PANEL_RELOADS):
            if complete:
                break
            logger.info("Enrichment: stripped Maps panel — reloading (%s/%s)", reload_index + 1, _MAX_PANEL_RELOADS)
            await asyncio.sleep(1.5)
            await NodriverDom.navigate(tab, place_url if "/maps/place/" in place_url else url)
            if not await self._open_place_panel(tab):
                break
            place_url = NodriverDom.tab_url(tab)
            complete = await self._wait_for_complete_panel(tab)
        return place_url

    async def _prepare_panel_for_extraction(self, tab: Any) -> None:
        """Expand hours and scroll to lazy-load photos.

        NOTE: we deliberately do NOT click Google's « Envoyer des commentaires / Connectez-vous »
        card (rap.signInCard). Clicking its « Fermer » made Google loop the panel open↔closed and
        stalled the scrape far worse — so we leave it be and just read what the DOM already holds.
        """
        try:
            await NodriverDom.evaluate(tab, _PREPARE_PANEL_JS, by_value=True)
            await asyncio.sleep(0.8)
        except Exception:
            pass

        try:
            for _ in range(6):
                await NodriverDom.scroll_element(tab, "div[role='main']", 1400)
                await asyncio.sleep(0.45)
        except Exception:
            pass

    async def _collect_open_grid(
        self,
        tab: Any,
        *,
        seed: list[str] | None = None,
        place_url: str | None = None,
        place_title: str | None = None,
    ) -> list[str] | None:
        """Open the photo grid and read it, returning THIS place's photo URLs, the business's own first.

        The grid is the only reliably prospect-scoped source (the panel and page also carry nearby
        businesses' thumbnails). Logged out, the hero viewer stops at about ten photos while the grid
        opened from the « Photos » section lists them all; the « Photos du propriétaire » tab then puts
        the business's own uploads first. The result starts from ``seed`` (already-known URLs).

        Args:
            tab: The Maps tab, on the place panel.
            seed: Photo URLs already known, kept first.
            place_url: The place's URL, to come back to it.
            place_title: The place's heading, to tell when a click left the panel (Street View).

        Returns:
            The photo URLs, or ``None`` when no grid opens, so the caller can pick its fallback.
        """
        opener = await self._open_photo_grid(tab, place_url=place_url, place_title=place_title)
        if opener is None:
            return None
        every_photo = await self._read_open_grid(tab)
        owner_photos = await self._read_photo_category(tab, _OWNER_PHOTOS_LABELS) or []
        logger.info(
            "Enrichment: photo grid opened by %s — %s photo(s), %s from the owner",
            opener,
            len(every_photo),
            len(owner_photos),
        )
        merged = list(dict.fromkeys(url for url in [*(seed or []), *owner_photos, *every_photo] if url))
        return merged[:40]

    async def _open_photo_grid(self, tab: Any, *, place_url: str | None, place_title: str | None) -> str | None:
        """
        Open the place's photo grid: its « Tout » category, else the section's « N photos », else the hero.

        Logged out, the hero viewer stops at about ten photos (31 against 10 on a Swiss landscaper, 7 Oct
        2026) and a Street View hero strands the scrape in Street View, so the hero comes last and never
        when it shows Street View. Google serves the place panel in two layouts, about half the time each
        — with category chips under « Photos et vidéos », or a plain « Photos » section reading « 32
        photos » whose grid stops at about ten — and renders either only once the panel is scrolled down
        to it. Reloading does not choose the layout, but clearing the cookies draws it again (measured 7 Oct
        2026: category, plain, category over three draws): a plain panel announcing more photos than its
        grid shows is drawn again up to three times.

        Args:
            tab: The Maps tab, on the place panel.
            place_url: The place's URL, to come back to it.
            place_title: The place's heading, to tell when a click left the panel (Street View).

        Returns:
            Which opener worked, or ``None`` when no grid opened.
        """
        category_opener = _OPEN_PHOTO_CATEGORY_JS % json.dumps(list(_ALL_PHOTOS_LABELS))
        redraws_left = _PLAIN_LAYOUT_REDRAWS
        redraws_without_count_left = 1
        while True:
            for _ in range(_PHOTO_SECTION_SCROLLS):
                if await self._opens_grid(tab, category_opener):
                    return "category"
                await NodriverDom.evaluate(tab, _SCROLL_PLACE_PANEL_JS, by_value=True)
                await asyncio.sleep(0.5)
            announced_photos = await NodriverDom.evaluate(tab, _PHOTO_COUNT_JS, by_value=True)
            is_count_shown = isinstance(announced_photos, int)
            if is_count_shown and announced_photos <= _PLAIN_LAYOUT_PHOTO_CAP:
                break
            if not is_count_shown and redraws_without_count_left == 0:
                break
            if redraws_left == 0 or not place_url:
                break
            redraws_left -= 1
            if not is_count_shown:
                redraws_without_count_left -= 1
            logger.info("Enrichment: plain photo layout (%s photos announced) — drawing it again", announced_photos)
            if not await self._redraw_layout(tab, place_url):
                break
        for name, script in (("photo count", _OPEN_PHOTO_COUNT_JS), ("hero", _OPEN_PHOTOS_JS)):
            if await self._opens_grid(tab, script):
                return name
            await self._back_to_place_panel(tab, place_url=place_url, place_title=place_title)
        logger.info("Enrichment: no photo grid could be opened on the place panel")
        return None

    async def _redraw_layout(self, tab: Any, place_url: str) -> bool:
        """
        Clear the cookies and reopen the place, so Google draws its panel layout again.

        Args:
            tab: The Maps tab.
            place_url: The place's URL.

        Returns:
            Whether the place panel opened again.
        """
        try:
            import nodriver.cdp as cdp

            await tab.send(cdp.network.clear_browser_cookies())
        except Exception as exc:
            logger.info("Enrichment: cookies could not be cleared (%s)", exc)
            return False
        await NodriverDom.navigate(tab, place_url)
        return await self._open_place_panel(tab)

    async def _back_to_place_panel(self, tab: Any, *, place_url: str | None, place_title: str | None) -> None:
        """Reload the place when a click left its panel (a Street View photo opens Street View, under the same URL)."""
        if not place_url or not place_title:
            return
        if await self._read_place_title(tab) == place_title:
            return
        await NodriverDom.navigate(tab, place_url)
        await self._open_place_panel(tab)

    @staticmethod
    async def _opens_grid(tab: Any, script: str) -> bool:
        """Whether clicking what ``script`` finds brings up the photo grid's tiles."""
        clicked = await NodriverDom.evaluate(tab, script, by_value=True)
        if clicked is not True and not isinstance(clicked, str):
            return False
        return await NodriverDom.wait_for_selector(tab, _GRID_TILE_SELECTOR, timeout_s=6.0)

    async def _read_photo_category(self, tab: Any, labels: tuple[str, ...]) -> list[str] | None:
        """
        Click a category tab of the open gallery and read its grid.

        « Photos du propriétaire » holds the business's own uploads, and the only real photo when « Tout »
        shows nothing but Street View.

        Args:
            tab: The Maps tab, on the open gallery.
            labels: The category's names, lowercase, in the languages Maps may show.

        Returns:
            The category's photo URLs, or ``None`` when the gallery shows no such category.
        """
        clicked = await NodriverDom.evaluate(tab, _OPEN_PHOTO_CATEGORY_JS % json.dumps(list(labels)), by_value=True)
        if not isinstance(clicked, str) or not await NodriverDom.wait_for_selector(
            tab, _GRID_TILE_SELECTOR, timeout_s=6.0
        ):
            return None
        # A tab switch swaps the tiles in place: let the previous category's tiles go before reading.
        await asyncio.sleep(1.0)
        return await self._read_open_grid(tab)

    async def _read_open_grid(self, tab: Any) -> list[str]:
        """Read the open grid, step-scrolling its virtualised container until no new tile shows up."""
        collected: list[str] = []
        stable_rounds = 0
        for _ in range(28):
            fresh = [url for url in await self._read_grid_photos(tab) if url not in collected]
            collected.extend(fresh)
            stable_rounds = 0 if fresh else stable_rounds + 1
            if stable_rounds >= 3 or len(collected) >= 40:
                break
            await NodriverDom.evaluate(tab, _GRID_SCROLL_JS, by_value=True)
            await asyncio.sleep(0.5)
        return collected

    async def _grab_more_photos(
        self, tab: Any, data: EnrichmentData, *, place_url: str | None = None, place_title: str | None = None
    ) -> None:
        """Fallback grid read (post-extraction, re-anchored panel): merge the grid into ``data.photos``.

        Isolated + best-effort: only ADDS photos, so a failure never touches what we already have.
        """
        try:
            collected = await self._collect_open_grid(
                tab, seed=data.photos, place_url=place_url, place_title=place_title
            )
            if collected is not None:
                data.photos = collected
        except Exception as exc:
            logger.info("Extra Google photo pass failed: %s", exc)

    async def _read_photo_grid_then_close(
        self, tab: Any, *, place_url: str | None = None, place_title: str | None = None
    ) -> list[str]:
        """Read the photo grid on the STILL-FRESH panel (before extraction hides the button), then close
        the gallery so extraction reads the place panel again.

        Reading here avoids the ~3s re-anchor page reload the post-extraction path needs to bring the
        « Voir les photos » button back. Best-effort close: if it doesn't restore the panel, the caller's
        completeness check re-anchors — never worse than the old order, which reloaded then read the grid.
        Returns ``[]`` when the grid never opened, so the caller falls back to the proven path.
        """
        try:
            collected = await self._collect_open_grid(tab, place_url=place_url, place_title=place_title)
        except Exception as exc:
            logger.info("Fresh-panel photo grid read failed: %s", exc)
            return []
        if not collected:
            return []
        try:
            await NodriverDom.evaluate(tab, _CLOSE_GALLERY_JS, by_value=True)
            await asyncio.sleep(0.4)
        except Exception:
            pass
        return collected

    async def _read_grid_photos(self, tab: Any) -> list[str]:
        """Read the currently-loaded tiles from the open photo grid (videos excluded)."""
        raw = await NodriverDom.evaluate(tab, f"JSON.stringify({_GRID_PHOTOS_JS})", by_value=True)
        if not isinstance(raw, str):
            return []
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if not isinstance(parsed, list):
            return []
        return [p for p in parsed if isinstance(p, str) and p.strip()]

    async def _extract_raw(self, tab: Any) -> dict[str, Any]:
        """Run the in-page extraction script once."""
        raw = await NodriverDom.evaluate(tab, f"JSON.stringify({_EXTRACT_JS})", by_value=True)
        if not isinstance(raw, str):
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    @staticmethod
    def _is_extraction_ready(data: EnrichmentData) -> bool:
        """True when wave-2 data looks complete enough to stop retrying.

        Weekly hours are the reliable signal; the review count is optional (new places and food
        trucks often have none), so we don't burn extra attempts waiting for a count that never comes.
        """
        return len(data.opening_hours) >= _ENRICHMENT_MIN_HOUR_ROWS

    @staticmethod
    def _merge_attempt_data(current: EnrichmentData, incoming: EnrichmentData) -> EnrichmentData:
        """Keep the richest fields seen across extraction attempts."""
        merged_reviews: list[dict[str, Any]] = _dedupe_reviews([*current.reviews, *incoming.reviews])

        merged_photos: list[str] = [url for url in current.photos if url]
        seen_photos: set[str] = set(merged_photos)
        for url in incoming.photos:
            if url and url not in seen_photos:
                merged_photos.append(url)
                seen_photos.add(url)

        merged_hours: list[dict[str, str]] = current.opening_hours
        if len(incoming.opening_hours) > len(merged_hours):
            merged_hours = incoming.opening_hours

        return EnrichmentData(
            source=incoming.source or current.source,
            logo_url=incoming.logo_url or current.logo_url,
            rating=incoming.rating if incoming.rating is not None else current.rating,
            reviews_count=incoming.reviews_count if incoming.reviews_count is not None else current.reviews_count,
            description=incoming.description or current.description,
            website=incoming.website or current.website,
            photos=merged_photos[:20],
            reviews=merged_reviews[:12],
            opening_hours=merged_hours,
            services=incoming.services or current.services,
            social_links={**(current.social_links or {}), **(incoming.social_links or {})},
            place_title=incoming.place_title or current.place_title,
            place_city=incoming.place_city or current.place_city,
            place_postal_code=incoming.place_postal_code or current.place_postal_code,
        )

    async def _extract_with_retries(
        self,
        tab: Any,
        *,
        business_name: str,
        city: str | None,
    ) -> EnrichmentData:
        """Poll extraction until wave-2 hydration is complete or attempts are exhausted."""
        # First pass on the CLEAN panel, BEFORE any hours expansion: captures the hero photos, rating
        # and reviews a destructive hours expansion drops (some food-truck listings open a full
        # « Horaires » view that replaces the panel). Later passes expand the hours and merge them in.
        best: EnrichmentData = self._build_from_raw(
            await self._extract_raw(tab), business_name=business_name, city=city
        )
        previous_hours: int = -1
        for attempt in range(_ENRICHMENT_MAX_ATTEMPTS):
            await self._prepare_panel_for_extraction(tab)
            raw = await self._extract_raw(tab)
            candidate = self._build_from_raw(raw, business_name=business_name, city=city)
            best = self._merge_attempt_data(best, candidate)
            if self._is_extraction_ready(best):
                logger.info("Enrichment ready for %s after %s attempt(s)", business_name, attempt + 1)
                return best
            # Plateau exit: the merged hour count stopped growing between attempts (best only ever
            # grows), so further attempts add nothing — a food truck open a few days, OR a panel the
            # sign-in modal collapsed so nothing parses (rating None, hours 0). No rating requirement:
            # the collapsed-panel case is exactly the one that has none, and it caused the ~20s stall.
            # A genuinely still-loading panel keeps growing, so it is never cut here.
            hours: int = len(best.opening_hours)
            if attempt > 0 and hours == previous_hours:
                logger.info("Enrichment plateaued for %s after %s attempt(s)", business_name, attempt + 1)
                return best
            previous_hours = hours
            if attempt + 1 < _ENRICHMENT_MAX_ATTEMPTS:
                logger.info(
                    "Enrichment incomplete for %s (attempt %s/%s) — retrying",
                    business_name,
                    attempt + 1,
                    _ENRICHMENT_MAX_ATTEMPTS,
                )
                await asyncio.sleep(_ENRICHMENT_POLL_INTERVAL_S)
        logger.info(
            "Enrichment for %s finished with partial data after %s attempts",
            business_name,
            _ENRICHMENT_MAX_ATTEMPTS,
        )
        return best

    @staticmethod
    def _build_from_raw(
        data: dict[str, Any],
        *,
        business_name: str | None = None,
        city: str | None = None,
    ) -> EnrichmentData:
        """Coerce the raw JS payload into a typed EnrichmentData.

        DOM selectors first, then JSON-LD (schema.org) as a stable fallback for
        description / rating / reviews_count when the obfuscated classes miss.
        ``business_name`` / ``city`` gate the meta-description fallback: it is the
        PAGE's meta, trustworthy only when it actually names the business.
        """
        if not isinstance(data, dict):
            return EnrichmentData()

        def _as_float(value: Any) -> float | None:
            try:
                return float(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        def _as_int(value: Any) -> int | None:
            try:
                return int(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        photos = [str(p) for p in data.get("photos", []) if isinstance(p, str)]
        reviews = [r for r in data.get("reviews", []) if isinstance(r, dict)]
        hours = [h for h in data.get("opening_hours", []) if isinstance(h, dict)]
        social = {str(k): str(v) for k, v in (data.get("social") or {}).items() if isinstance(v, str) and v.strip()}
        website = (str(data["website"]).strip() if data.get("website") else None) or None

        # JSON-LD fallback (Google Maps place pages sometimes ship schema.org data).
        business = parse_ld_json_blocks(data.get("ld"))

        rating = _as_float(data.get("rating"))
        if rating is None and business:
            rating = _as_float(business.get("rating"))

        reviews_count = _as_int(data.get("reviews_count"))
        if reviews_count is None and business:
            reviews_count = _as_int(business.get("reviews_count"))

        dom_description = (str(data["description"]).strip() if data.get("description") else None) or None
        # The DOM value is the page's meta description: on a place deep link it names
        # the business, on a search/consent page it's Google's own boilerplate.
        if dom_description and (
            validation_service.is_generic_platform_description(dom_description)
            or not validation_service.description_mentions_business(dom_description, business_name, city)
        ):
            logger.info("Enrichment: dropping irrelevant meta description %r", dom_description[:80])
            dom_description = None

        description = dom_description
        if business and business.get("description"):
            # Prefer a JSON-LD description over the meta description fallback.
            ld_description = str(business["description"]).strip()
            if ld_description and not validation_service.is_generic_platform_description(ld_description):
                description = ld_description

        place_title = _clean_place_title(str(data["place_title"]) if data.get("place_title") else None)
        if place_title is None and business and business.get("name"):
            place_title = str(business["name"]).strip() or None

        return EnrichmentData(
            source="google",
            rating=rating,
            reviews_count=reviews_count,
            description=description,
            website=website,
            photos=photos,
            reviews=reviews,
            opening_hours=hours,
            social_links=social,
            place_title=place_title,
            place_city=(str(business["city"]).strip() or None) if business and business.get("city") else None,
            place_postal_code=(
                (str(business["postal_code"]).strip() or None) if business and business.get("postal_code") else None
            ),
        )


enrichment_scraper = EnrichmentScraper()
