"""
Complementary enrichment from OpenStreetMap (via Nominatim) — structured, free, no blocking.

Google Maps (the primary enricher) is rich but fragile and blockable; OSM fills its gaps
with STABLE structured tags from the public Nominatim API (no browser, no captcha, IP-agnostic).
Measured coverage on French artisans: ~60 % expose ``opening_hours`` (Google's weakest field),
plus ``contact:facebook`` / ``contact:instagram`` (social links Google never gave us), ``email``,
``website``, ``phone`` and occasionally ``description``. OSM has almost no photos, so it stays
complementary to Google rather than a replacement.

Looked up by business name + city via Nominatim search with ``extratags`` (which returns the
OSM tags directly) — purpose-built for named lookup, unlike a costly Overpass regex scan.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_HEADERS = {"User-Agent": "DevLeadHunter/1.0 (prospect enrichment)", "Accept": "application/json"}

# OSM contact:* social keys → the social_links dict key + a URL prefix to rebuild bare handles.
_SOCIAL_TAGS: dict[str, tuple[str, str]] = {
    "contact:facebook": ("facebook", "https://facebook.com/"),
    "facebook": ("facebook", "https://facebook.com/"),
    "contact:instagram": ("instagram", "https://instagram.com/"),
    "instagram": ("instagram", "https://instagram.com/"),
    "contact:linkedin": ("linkedin", "https://www.linkedin.com/"),
    "contact:youtube": ("youtube", "https://youtube.com/"),
    "contact:tiktok": ("tiktok", "https://www.tiktok.com/"),
    "contact:twitter": ("twitter", "https://twitter.com/"),
}

# OSM English day tokens → French labels.
_DAYS: dict[str, str] = {
    "Mo": "Lun", "Tu": "Mar", "We": "Mer", "Th": "Jeu",
    "Fr": "Ven", "Sa": "Sam", "Su": "Dim",
    "PH": "Jours fériés", "SH": "Vacances scolaires",
}


def _normalize_name(value: str) -> str:
    """Lowercase, strip accents/punctuation for fuzzy name comparison."""
    lowered = value.strip().lower()
    lowered = lowered.encode("ascii", "ignore").decode("ascii")  # drop accents
    return re.sub(r"[^a-z0-9]+", " ", lowered).strip()


def parse_osm_opening_hours(spec: str) -> list[dict[str, str]]:
    """Parse an OSM ``opening_hours`` string into readable ``[{day, hours}]`` rows.

    Handles the common cases (``Mo-Fr 08:00-12:00,14:00-18:00; Sa 09:00-12:00; Su off``,
    ``24/7``); a rule it can't split is kept verbatim so nothing is lost. Not the full OSM
    spec (which is famously complex) — just enough for a website's hours section.

    @param spec - Raw OSM ``opening_hours`` value.
    @returns A list of ``{day, hours}`` (French day labels).
    """
    if not spec or not isinstance(spec, str):
        return []
    if spec.strip() == "24/7":
        return [{"day": "7j/7", "hours": "24h/24"}]

    rows: list[dict[str, str]] = []
    for rule in spec.split(";"):
        rule = rule.strip()
        if not rule:
            continue
        match = re.match(r"^([A-Za-z,\-\s]+?)\s+(.+)$", rule)
        if not match:
            rows.append({"day": "", "hours": rule})
            continue
        day_spec, time_spec = match.group(1).strip(), match.group(2).strip()
        day_label = _translate_days(day_spec)
        if time_spec.lower() in {"off", "closed"}:
            hours_label = "Fermé"
        else:
            hours_label = time_spec.replace(",", ", ").replace("-", "–")
        rows.append({"day": day_label, "hours": hours_label})
    return rows[:7]


def _translate_days(day_spec: str) -> str:
    """Translate an OSM day spec (``Mo-Fr``, ``Mo,We,Fr``) to a French label."""
    parts: list[str] = []
    for token in day_spec.split(","):
        token = token.strip()
        range_match = re.match(r"^([A-Za-z]{2})-([A-Za-z]{2})$", token)
        if range_match:
            start = _DAYS.get(range_match.group(1), range_match.group(1))
            end = _DAYS.get(range_match.group(2), range_match.group(2))
            parts.append(f"{start}–{end}")
        else:
            parts.append(_DAYS.get(token, token))
    return ", ".join(parts)


def _social_from_tags(tags: dict[str, str]) -> dict[str, str]:
    """Build a ``{network: url}`` dict from OSM ``contact:*`` social tags."""
    social: dict[str, str] = {}
    for tag_key, (network, prefix) in _SOCIAL_TAGS.items():
        value = tags.get(tag_key)
        if not value or network in social:
            continue
        url = value.strip()
        if not url.startswith("http"):
            url = prefix + url.lstrip("@/")
        social[network] = url
    return social


def _extract_from_tags(tags: dict[str, str]) -> dict[str, Any]:
    """Map OSM tags (Nominatim ``extratags``) to the enrichment fields OSM is good at."""
    if not isinstance(tags, dict):
        return {}
    result: dict[str, Any] = {}

    hours = parse_osm_opening_hours(tags.get("opening_hours", ""))
    if hours:
        result["opening_hours"] = hours

    social = _social_from_tags(tags)
    if social:
        result["social_links"] = social

    description = (tags.get("description") or "").strip()
    if description:
        result["description"] = description

    email = (tags.get("email") or tags.get("contact:email") or "").strip()
    if email:
        result["email"] = email

    website = (tags.get("website") or tags.get("contact:website") or "").strip()
    if website:
        result["website"] = website

    phone = (tags.get("phone") or tags.get("contact:phone") or "").strip()
    if phone:
        result["phone"] = phone

    return result


def _result_name(result: dict[str, Any]) -> str:
    """Best available name for a Nominatim result (namedetails, else display_name head)."""
    named = result.get("namedetails") or {}
    if isinstance(named, dict) and named.get("name"):
        return str(named["name"])
    display = str(result.get("display_name") or "")
    return display.split(",")[0]


def _best_match(results: list[dict[str, Any]], business_name: str) -> Optional[dict[str, Any]]:
    """Pick the Nominatim result whose name best matches (exact-normalised > contains)."""
    target = _normalize_name(business_name)
    if not target:
        return None
    exact: Optional[dict[str, Any]] = None
    contains: Optional[dict[str, Any]] = None
    for result in results:
        name = _normalize_name(_result_name(result))
        if not name:
            continue
        if name == target and exact is None:
            exact = result
        elif contains is None and (target in name or name in target):
            contains = result
    return exact or contains


async def enrich_from_osm(business_name: str, city: Optional[str]) -> dict[str, Any]:
    """Fetch complementary enrichment for one business from OpenStreetMap.

    @param business_name - The business to look up.
    @param city - City appended to the search query to disambiguate.
    @returns A partial enrichment dict (only the fields OSM could resolve): any of
        ``opening_hours``, ``social_links``, ``description``, ``email``, ``website``,
        ``phone``. Empty dict when nothing is found or OSM is unreachable.
    """
    if not business_name or not business_name.strip():
        return {}
    query = f"{business_name.strip()}, {city.strip()}" if city and city.strip() else business_name.strip()
    params = {
        "q": query,
        "format": "json",
        "limit": 5,
        "countrycodes": "fr",
        "extratags": 1,
        "namedetails": 1,
    }
    try:
        async with aiohttp.ClientSession(headers=_HEADERS) as session:
            async with session.get(
                _NOMINATIM_URL, params=params, timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                if response.status != 200:
                    logger.info("Nominatim enrichment returned %s for %s", response.status, business_name)
                    return {}
                results = await response.json()
        if not isinstance(results, list) or not results:
            return {}
        match = _best_match(results, business_name)
        if match is None:
            return {}
        return _extract_from_tags(match.get("extratags") or {})
    except Exception as exc:  # noqa: BLE001 — complementary source, never fatal
        logger.info("OSM enrichment unavailable for %s: %s", business_name, exc)
        return {}
