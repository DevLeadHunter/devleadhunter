"""
Facebook discovery scraper — find businesses whose only web presence is Facebook.

Retained approach (Option 2, validated logged-out on 2026-08-25): the discovery
never touches Facebook. It runs a search-engine query ``site:facebook.com "{métier}"
"{ville}"`` (Google, then Bing for recall) through the Bright Data Web Unlocker,
extracts the Facebook *page* URLs from the results, and emits one prospect per page
carrying ``facebook_url`` (+ name, city, category). Those prospects then flow into the
already-live V1 enrichment, which reads the public Facebook page (logged-out, on the
desktop) to fill photos, reviews, email, etc.

Why a search engine and not Facebook's own search: logged-out, FB's business-page
search is behind a login wall (``/search/pages/`` → "Not Found"; only ``/public/``
works and returns personal profiles, not business pages). A search engine sidesteps
that entirely and keeps FB fully logged-out — the only place a real session would be
needed is a future high-volume variant.

This scraper is pure async HTTP (no browser), so it runs on the VPS as well as the
desktop, exactly like :mod:`scrappers.brightdata_scraper`.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
from collections.abc import Callable
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup, Tag

from enums.country import country_label
from enums.source import Source
from models.prospect import ProspectCreate
from services.scrape_progress import ScrapeProgressReporter

from .base_scraper import BaseScraper
from .brightdata_client import BrightDataClient

logger = logging.getLogger(__name__)

# First path segments that are Facebook features, never a business page.
_RESERVED_FIRST_SEGMENTS: frozenset[str] = frozenset(
    {
        "login",
        "recover",
        "reg",
        "help",
        "policies",
        "policy.php",
        "legal",
        "terms",
        "privacy",
        "settings",
        "hashtag",
        "watch",
        "gaming",
        "games",
        "marketplace",
        "events",
        "groups",
        "story.php",
        "photo.php",
        "photo",
        "permalink.php",
        "media",
        "reel",
        "reels",
        "stories",
        "bookmarks",
        "notes",
        "business",
        "ads",
        "adsmanager",
        "careers",
        "home.php",
        "biz",
        "saved",
        "messages",
        "friends",
        "search",
        "public",
        "sharer",
        "sharer.php",
        "tr",
        "plugins",
        "dialog",
        "l.php",
        "flx",
        "ajax",
        "whitehat",
        "about",
        "connect",
        "campaign",
        "fundraisers",
        "live",
        "help.php",
    }
)

# FB sub-tabs Facebook appends to a page title ("… - Home | Facebook").
_TITLE_TAB_WORDS: str = (
    r"Home|Posts|About|Photos|Videos|Reviews|Menu|Community|Shop|Services|Offers|Jobs|"
    r"Accueil|Publications|À propos|A propos|Avis|Vidéos|Boutique|Services|Menu|Offres"
)
_TITLE_TAB_RE: re.Pattern[str] = re.compile(rf"\s*[|\-–·]\s*(?:{_TITLE_TAB_WORDS})\s*$", re.IGNORECASE)
_TITLE_FACEBOOK_RE: re.Pattern[str] = re.compile(r"\s*[|\-–·]\s*Facebook\s*$", re.IGNORECASE)
_TITLE_NOTIF_PREFIX_RE: re.Pattern[str] = re.compile(r"^\s*\(\d+\)\s*")

_FB_SLUG_RE: re.Pattern[str] = re.compile(r"^[A-Za-z0-9.\-_]+$")
# Loose scan of the raw HTML to catch FB links the anchor walk missed (recall net).
_FB_URL_IN_HTML_RE: re.Pattern[str] = re.compile(r"https?://[^\s\"'<>()]*facebook\.com/[^\s\"'<>()]+", re.IGNORECASE)


def _decode_bing_redirect(href: str) -> str | None:
    """Decode a Bing ``/ck/a`` redirect to its target URL, if possible.

    Bing wraps result links as ``.../ck/a?…&u=a1<base64url>``.

    Args:
        href: The Bing redirect href.

    Returns:
        The decoded target URL, or ``None`` when it cannot be decoded.
    """
    encoded = parse_qs(urlparse(href).query).get("u", [""])[0]
    if not encoded.startswith("a1"):
        return None
    payload = encoded[2:]
    try:
        padded = payload + "=" * (-len(payload) % 4)
        return base64.urlsafe_b64decode(padded).decode("utf-8", "ignore")
    except Exception:
        return None


def _unwrap_redirect(href: str) -> str:
    """Resolve a search-engine redirect href to the real destination URL.

    Handles Google ``/url?q=…``, Bing ``/ck/a?u=a1…`` and Facebook ``l.php?u=…``.

    Args:
        href: The raw anchor href from a SERP.

    Returns:
        The destination URL (percent-decoded), or *href* unchanged when not a redirect.
    """
    parsed = urlparse(href)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    if path == "/url" or (host.endswith("google.com") and path.endswith("/url")):
        target = parse_qs(parsed.query).get("q", [""])[0]
        return unquote(target) if target else href
    if host.endswith("bing.com") and path.startswith("/ck/a"):
        decoded = _decode_bing_redirect(href)
        return decoded if decoded else href
    if host.endswith("facebook.com") and path.endswith("l.php"):
        target = parse_qs(parsed.query).get("u", [""])[0]
        return unquote(target) if target else href
    return href


def normalize_facebook_page_url(raw: str) -> str | None:
    """Reduce any Facebook URL to the canonical page URL, or ``None`` if not a page.

    A page reference (``/{handle}``, ``/pg/{handle}``, ``/pages/{name}/{id}``,
    ``/people/{name}/{id}``, ``/profile.php?id=…``) collapses to its root, dropping
    sub-tabs, posts, photos and tracking query strings. Feature URLs (login, groups,
    watch, sharer…) return ``None``.

    Args:
        raw: Any URL that may point at a Facebook page.

    Returns:
        ``https://www.facebook.com/…`` canonical page URL, or ``None``.
    """
    parsed = urlparse(raw.strip())
    host = parsed.netloc.lower()
    if host != "facebook.com" and not host.endswith(".facebook.com"):
        return None

    segments = [seg for seg in parsed.path.split("/") if seg]
    if not segments:
        return None
    first = segments[0].lower()

    if first == "profile.php":
        page_id = parse_qs(parsed.query).get("id", [""])[0]
        return f"https://www.facebook.com/profile.php?id={page_id}" if page_id.isdigit() else None
    if first == "pg":
        return (
            normalize_facebook_page_url(f"https://www.facebook.com/{'/'.join(segments[1:])}")
            if len(segments) > 1
            else None
        )
    if first == "pages":
        if len(segments) >= 3 and segments[1].lower() != "category" and _FB_SLUG_RE.match(segments[2]):
            return f"https://www.facebook.com/pages/{segments[1]}/{segments[2]}"
        return None
    if first == "people":
        if len(segments) >= 3 and segments[2].isdigit():
            return f"https://www.facebook.com/people/{segments[1]}/{segments[2]}"
        return None
    if first in _RESERVED_FIRST_SEGMENTS:
        return None

    slug = segments[0]
    if not _FB_SLUG_RE.match(slug) or slug.endswith(".php"):
        return None
    return f"https://www.facebook.com/{slug}"


def clean_serp_title(title: str) -> str:
    """Strip Facebook boilerplate from a SERP result title.

    Removes a leading notification count ``(3)``, trailing FB sub-tab words
    (``- Home``, ``- Avis``…) and a trailing ``| Facebook``.

    Args:
        title: Raw ``<h3>`` / anchor text from the SERP.

    Returns:
        The business name, whitespace-collapsed (may be empty).
    """
    cleaned = _TITLE_NOTIF_PREFIX_RE.sub("", title or "")
    cleaned = _TITLE_FACEBOOK_RE.sub("", cleaned)
    cleaned = _TITLE_TAB_RE.sub("", cleaned)
    cleaned = _TITLE_FACEBOOK_RE.sub("", cleaned)  # e.g. "… - Home | Facebook" needed two passes
    return re.sub(r"\s+", " ", cleaned).strip()


def humanize_facebook_slug(page_url: str) -> str:
    """Derive a readable business name from a Facebook page URL, as a last resort.

    Args:
        page_url: A canonical Facebook page URL.

    Returns:
        A title-cased name, or ``"Page Facebook"`` when the slug carries no words.
    """
    segments = [seg for seg in urlparse(page_url).path.split("/") if seg]
    if not segments or segments[0] == "profile.php":
        return "Page Facebook"
    slug = segments[1] if segments[0] in {"pages", "people"} and len(segments) > 1 else segments[0]
    words = re.sub(r"[._\-]+", " ", slug).strip()
    words = re.sub(r"\d+", " ", words).strip()
    return words.title() if words else "Page Facebook"


def _title_for_anchor(anchor: Tag) -> str:
    """Best-effort result title for a SERP anchor (Google ``<h3>`` or Bing text).

    Args:
        anchor: The ``<a>`` tag pointing at a Facebook page.

    Returns:
        The raw title text (uncleaned), or an empty string.
    """
    heading = anchor.find("h3")
    if heading is None:
        parent = anchor.parent
        for _ in range(3):
            if parent is None:
                break
            heading = parent.find("h3") if isinstance(parent, Tag) else None
            if heading is not None:
                break
            parent = parent.parent
    if heading is not None:
        return heading.get_text(" ", strip=True)
    return anchor.get_text(" ", strip=True).split("\n")[0]


def extract_facebook_results(html: str) -> list[tuple[str, str]]:
    """Extract ``(canonical_page_url, raw_title)`` pairs from one SERP page.

    Walks anchors first (they carry titles), then sweeps the raw HTML for any
    Facebook link the anchors missed. De-duplicated by canonical URL, first title
    wins, source order preserved.

    Args:
        html: Raw SERP HTML (Google or Bing).

    Returns:
        List of ``(page_url, title)`` — *title* may be empty for regex-only hits.
    """
    soup = BeautifulSoup(html, "html.parser")
    results: dict[str, str] = {}

    for anchor in soup.find_all("a", href=True):
        page_url = normalize_facebook_page_url(_unwrap_redirect(str(anchor["href"])))
        if page_url and page_url not in results:
            results[page_url] = _title_for_anchor(anchor)

    for match in _FB_URL_IN_HTML_RE.findall(html):
        page_url = normalize_facebook_page_url(_unwrap_redirect(unquote(match)))
        if page_url and page_url not in results:
            results[page_url] = ""

    return list(results.items())


class FacebookSearchScraper(BaseScraper):
    """Discover Facebook-only businesses through a search engine (never touching FB)."""

    def __init__(self) -> None:
        """Register as the ``facebook`` source and build the SERP client."""
        super().__init__(source=Source.FACEBOOK)
        self._client = BrightDataClient()

    def _queries(self, category: str, city: str, country: str = "FR") -> list[str]:
        """Build the SERP queries, precise first then looser for recall.

        Args:
            category: Business category (e.g. ``"food truck"``).
            city: City to search in.
            country: Search country — its name joins the loose queries so homonym
                     cities abroad do not pollute the results.

        Returns:
            Ordered list of search queries.
        """
        label = "" if country == "FR" else f" {country_label(country)}"
        return [
            f'site:facebook.com "{category}" "{city}"',
            f"site:facebook.com {category} {city}{label}",
            # Pages whose snippet surfaces a gmail address — exactly the segment the
            # match filter keeps (email required), so this variant boosts usable recall.
            f'site:facebook.com {category} {city}{label} "gmail.com"',
        ]

    # SERP pages fetched per engine × query (20 results each). Deeper pages are only
    # paid for while shallower ones still yield unseen Facebook pages.
    _PAGES_PER_QUERY: int = 3

    async def _fetch_serp(self, engine: str, query: str, page: int, country: str = "FR") -> str | None:
        """Fetch one SERP page from *engine*, returning ``None`` on failure.

        Args:
            engine: ``"google"`` or ``"bing"``.
            query: The search query.
            page: 0-based SERP page (20 results per page).
            country: Ranking country forwarded to the SERP client.

        Returns:
            Raw SERP HTML, or ``None`` when the fetch failed.
        """
        try:
            if engine == "google":
                return await self._client.google(query, start=page * 20, country=country)
            return await self._client.bing(query, first=page * 20 + 1, country=country)
        except Exception as exc:
            # Warning, not debug: with a bad token / Bright Data outage EVERY fetch lands
            # here and the run would otherwise look like a plain "0 results".
            logger.warning("[Facebook] %s SERP failed for '%s' (page %d): %s", engine, query, page, exc)
            return None

    async def scrape(
        self,
        category: str,
        city: str,
        max_results: int = 50,
        *,
        country: str = "FR",
        only_without_website: bool = True,
        progress: ScrapeProgressReporter | None = None,
        should_stop: Callable[[], bool] | None = None,
    ) -> list[ProspectCreate]:
        """Discover Facebook pages for *category* + *city*, streaming candidates.

        Candidates are emitted through *progress* AS they are found, page after SERP
        page: the job filters each one (already-excluded pages, duplicates) without
        counting the filtered ones, so ``should_stop`` staying ``False`` makes this
        scraper dig into DEEPER result pages until the job has the candidates it
        needs or every engine × query × page combination is exhausted.

        ``only_without_website`` is accepted for interface parity but not applied
        here: discovery does not fetch each Facebook page, so the site is unknown at
        this stage. The website (if any) is resolved by the enrichment that follows,
        and the match filter runs there.

        Args:
            category: Business category to search for (e.g. ``"food truck"``).
            city: City to search in.
            max_results: Emission cap when no *should_stop* drives the run.
            only_without_website: Ignored here (see above).
            progress: Optional SSE reporter for streaming progress events.
            should_stop: Optional callable; when it returns ``True`` the scrape aborts.

        Returns:
            List of :class:`ProspectCreate` carrying ``facebook_url``, in discovery order.
        """
        logger.info("[Facebook] Starting discovery category=%s city=%s max=%s", category, city, max_results)
        await self.start()
        try:
            self._client.reload_credentials()
            if not self._client.is_configured:
                logger.warning("[Facebook] No Bright Data token — set BRIGHTDATA_API_TOKEN to enable this source")
                if progress:
                    await progress.log("Facebook — Bright Data non configuré, source ignorée.")
                return []

            if progress:
                await progress.log(f"Facebook — recherche de pages ({category} / {city})…")

            queries = self._queries(category, city, country)
            emitted: set[str] = set()  # canonical urls already emitted to the caller
            prospects: list[ProspectCreate] = []
            attempts = failures = 0

            def enough() -> bool:
                """Whether to stop digging — the caller said stop, or the cap is hit."""
                if should_stop is not None:
                    return should_stop()
                return len(prospects) >= max_results

            for engine in ("google", "bing"):
                engine_label = "Google" if engine == "google" else "Bing"
                for query_index, query in enumerate(queries, start=1):
                    for page in range(self._PAGES_PER_QUERY):
                        if enough():
                            break
                        attempts += 1
                        if progress:
                            # Each SERP fetch takes ~10-20s through Bright Data — heartbeat
                            # so the journal shows the search alive during that stretch.
                            await progress.log(
                                f"Facebook — {engine_label} : requête {query_index}/{len(queries)}, page {page + 1}…"
                            )
                        html = await self._fetch_serp(engine, query, page, country)
                        if html is None:
                            failures += 1
                            break  # deeper pages of a failing engine/query would fail too
                        new_on_page = 0
                        for page_url, raw_title in extract_facebook_results(html):
                            if page_url in emitted:
                                continue
                            emitted.add(page_url)
                            new_on_page += 1
                            name = (clean_serp_title(raw_title) or humanize_facebook_slug(page_url))[:200]
                            prospect = ProspectCreate(
                                name=name or "Page Facebook",
                                city=city,
                                phone=None,
                                email=None,
                                website=None,
                                website_status=None,
                                facebook_url=page_url,
                                category=category,
                                source=Source.FACEBOOK,
                                # Discovery-only: name/contact are unverified until enrichment runs.
                                confidence=1,
                                social_url=page_url,
                            )
                            prospects.append(prospect)
                            if progress:
                                await progress.prospect(prospect)
                            if enough():
                                break
                        await asyncio.sleep(0.3)
                        # A page with nothing new means this query is exhausted —
                        # don't pay for its deeper pages.
                        if new_on_page == 0:
                            break
                    if enough():
                        break
                if enough():
                    break

            if progress:
                if not emitted and attempts and failures == attempts:
                    # Every SERP fetch failed — surface it as an outage, not a thin market.
                    await progress.log("Facebook — recherche moteur en échec (Bright Data), voir les logs serveur.")
                else:
                    await progress.log(f"Facebook — {len(emitted)} page(s) candidate(s) trouvée(s).")

            logger.info("[Facebook] Final: %d candidate(s) emitted", len(prospects))
            return prospects

        except Exception as exc:
            logger.error("[Facebook] Unexpected error: %s", exc, exc_info=True)
            return []
        finally:
            await self.stop()
