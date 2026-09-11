"""
Facebook page enrichment scraper.

Fallback for prospects that have NO Google listing but an active public Facebook
page — common among artisans who only ever set up a Facebook presence. It produces
the same ``EnrichmentData`` the Google scraper returns, so the rest of the pipeline
(``EnrichmentService._apply_data``, site-content mapping) is untouched.

Two Facebook specifics drive the design:

- **No stable CSS classes.** Facebook hashes and rotates every class name, so
  extraction is anchored on **stable French captions** ("Mobile", "Recommandé par
  X %", "… recommande …", "Intro") and on ``a[href]`` / ``img[src]`` — never on
  class names.
- **Reviews are binary.** Facebook shows "recommends / doesn't recommend" plus a
  "Recommandé par X %" rate, not 1-5 stars. The rate is converted to a /5 rating so
  the data lines up with what Google yields (kept homogeneous on purpose).

Like the Google scraper it runs on the user's desktop (nodriver, residential IP) —
Facebook blocks datacenter IPs too. Everything is best-effort: a partial read still
returns whatever could be gathered. The text-parsing helpers are pure functions so
they can be unit-tested without a browser.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
from typing import Any
from urllib.parse import parse_qs, parse_qsl, unquote, urlencode, urlparse, urlunparse

import httpx

from scrappers.enrichment_scraper import EnrichmentData, _dedupe_reviews
from scrappers.nodriver_browser import NODRIVER_AVAILABLE, NodriverBrowser
from scrappers.nodriver_dom import NodriverDom
from scrappers.nodriver_executor import run_nodriver_task
from services.decision_maker.normalize import company_tokens, fold

logger = logging.getLogger(__name__)

# Cap aligned with the Google enrichment merge (photos 40 / reviews 12). More photos than we show:
# Google's come first, Facebook's are appended as a secondary pool, and the user picks the best.
_MAX_PHOTOS = 40
_MAX_REVIEWS = 12
# How many fbcdn photos to capture as base64 data URIs (they outlive the short-lived signed URLs).
# A site needs ~8 (hero, about, menu, collage, testimonial); 12 leaves margin without bloating the POST.
_FB_REHOST_CAP = 12
# Skip a photo heavier than this (bytes) — a full-size gallery JPEG is well under it.
_FB_PHOTO_MAX_BYTES = 3_500_000
# Concurrent photo downloads: quick capture without hammering fbcdn.
_FB_DOWNLOAD_CONCURRENCY = 4
# Browser-like headers so fbcdn serves our client the same signed URL it served the <img> tag.
_FB_DOWNLOAD_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://www.facebook.com/",
}

# `\s` matches the thin/no-break spaces Facebook puts before « % », so « 96 % » / « 22 avis » parse verbatim.
_RECOMMEND_RE = re.compile(r"recommand[ée]?s?\s+par\s*(\d+)\s*%", re.IGNORECASE)
_REVIEWS_COUNT_RE = re.compile(r"\((\d[\d\s.,]*)\s*avis\)", re.IGNORECASE)
# Header line of a review block: "<Author> recommande <page>." / "… ne recommande pas …".
_REVIEW_HEADER_RE = re.compile(r"^(.+?)\s+(?:ne\s+)?recommande\b", re.IGNORECASE)
# A French date line ("27 septembre 2025") that sits between the header and the body.
_DATE_RE = re.compile(r"^\d{1,2}\s+\S+\s+\d{4}$")
_REVIEW_STOP_MARKERS: tuple[str, ...] = (
    "toutes les réactions",
    "toutes les reactions",
    "j'aime",
    "j’aime",
    "commenter",
    "partager",
    "répondre",
    "repondre",
)
# Lines that end the Intro blurb on the public page (contact / category / socials).
_INTRO_STOP_MARKERS: tuple[str, ...] = (
    "page ·",
    "recommandé par",
    "recommande par",
    "mobile",
    "whatsapp",
    "e-mail",
    "email",
    "adresse",
    "followers",
    "suivi(e)s",
    "sièges en terrasse",
    "photos",
)
_SOCIAL_HOST_RE = re.compile(
    r"(?:instagram|tiktok|facebook|youtube|linkedin|twitter|x)\.com",
    re.IGNORECASE,
)
_PHONE_LINE_RE = re.compile(r"^\+?\d[\d\s./()-]{6,}$")
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Domains/extensions that are never a business contact email (CDN assets, tracking, Facebook itself).
_EMAIL_NOISE: tuple[str, ...] = ("facebook.com", "fbcdn", "sentry", "example.com", ".png", ".jpg", ".gif", ".svg")


def _extract_emails(*texts: str) -> list[str]:
    """Find contact emails in the Facebook page's own text (intro / about / embedded), deduped.

    A business page usually lists a contact email (e.g. ``contact@…``) that Google Maps does not expose;
    this is the whole point of the complementary Facebook read. CDN/tracking noise is filtered out.
    """
    found: list[str] = []
    seen: set[str] = set()
    for blob in texts:
        for match in _EMAIL_RE.findall(blob or ""):
            email = match.strip().rstrip(".").lower()
            if any(noise in email for noise in _EMAIL_NOISE):
                continue
            if email in seen:
                continue
            seen.add(email)
            found.append(email)
    return found


_TRACKING_QUERY_KEYS = frozenset(
    {
        "igsh",
        "igshid",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_content",
        "utm_term",
        "_r",
        "_t",
        "fbclid",
    }
)

# Soft-dismiss only: clicking Fermer. Removing dialog nodes breaks React hydration
# and Facebook then never paints the rest of the reviews list.
_DISMISS_LOGIN_JS = r"""
(() => {
    let closed = false;
    for (const el of document.querySelectorAll('[aria-label="Fermer"], [aria-label="Close"]')) {
        try { el.click(); closed = true; break; } catch (e) {}
    }
    // Decline the Facebook cookie banner (privacy-preserving) — it otherwise covers the photos grid
    // and blocks the read. Match its exact button text so we never click « Autoriser tous ».
    for (const el of document.querySelectorAll('[role="button"], button')) {
        const label = ((el.getAttribute('aria-label') || '') + ' ' + (el.textContent || '')).trim().toLowerCase();
        if (label.includes('refuser les cookies optionnel') || label.includes('decline optional cookies') ||
            label.includes('only allow essential cookies')) {
            try { el.click(); closed = true; break; } catch (e) {}
        }
    }
    try {
        document.body.style.overflow = 'visible';
        document.documentElement.style.overflow = 'visible';
    } catch (e) {}
    return closed;
})()
"""

# Expand truncated Intro / about blurbs when Facebook collapses them behind « En voir plus ».
_EXPAND_SEE_MORE_JS = r"""
(() => {
    let clicked = 0;
    for (const el of document.querySelectorAll('div[role="button"], span')) {
        const label = ((el.innerText || el.textContent || '') + ' ' + (el.getAttribute('aria-label') || '')).trim().toLowerCase();
        if (!/^(en )?voir plus|see more|voir la suite$/.test(label) && !label.includes('en voir plus')) continue;
        try { el.click(); clicked += 1; } catch (e) {}
        if (clicked >= 4) break;
    }
    return clicked;
})()
"""

# Public page home: title, Intro blurb, og:description + embedded bio, socials.
# Photos come from /photos_by + /photos_of — the home feed mixes posts and UI.
_FB_PAGE_JS = r"""
(() => {
    const out = {
        place_title: null, intro_text: '', about_text: '', og_description: null,
        embedded_texts: [], social: {}, website: null, profile_photo: null, emails: []
    };
    const txt = (el) => (el ? (el.innerText || el.textContent || '').trim() : '');
    try { out.place_title = txt(document.querySelector('h1')) || null; } catch (e) {}
    try {
        const main = document.querySelector('div[role="main"]');
        out.about_text = (main ? main.innerText : (document.body ? document.body.innerText : '')) || '';
    } catch (e) { out.about_text = ''; }
    try {
        const og = document.querySelector('meta[property="og:description"], meta[name="description"]');
        out.og_description = og ? ((og.getAttribute('content') || '').trim() || null) : null;
    } catch (e) {}
    try {
        let intro = '';
        for (const heading of document.querySelectorAll('h2')) {
            if (!/^intro$/i.test(txt(heading))) continue;
            let root = heading.parentElement;
            for (let depth = 0; depth < 12 && root; depth += 1) {
                const block = txt(root);
                if (block.length > 40 && /^intro\b/i.test(block)) {
                    intro = block;
                    break;
                }
                root = root.parentElement;
            }
            if (intro) break;
        }
        out.intro_text = intro;
    } catch (e) { out.intro_text = ''; }
    // Full page bio often lives in Relay JSON even when the Intro card / og:description
    // are truncated behind the login wall or cut with « … ».
    try {
        const html = document.documentElement ? (document.documentElement.innerHTML || '') : '';
        const re = /"text":"((?:\\.|[^"\\])*)"/g;
        const seen = new Set();
        let match;
        while ((match = re.exec(html))) {
            let decoded = '';
            try { decoded = JSON.parse('"' + match[1] + '"'); } catch (e) { continue; }
            decoded = (decoded || '').trim();
            if (!decoded || seen.has(decoded)) continue;
            seen.add(decoded);
            out.embedded_texts.push(decoded);
            if (out.embedded_texts.length >= 80) break;
        }
    } catch (e) {}
    const unwrap = (href) => {
        const m = (href || '').match(/[?&]u=([^&]+)/);
        if (m) { try { return decodeURIComponent(m[1]); } catch (e) {} }
        return href || '';
    };
    const isSocial = (low) => ['facebook.com', 'instagram.com', 'tiktok.com', 'youtube.com',
        'linkedin.com', 'twitter.com', 'x.com', 'l.php', 'l.facebook'].some((needle) => low.includes(needle));
    // A media asset (a poster/logo/photo from a post — e.g. a cloudinary .png) is NOT a website.
    const isAsset = (low) => /\.(png|jpe?g|gif|webp|svg|avif|bmp|ico|mp4|pdf)(\?|#|$)/.test(low) ||
        ['cloudinary.com', 'fbcdn', 'cdninstagram', 'googleusercontent', 'lookaside'].some((h) => low.includes(h));
    try {
        const nets = { facebook: 'facebook.com/', instagram: 'instagram.com/',
            tiktok: 'tiktok.com/', youtube: 'youtube.com/', linkedin: 'linkedin.com/' };
        for (const a of document.querySelectorAll('a[href]')) {
            const href = unwrap(a.getAttribute('href'));
            const low = href.toLowerCase();
            for (const [net, needle] of Object.entries(nets)) {
                if (!out.social[net] && low.includes(needle)) out.social[net] = href;
            }
            if (!out.website && /^https?:\/\//i.test(href) && !isSocial(low) && !isAsset(low)) out.website = href;
        }
    } catch (e) {}
    // Profile photo (logo candidate). Facebook renders it as an <svg role="img"><image xlink:href>
    // with a circular mask, and its URL lives on the `t39.30808-1` CDN path (posts use `-6`). Accept
    // it when the URL is on that profile path OR when the element's alt/aria-label names the page — so
    // a cover photo or a post is never mistaken for the logo (no match → no logo → template fallback).
    try {
        const title = (out.place_title || '').toLowerCase().slice(0, 14);
        for (const el of document.querySelectorAll('image, img')) {
            const src = el.getAttribute('xlink:href') || el.getAttribute('href') || el.getAttribute('src') || '';
            if (!/scontent/i.test(src)) continue;
            const holder = el.closest('[aria-label]');
            const label = ((el.getAttribute('alt') || '') + ' ' + (holder ? holder.getAttribute('aria-label') || '' : '')).toLowerCase();
            const isProfilePath = /\/t39\.30808-1\//.test(src);
            const namesPage = title && label.includes(title);
            if (isProfilePath || namesPage) { out.profile_photo = src; break; }
        }
    } catch (e) {}
    // The contact email often renders in a « Coordonnées » row (icon + <span>) OUTSIDE div[role="main"],
    // so about_text (main only) misses it — harvest it from the whole page below. Order by confidence:
    // mailto and visible text first (one becomes the prospect's send address), the JSON contact keys last.
    try {
        const seenEmail = new Set();
        const pushEmail = (raw) => {
            const email = (raw || '').trim().replace(/[.,;>)\]]+$/, '').toLowerCase();
            if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email) || seenEmail.has(email)) return;
            seenEmail.add(email);
            out.emails.push(email);
        };
        for (const a of document.querySelectorAll('a[href^="mailto:"], a[href^="MAILTO:"]')) {
            pushEmail((a.getAttribute('href') || '').slice(7).split('?')[0]);
        }
        const bodyText = document.body ? (document.body.innerText || '') : '';
        const textRe = /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g;
        let textMatch;
        while ((textMatch = textRe.exec(bodyText))) pushEmail(textMatch[0]);
        const html = document.documentElement ? (document.documentElement.innerHTML || '') : '';
        const jsonRe = /"(?:email|email_address|contact_email|public_email)"\s*:\s*"([^"]+@[^"]+?)"/gi;
        let jsonMatch;
        while ((jsonMatch = jsonRe.exec(html))) {
            let decoded = jsonMatch[1];
            try { decoded = JSON.parse('"' + jsonMatch[1] + '"'); } catch (e) {}
            pushEmail(decoded);
        }
    } catch (e) {}
    return out;
})()
"""

# Photos galleries: keep ``scontent`` only (real media). ``static.xx.fbcdn`` / ``rsrc.php``
# are UI icons (phone, star, house…) that previously polluted the enrichment.
_FB_PHOTOS_JS = r"""
(() => {
    const out = { photos: [] };
    const minPx = 100;
    const seen = new Set();
    const push = (src) => {
        if (!src || seen.has(src)) return;
        seen.add(src);
        out.photos.push(src);
    };
    try {
        for (const img of document.querySelectorAll('img')) {
            const src = img.getAttribute('src') || '';
            if (!/scontent/i.test(src)) continue;
            if (/emoji\.php|rsrc\.php|static\.xx\.fbcdn/i.test(src)) continue;
            const width = img.naturalWidth || img.width || 0;
            const height = img.naturalHeight || img.height || 0;
            if (width > 0 && height > 0 && (width < minPx || height < minPx)) continue;
            push(src);
            if (out.photos.length >= 30) break;
        }
    } catch (e) {}
    return out;
})()
"""

# Reviews tab: visible text is often truncated to 1 review behind the login wall.
# The full recommendations still live in the Relay JSON embedded in the HTML —
# extract those `"text"` payloads so we do not depend on lazy DOM hydration.
_FB_REVIEWS_JS = r"""
(() => {
    const out = { reviews_text: '', embedded_texts: [] };
    const main = document.querySelector('div[role="main"]');
    out.reviews_text = (main ? main.innerText : (document.body ? document.body.innerText : '')) || '';
    try {
        const html = document.documentElement ? (document.documentElement.innerHTML || '') : '';
        const re = /"text":"((?:\\.|[^"\\])*)"/g;
        const seen = new Set();
        let match;
        while ((match = re.exec(html))) {
            let decoded = '';
            try { decoded = JSON.parse('"' + match[1] + '"'); } catch (e) { continue; }
            decoded = (decoded || '').trim();
            if (!decoded || seen.has(decoded)) continue;
            seen.add(decoded);
            out.embedded_texts.push(decoded);
            if (out.embedded_texts.length >= 100) break;
        }
    } catch (e) {}
    return out;
})()
"""

_SCROLL_REVIEWS_JS = r"""
(() => {
    const main = document.querySelector('div[role="main"]');
    if (main && typeof main.scrollBy === 'function') {
        main.scrollBy(0, 1400);
    }
    window.scrollBy(0, 1400);
    return true;
})()
"""

# Chrome strings that appear as `"text"` payloads but are not review bodies.
_REVIEW_CHROME_RE = re.compile(
    r"^(recommand[ée]?s?\s+par\b|toutes les réactions|j['’]aime|commenter|partager|"
    r"publications|à propos|reels|photos|followers|suivi|"
    r"les commentaires ont [ée]t[ée] d[ée]sactiv[ée]s|comments are turned off)",
    re.IGNORECASE,
)
# Page-bio candidates from Relay JSON (avoid review headers / UI chrome).
_BIO_NOISE_RE = re.compile(
    r"recommande\b|j['’]aime|followers|publication|commentaire|commenter|partager|"
    r"toutes les réactions|en voir plus|see more",
    re.IGNORECASE,
)
_OG_LIKES_PREFIX_RE = re.compile(
    r"^[^.]*\.\s*\d[\d\s ]*j['’]aime\s*·\s*\d[\d\s ]*en parlent\.\s*",
    re.IGNORECASE,
)


def _rating_from_pct(pct: int | None) -> float | None:
    """Convert a Facebook "recommended by X %" rate into a /5 rating (96 % → 4.8).

    Args:
        pct: Recommendation percentage (0-100), or None.

    Returns:
        The rating rounded to one decimal and clamped to [0, 5], or None.
    """
    if pct is None:
        return None
    return round(max(0.0, min(100.0, float(pct))) / 20.0, 1)


def _parse_about_stats(text: str) -> tuple[int | None, int | None]:
    """Extract the recommendation rate and review count from a Facebook panel text.

    Args:
        text: Visible text of the « À propos » / « Avis » panel.

    Returns:
        A ``(rating_pct, reviews_count)`` pair, each None when absent.
    """
    rating_match = _RECOMMEND_RE.search(text)
    count_match = _REVIEWS_COUNT_RE.search(text)
    rating_pct = int(rating_match.group(1)) if rating_match else None
    reviews_count = int(re.sub(r"\D", "", count_match.group(1))) if count_match else None
    return rating_pct, reviews_count


def _parse_intro_description(intro_text: str) -> str | None:
    """Pull the business Intro blurb out of the public page's Intro card text.

    Args:
        intro_text: Visible text of the Intro card (or empty).

    Returns:
        The cleaned multi-sentence description, or None when absent.
    """
    if not (intro_text or "").strip():
        return None
    lines: list[str] = [line.strip() for line in intro_text.splitlines() if line.strip()]
    start = next((index for index, line in enumerate(lines) if line.lower() == "intro"), None)
    if start is None:
        return None
    body: list[str] = []
    for line in lines[start + 1 :]:
        lowered = line.lower()
        if any(marker in lowered for marker in _INTRO_STOP_MARKERS):
            break
        if _SOCIAL_HOST_RE.search(line) or _PHONE_LINE_RE.match(line) or "@" in line:
            break
        if re.match(r"^page\s*·", lowered):
            break
        body.append(line)
    description = " ".join(body).strip()
    return description or None


def _parse_og_description(og_description: str | None) -> str | None:
    """Clean Facebook's og:description into a usable business blurb.

    Args:
        og_description: Raw Open Graph description, or None.

    Returns:
        A cleaned description without the « X J'aime · Y en parlent » prefix,
        or None when empty / too short.
    """
    if not (og_description or "").strip():
        return None
    text = _OG_LIKES_PREFIX_RE.sub("", og_description.strip()).strip()
    # Weak pages give « {name}. {X} J'aime. {category} » with no « en parlent » — strip that shape too,
    # so what's left is real copy (or nothing). Spaces cover the French thin/no-break number separators.
    text = re.sub(r"^[^.]*\.\s*\d[\d\s  ]*j['’]aime\.\s*", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\s*\.\.\.\s*$", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text if len(text) >= 40 else None


def _is_review_chrome(text: str) -> bool:
    """True for UI / stats strings that are not a review body."""
    first = text.splitlines()[0].strip() if text else ""
    if not first:
        return True
    if _REVIEW_CHROME_RE.match(first):
        return True
    if _DATE_RE.match(first):
        return True
    return bool(first.replace(" ", "").isdigit())


def _clean_social_url(url: str) -> str:
    """Normalise a social profile URL: unwrap FB login/redirect wrappers, drop tracking.

    Facebook sometimes exposes a link behind a redirect wrapper — ``l.facebook.com/
    l.php?u=…`` or ``/login/?next=…`` — whose real destination lives in the ``u`` /
    ``next`` query param. A bare login wrapper with no recoverable target is not a
    usable profile and is dropped (the caller then omits that network).

    Args:
        url: Raw social URL found in the page's anchors.

    Returns:
        A clean profile URL, or ``""`` when only an unusable login redirect was found.
    """
    candidate = url.strip()
    parsed = urlparse(candidate)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    if host.endswith("facebook.com") and (
        path.endswith("l.php") or path.startswith("/login") or path.startswith("/flx")
    ):
        params = parse_qs(parsed.query)
        target = (params.get("u") or params.get("next") or [""])[0]
        target = unquote(target) if target else ""
        if not target.lower().startswith("http"):
            return ""  # login wrapper without a destination — not a profile
        candidate = target
        parsed = urlparse(candidate)

    if not parsed.scheme or not parsed.netloc:
        return candidate
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in _TRACKING_QUERY_KEYS
    ]
    return urlunparse(parsed._replace(query=urlencode(query), fragment=""))


def _website_belongs_to_business(website: str, place_title: str | None) -> bool:
    """Whether *website*'s domain plausibly belongs to the business (not a third-party link).

    Facebook pages often carry a partner / supplier link in a post or the description
    (a food truck citing ``agriethique.fr``, for instance), which the DOM scan can pick
    up as the "website". We keep a website only when its registrable label shares a
    significant token with the business name; when the name is unknown we cannot judge,
    so we keep it. Trade-off: a real site whose domain shares no word with the name is
    dropped — acceptable, since a wrong embedded site is worse than a missing one and
    this path targets businesses that usually have no site at all.

    Args:
        website: Candidate website URL scraped from the page.
        place_title: The business name, when known.

    Returns:
        ``True`` to keep the website, ``False`` to treat the prospect as site-less.
    """
    if not place_title:
        return True
    host = urlparse(website if "://" in website else f"http://{website}").netloc.lower().split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    domain_label = fold(host.split(".")[0]) if host else ""
    tokens = {tok for tok in company_tokens(place_title) if len(tok) >= 4}
    if not domain_label or not tokens:
        return True
    return any(tok in domain_label or domain_label in tok for tok in tokens)


# FB "Coordonnées" writes « City, France, 75011 »; a street address writes « 75011 Paris » — read both orders.
_CITY_FRANCE_POSTAL_RE: re.Pattern[str] = re.compile(
    r"([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’.\- ]{1,58}?),\s*France,?\s*(\d{5})\b", re.IGNORECASE
)
_POSTAL_CITY_RE: re.Pattern[str] = re.compile(r"\b(\d{5})\b[ ,]+([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ'’.\- ]{1,58})")

# Facebook caption / UI words a naive match could mistake for a city.
_NON_CITY_WORDS: frozenset[str] = frozenset(
    {
        "adresse",
        "coordonnees",
        "mobile",
        "whatsapp",
        "email",
        "e-mail",
        "telephone",
        "france",
        "site",
        "web",
        "fourchette",
        "prix",
        "avis",
        "page",
        "intro",
        "about",
        "a propos",
        "horaires",
        "ouvert",
        "ferme",
    }
)


def _clean_city_fragment(raw: str) -> str:
    """Trim a captured city fragment to its first clause (strip country, separators).

    Args:
        raw: The raw city capture.

    Returns:
        The cleaned city string (possibly empty).
    """
    city = re.split(r"[,\n·•|]", raw)[0].strip(" ,.-\t")
    return re.sub(r"\b(France|Frankreich)\b.*$", "", city, flags=re.IGNORECASE).strip(" ,.-")


def _is_plausible_city(city: str) -> bool:
    """Whether *city* looks like a real city name rather than a UI caption or number.

    Args:
        city: A cleaned city candidate.

    Returns:
        ``True`` when it has letters, a sane length and is not a Facebook caption word.
    """
    return bool(1 < len(city) <= 58 and re.search(r"[A-Za-zÀ-ÿ]", city) and fold(city) not in _NON_CITY_WORDS)


# French phone in the « Coordonnées » block — 06 29 34 58 99, 0629345899, +33 6 29 34 58 99…
_FR_PHONE_RE: re.Pattern[str] = re.compile(r"(?<!\d)(?:\+33[\s.\-]?[1-9]|0[1-9])(?:[\s.\-]?\d{2}){4}(?!\d)")


def _parse_phone(*texts: str) -> str | None:
    """Best-effort French phone number from a Facebook page's text.

    Args:
        *texts: Text blocks to scan (intro first, then the about panel).

    Returns:
        The number normalised to ``0X XX XX XX XX``, or ``None`` when absent.
    """
    for text in texts:
        if not text:
            continue
        match = _FR_PHONE_RE.search(text)
        if not match:
            continue
        digits = re.sub(r"\D", "", match.group(0))
        if digits.startswith("33"):
            digits = "0" + digits[2:]
        if len(digits) == 10:
            return " ".join(digits[i : i + 2] for i in range(0, 10, 2))
    return None


def _parse_city_postal(*texts: str) -> tuple[str | None, str | None]:
    """Best-effort French ``(city, postal_code)`` from a Facebook page's text.

    Anchored on the 5-digit postal code — the only address shape reliable enough on a
    Facebook page (a lone city line is too ambiguous). Reads both the "Coordonnées"
    order (``City, France, 75011``) and a street-address order (``75011 Paris``). Scans
    blocks most-specific first and returns the first plausible match.

    Args:
        *texts: Text blocks to scan (intro first, then description, then page body).

    Returns:
        ``(city, postal_code)`` — either element may be ``None``.
    """
    for text in texts:
        if not text:
            continue
        for match in _CITY_FRANCE_POSTAL_RE.finditer(text):
            city = _clean_city_fragment(match.group(1))
            if _is_plausible_city(city):
                return city, match.group(2)
        for match in _POSTAL_CITY_RE.finditer(text):
            city = _clean_city_fragment(match.group(2))
            if _is_plausible_city(city):
                return city, match.group(1)
    return None, None


def _is_review_noise(line: str) -> bool:
    """True for lines that are not part of a review body (date, dot, reaction count)."""
    if line in {"·", "•", "…"}:
        return True
    if _DATE_RE.match(line):
        return True
    return line.replace(" ", "").isdigit()


def _is_review_stop(line: str) -> bool:
    """True when a line marks the end of a review body (reactions / action bar)."""
    lowered = line.lower()
    return any(marker in lowered for marker in _REVIEW_STOP_MARKERS)


def _parse_reviews(text: str) -> list[dict[str, Any]]:
    """Parse the reviews-tab text into ``{author, text, rating}`` rows.

    Each Facebook review reads "<Author> recommande <page>." then a date then the
    body, up to the "Toutes les réactions" marker. A recommendation maps to 5/5, a
    "ne recommande pas" to 2/5 (Facebook has no finer grain).

    Args:
        text: Visible text of the « Avis » panel.

    Returns:
        Up to 12 parsed reviews, in page order.
    """
    lines: list[str] = [line.strip() for line in text.splitlines() if line.strip()]
    reviews: list[dict[str, Any]] = []
    index = 0
    while index < len(lines) and len(reviews) < _MAX_REVIEWS:
        header = _REVIEW_HEADER_RE.match(lines[index])
        if header is None:
            index += 1
            continue
        author: str = header.group(1).strip()
        recommends: bool = "ne recommande pas" not in lines[index].lower()
        body: list[str] = []
        cursor = index + 1
        while cursor < len(lines):
            line = lines[cursor]
            if _REVIEW_HEADER_RE.match(line) or _is_review_stop(line):
                break
            if not _is_review_noise(line):
                body.append(line)
            cursor += 1
        review_text: str = " ".join(body).strip()
        if author and review_text:
            reviews.append({"author": author, "text": review_text, "rating": 5 if recommends else 2})
        index = cursor if cursor > index else index + 1
    return reviews


def _parse_reviews_from_embedded_texts(texts: list[str]) -> list[dict[str, Any]]:
    """Build reviews from Relay ``text`` payloads embedded in the page HTML.

    The login wall often paints a single review in the DOM while the full list
    still sits in the prefetched JSON. Headers look like
    ``\"Fox Emmanuel  recommande …\"``; bodies are the neighbouring long texts.
    Relay often emits the body *before* the header — prefer that order, and
    never reuse the same body for two authors.

    Args:
        texts: Decoded ``text`` payloads, in document order.

    Returns:
        Up to ``_MAX_REVIEWS`` review rows.
    """
    headers: list[tuple[int, str, bool]] = []
    bodies: list[tuple[int, str]] = []
    for index, text in enumerate(texts):
        first_line = text.splitlines()[0].strip()
        header = _REVIEW_HEADER_RE.match(first_line)
        if header is not None:
            author = header.group(1).strip()
            recommends = "ne recommande pas" not in first_line.lower()
            if author:
                headers.append((index, author, recommends))
            continue
        if _is_review_chrome(text) or len(text) < 20:
            continue
        bodies.append((index, " ".join(part.strip() for part in text.splitlines() if part.strip())))

    reviews: list[dict[str, Any]] = []
    seen_authors: set[str] = set()
    used_body_indexes: set[int] = set()
    for header_index, author, recommends in headers:
        author_key = author.lower()
        if author_key in seen_authors:
            continue
        best_body: str | None = None
        best_body_index: int | None = None
        best_score: int | None = None
        for body_index, body in bodies:
            if body_index in used_body_indexes:
                continue
            delta = body_index - header_index
            # Prefer body immediately before the header (common Relay order),
            # then body right after (DOM-like order).
            if -4 <= delta < 0:
                score = abs(delta)
            elif 0 < delta <= 8:
                score = 10 + delta
            else:
                continue
            if best_score is None or score < best_score:
                best_score = score
                best_body = body
                best_body_index = body_index
        if not best_body or best_body_index is None:
            continue
        used_body_indexes.add(best_body_index)
        seen_authors.add(author_key)
        reviews.append({"author": author, "text": best_body, "rating": 5 if recommends else 2})
        if len(reviews) >= _MAX_REVIEWS:
            break
    return reviews


def _merge_review_lists(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Union review rows by named author, preserving first-seen order (Relay before DOM)."""
    concatenated: list[dict[str, Any]] = []
    for group in groups:
        concatenated.extend(group)
    return _dedupe_reviews(concatenated)[:_MAX_REVIEWS]


def _upgrade_fb_photo_url(url: str) -> str:
    """Upgrade an fbcdn grid thumbnail URL to full size, keeping the signature valid.

    Grid photos are squares whose display size lives in the ``ctp`` param (``s206x206``…). Dropping it
    serves the full size (bounded by ``cstp``, e.g. 1440²) and the ``oh`` signature still validates —
    verified against a live listing (``ctp=s206x206`` → 206², dropped → 1440²). Non-fbcdn URLs and URLs
    without ``ctp`` are returned unchanged.
    """
    if "fbcdn" not in url and "scontent" not in url:
        return url
    return re.sub(r"&ctp=[^&]*", "", url)


def photo_identity(url: str) -> str:
    """A stable identity so the SAME photo served at different sizes / CDN nodes / query strings
    dedupes to one entry. Facebook fbcdn URLs embed a numeric photo id at the start of the filename
    (``…/t39.30808-6/{id}_{hash}_n.jpg``) — keep that; otherwise (Google) fall back to host+path
    without the size/tracking query string.
    """
    try:
        parsed = urlparse(url)
        name = parsed.path.rsplit("/", 1)[-1]
        match = re.match(r"(\d{6,})_", name)
        if match:
            return match.group(1)
        return f"{parsed.netloc}{parsed.path}"
    except Exception:
        return url.split("?", 1)[0]


def _dedupe_photos(urls: list[str]) -> list[str]:
    """Keep photos unique by stable IMAGE IDENTITY (not raw URL) in order, capped at ``_MAX_PHOTOS``.

    In-browser rehosted photos arrive as ``data:image`` URIs (see ``_rehost_fb_photos``): they carry no
    fbcdn host, so they must skip the scontent/asset filters — otherwise this second dedup pass, run at
    build time, silently drops every captured photo and the prospect renders imageless again.
    """
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        cleaned = (url or "").strip()
        if not cleaned:
            continue
        is_data_uri: bool = cleaned.startswith("data:image")
        if not is_data_uri:
            # Icons / static assets sometimes slip through if the page rewrites src.
            if not re.search(r"scontent", cleaned, re.IGNORECASE):
                continue
            if re.search(r"emoji\.php|rsrc\.php|static\.xx\.fbcdn", cleaned, re.IGNORECASE):
                continue
        key = cleaned if is_data_uri else photo_identity(cleaned)
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
        if len(out) >= _MAX_PHOTOS:
            break
    return out


def _parse_bio_from_embedded_texts(texts: list[str]) -> str | None:
    """Pick the longest Relay ``text`` that looks like the page Intro bio.

    Args:
        texts: Decoded ``text`` payloads from the page HTML.

    Returns:
        A multi-sentence bio, or None when nothing usable is found.
    """
    candidates: list[str] = []
    for text in texts:
        cleaned = " ".join(part.strip() for part in text.splitlines() if part.strip())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) < 60:
            continue
        if _BIO_NOISE_RE.search(cleaned):
            continue
        if _REVIEW_HEADER_RE.match(cleaned.splitlines()[0] if cleaned else ""):
            continue
        # Prefer blurbs that read like a business intro (multi-sentence / « Food Truck »…).
        if cleaned.count(".") + cleaned.count("!") + cleaned.count("?") < 1 and len(cleaned) < 120:
            continue
        candidates.append(cleaned)
    if not candidates:
        return None
    return max(candidates, key=len)


def _pick_description(
    *,
    intro_text: str,
    about_text: str,
    og_description: str | None,
    embedded_texts: list[str] | None = None,
) -> str | None:
    """Prefer Intro card / embedded bio, then og:description, then about text."""
    candidates = [
        _parse_intro_description(intro_text),
        _parse_bio_from_embedded_texts(embedded_texts or []),
        _parse_og_description(og_description),
        _parse_intro_description(about_text),
    ]
    # Longest non-empty wins — og:description is often truncated with « … ».
    picked = [item for item in candidates if item]
    if not picked:
        return None
    return max(picked, key=len)


class FacebookEnrichmentScraper:
    """Gathers proof data (rating, reviews, socials, photos) from a public Facebook page."""

    async def enrich(self, *, business_name: str, facebook_url: str) -> EnrichmentData:
        """Scrape a prospect's Facebook page into an ``EnrichmentData`` (source « facebook »).

        Args:
            business_name: Prospect name (logging only).
            facebook_url: Public Facebook page URL.

        Returns:
            The scraped enrichment; an empty « facebook » payload when nodriver is
            unavailable or the page could not be read.
        """
        if not NODRIVER_AVAILABLE:
            logger.warning("nodriver not available — Facebook enrichment skipped for %s", business_name)
            return EnrichmentData(source="facebook")

        async def task() -> EnrichmentData:
            return await self._enrich_nodriver(business_name, facebook_url)

        return await run_nodriver_task(task, timeout=180)

    async def _enrich_nodriver(self, business_name: str, facebook_url: str) -> EnrichmentData:
        """nodriver implementation: home → photos → reviews, dismiss login each hop."""
        # Facebook throttles logged-out photo scrolling behind a « Voir plus sur Facebook » wall after
        # ~30 photos. A dedicated persistent Chrome profile did NOT lift it (tested: a fresh profile
        # can't reproduce a real browser's years of trusted cookies), so we stay ephemeral — the wall is
        # a hard limit of logged-out scraping, and the perceptual dedup already trims the duplicates.
        browser = NodriverBrowser(ephemeral=True)
        try:
            tab = await browser.get_tab(self._base_url(facebook_url))
            await self._prepare_tab(tab)
            if not await NodriverDom.wait_for_selector(tab, "h1", timeout_s=10.0):
                logger.info("Facebook enrichment: page not readable for %s", business_name)
                return EnrichmentData(source="facebook")
            page = await self._extract_json(tab, _FB_PAGE_JS)
            photos = await self._extract_photos(tab, facebook_url)
            photos = await self._rehost_fb_photos(photos)
            # The logo is the FB profile photo (fbcdn): capture it too, else generation drops it as
            # unrehostable and the site loses its logo/favicon (#18, applied to the logo this time).
            logo_src = page.get("profile_photo")
            if isinstance(logo_src, str) and logo_src.strip():
                page["profile_photo"] = (await self._rehost_fb_photos([logo_src]))[0]
            reviews_text, embedded_texts = await self._extract_reviews(tab, facebook_url)
            return self._build_from_raw(page, reviews_text, photos, embedded_texts)
        except Exception as exc:
            logger.warning("Facebook enrichment failed for %s: %s", business_name, exc)
            return EnrichmentData(source="facebook")
        finally:
            await browser.close()

    @staticmethod
    def _base_url(facebook_url: str) -> str:
        """Normalize a Facebook page URL to a root that the /photos_by, /photos_of, /reviews
        sub-pages actually accept. A « /p/{slug}-{id}/ » permalink, a « /people/{name}/{id}/ »
        profile URL or a « profile.php?id={id} » URL does NOT support those sub-pages — Facebook
        redirects « /…/photos_by » to a generic « facebook.com/photos_by » (no page → 0 photos).
        Collapse them all to the numeric-id root « facebook.com/{id} », which the sub-pages DO accept.
        """
        raw = facebook_url.strip()
        if not raw.startswith("http"):
            raw = f"https://{raw}"
        match = (
            re.search(r"profile\.php\?id=(\d+)", raw)
            or re.search(r"/people/[^/]+/(\d{6,})", raw)
            or re.search(r"/p/[^/?#]*?-(\d{6,})(?:[/?#]|$)", raw)
        )
        if match:
            return f"https://www.facebook.com/{match.group(1)}"
        return raw.split("?")[0].rstrip("/")

    @classmethod
    def _photos_by_url(cls, facebook_url: str) -> str:
        """Photos uploaded by the page itself."""
        return f"{cls._base_url(facebook_url)}/photos_by"

    @classmethod
    def _photos_of_url(cls, facebook_url: str) -> str:
        """Tagged photos (customers photographing the business)."""
        return f"{cls._base_url(facebook_url)}/photos_of"

    @classmethod
    def _reviews_url(cls, facebook_url: str) -> str:
        """The « Avis » sub-page URL (recommendations)."""
        return f"{cls._base_url(facebook_url)}/reviews"

    async def _dismiss_login_gate(self, tab: Any) -> None:
        """Close the login modal with a soft click (best-effort)."""
        try:
            await NodriverDom.evaluate(tab, _DISMISS_LOGIN_JS, by_value=True)
        except Exception:
            pass

    async def _prepare_tab(self, tab: Any) -> None:
        """Dismiss the login wall, expand truncated blurbs, let the public DOM settle."""
        await self._dismiss_login_gate(tab)
        await asyncio.sleep(0.8)
        await self._dismiss_login_gate(tab)
        try:
            await NodriverDom.evaluate(tab, _EXPAND_SEE_MORE_JS, by_value=True)
        except Exception:
            pass
        await asyncio.sleep(0.4)

    async def _extract_json(self, tab: Any, script: str) -> dict[str, Any]:
        """Evaluate a JS IIFE and coerce the JSON payload to a dict."""
        raw = await NodriverDom.evaluate(tab, f"JSON.stringify({script})", by_value=True)
        if not isinstance(raw, str):
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    async def _rehost_fb_photos(self, photos: list[str]) -> list[str]:
        """Capture the top Facebook-CDN photos as base64 ``data:`` URIs, now, while their short-lived
        signed URLs are still valid.

        fbcdn URLs are signed and expire within days: by generation time they would be dead, so the bytes
        must be grabbed at scrape time. This runs on the operator's residential connection (like the whole
        scrape), where a plain HTTP GET of the signed URL succeeds — no browser, no CORS, no Facebook
        session needed (the signature travels in the URL itself). Downloading server-side here is far more
        reliable than the previous in-browser ``fetch`` (which silently lost most photos to CORS/timing).
        The captured data URIs are later moved to permanent R2 storage when the enrichment is persisted.
        Best-effort + additive: any photo we cannot capture is left as its original URL, so generation's
        drop-then-fallback still yields a complete site.
        """

        def _is_fb_cdn(url: str) -> bool:
            low: str = url.lower()
            return "fbcdn" in low or "scontent" in low

        targets: list[str] = [p for p in photos if _is_fb_cdn(p)][:_FB_REHOST_CAP]
        if not targets:
            return photos

        captured: dict[str, str] = await self._download_as_data_uris(targets)
        if captured:
            logger.info("Facebook enrichment: captured %d/%d fbcdn photo(s) as data URIs", len(captured), len(targets))
        else:
            logger.warning("Facebook enrichment: 0/%d fbcdn photos captured (download failed)", len(targets))
        return [captured.get(p, p) for p in photos]

    @staticmethod
    async def _download_as_data_uris(urls: list[str]) -> dict[str, str]:
        """Download image URLs concurrently, returning ``{url: data-uri}`` for the ones that succeeded.

        Args:
            urls: Full-size fbcdn photo URLs (already upgraded by ``_upgrade_fb_photo_url``).

        Returns:
            One base64 ``data:`` URI per URL that returned a real image under the size guard; a dead link,
            oversized body or non-image is simply omitted.
        """
        semaphore = asyncio.Semaphore(_FB_DOWNLOAD_CONCURRENCY)
        captured: dict[str, str] = {}

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            headers=_FB_DOWNLOAD_HEADERS,
            follow_redirects=True,
        ) as client:

            async def _grab(url: str) -> None:
                async with semaphore:
                    try:
                        response = await client.get(url)
                    except httpx.HTTPError:
                        return
                    if response.status_code != 200:
                        return
                    data: bytes = response.content
                    if not data or len(data) > _FB_PHOTO_MAX_BYTES:
                        return
                    content_type: str = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
                    # A non-image type means fbcdn served an error/login HTML page, not the photo — skip
                    # it. A missing type (fbcdn sometimes omits it) is trusted as an image.
                    if content_type and not content_type.startswith("image/"):
                        return
                    encoded: str = base64.b64encode(data).decode("ascii")
                    captured[url] = f"data:{content_type or 'image/jpeg'};base64,{encoded}"

            await asyncio.gather(*(_grab(url) for url in urls))
        return captured

    async def _extract_photos(self, tab: Any, facebook_url: str) -> list[str]:
        """Read photos from « prises par » then « identifiées », filtered for real media."""
        collected: list[str] = []
        for url in (self._photos_by_url(facebook_url), self._photos_of_url(facebook_url)):
            try:
                await NodriverDom.navigate(tab, url, sleep_s=1.2)
                await self._prepare_tab(tab)
                # Facebook only renders the first ~10 photos until the grid is scrolled — page through
                # it several times (dismissing the login gate each hop) so we gather the fuller set.
                for _ in range(10):
                    try:
                        await NodriverDom.evaluate(tab, _SCROLL_REVIEWS_JS, by_value=True)
                    except Exception:
                        break
                    await asyncio.sleep(0.5)
                    await self._dismiss_login_gate(tab)
                payload = await self._extract_json(tab, _FB_PHOTOS_JS)
                for photo in payload.get("photos", []):
                    if isinstance(photo, str) and photo.strip():
                        collected.append(_upgrade_fb_photo_url(photo.strip()))
            except Exception as exc:
                logger.info("Facebook photos tab not readable (%s): %s", url, exc)
        return _dedupe_photos(collected)

    async def _extract_reviews(self, tab: Any, facebook_url: str) -> tuple[str, list[str]]:
        """Open the reviews tab and return visible text + embedded Relay text payloads."""
        try:
            await NodriverDom.navigate(tab, self._reviews_url(facebook_url), sleep_s=1.4)
            await self._prepare_tab(tab)
            for _ in range(5):
                try:
                    await NodriverDom.evaluate(tab, _SCROLL_REVIEWS_JS, by_value=True)
                except Exception:
                    break
                await asyncio.sleep(0.5)
                await self._dismiss_login_gate(tab)
            payload = await self._extract_json(tab, _FB_REVIEWS_JS)
            reviews_text = str(payload.get("reviews_text") or "")
            embedded_raw = payload.get("embedded_texts") or []
            embedded_texts = [str(item).strip() for item in embedded_raw if isinstance(item, str) and item.strip()]
            return reviews_text, embedded_texts
        except Exception as exc:
            logger.info("Facebook reviews tab not readable: %s", exc)
        return "", []

    @staticmethod
    def _build_from_raw(
        dom: dict[str, Any],
        reviews_text: str,
        photos: list[str] | None = None,
        embedded_texts: list[str] | None = None,
    ) -> EnrichmentData:
        """Coerce the raw page payload + reviews into a typed ``EnrichmentData``."""
        about_text = str(dom.get("about_text") or "")
        intro_text = str(dom.get("intro_text") or "")
        og_description = str(dom["og_description"]).strip() if dom.get("og_description") else None
        page_embedded_raw = dom.get("embedded_texts") or []
        page_embedded = [str(item).strip() for item in page_embedded_raw if isinstance(item, str) and item.strip()]
        rating_pct, reviews_count = _parse_about_stats(f"{about_text}\n{intro_text}\n{reviews_text}")
        # Clean each social URL (unwraps login redirects) then keep only the usable ones.
        social: dict[str, str] = {}
        for network, url in (dom.get("social") or {}).items():
            if not (isinstance(url, str) and url.strip()):
                continue
            cleaned = _clean_social_url(url)
            if cleaned:
                social[str(network)] = cleaned
        photo_urls = _dedupe_photos(
            list(photos or []) or [str(url) for url in dom.get("photos", []) if isinstance(url, str) and url.strip()]
        )
        place_title = str(dom["place_title"]).strip() if dom.get("place_title") else None
        website = str(dom["website"]).strip() if dom.get("website") else None
        if website and not _website_belongs_to_business(website, place_title):
            logger.debug("[Facebook] Dropping third-party website '%s' (no name match with '%s')", website, place_title)
            website = None
        place_city, place_postal_code = _parse_city_postal(intro_text, str(og_description or ""), about_text[:4000])
        phone = _parse_phone(intro_text, about_text[:4000])
        description = _pick_description(
            intro_text=intro_text,
            about_text=about_text,
            og_description=og_description,
            embedded_texts=page_embedded,
        )
        reviews = _merge_review_lists(
            _parse_reviews_from_embedded_texts(embedded_texts or []),
            _parse_reviews(reviews_text),
        )
        # Page-harvested emails rank first, so the best contact becomes emails[0] — the prospect's send address.
        page_emails = [
            str(item).strip() for item in (dom.get("emails") or []) if isinstance(item, str) and item.strip()
        ]
        emails = _extract_emails("\n".join(page_emails), intro_text, about_text, "\n".join(page_embedded))
        logo_url = str(dom["profile_photo"]).strip() if dom.get("profile_photo") else None
        return EnrichmentData(
            source="facebook",
            rating=_rating_from_pct(rating_pct),
            reviews_count=reviews_count,
            description=description,
            website=website or None,
            photos=photo_urls,
            reviews=reviews,
            social_links=social,
            emails=emails,
            place_title=place_title or None,
            place_city=place_city,
            place_postal_code=place_postal_code,
            phone=phone,
            logo_url=logo_url,
        )


facebook_enrichment_scraper = FacebookEnrichmentScraper()
