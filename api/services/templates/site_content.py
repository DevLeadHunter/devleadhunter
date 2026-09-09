"""Shared building blocks for the flat ``SiteContent`` path (Phase 4b).

Every template that opts into ``SiteContent`` (exposes ``build_site_content``) reuses the
same, template-AGNOSTIC pieces defined here:

- ``map_prospect_and_enrichment`` — maps the prospect fields + the enrichment dict into the
  common ``SiteContent`` fields (identity, contact, media, palette, reviews, opening hours).
- ``SITE_CONTENT_SCHEMAS`` — the native Storyblok section blok schemas (``section_hero``,
  ``section_about``…) + their nested item bloks, so the client's editor is a set of small forms.
- ``to_storyblok_site_content`` — projects a flat ``SiteContent`` into the page ``body`` of section bloks.
- ``from_storyblok_site_content`` — the inverse bridge (published story → flat ``SiteContent``),
  used by the Storyblok webhook to sync client edits back into ``demo_site.content_json``
  (the public site renders content_json, not Storyblok). Python mirror of demo-host's
  ``StoryblokSiteContentBridge``.

A template's own ``build_site_content`` calls ``map_prospect_and_enrichment`` and adds its
editorial ``services`` / ``faq`` (design copy, per trade). The demo-host layer supplies the
remaining boilerplate (section headings, etc.).
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from services.photo_labels import labels_for_urls, rank_card_photos
from services.validation_service import validation_service

# Operator-curated service cards (``DemoSite.section_overrides["services"]``): shape limits.
MAX_SERVICE_CARDS = 12
MAX_SERVICE_CARD_TITLE_CHARS = 80
MAX_SERVICE_CARD_DESCRIPTION_CHARS = 240

# Generic, per-trade editorial defaults. A template's build_site_content may pass these
# (or its own) so the services/FAQ sections render and stay editable in Storyblok.
PLUMBER_SERVICES: list[dict[str, str]] = [
    {
        "title": "Dépannage & urgences",
        "description": "Fuite, engorgement, panne de chauffe-eau : intervention rapide 7j/7.",
    },
    {"title": "Recherche de fuite", "description": "Détection précise sans casse inutile, puis réparation durable."},
    {"title": "Installation sanitaire", "description": "Salle de bain, cuisine, WC : pose complète et soignée."},
    {"title": "Chauffe-eau & chauffage", "description": "Installation, remplacement et entretien de vos équipements."},
    {"title": "Rénovation de salle de bain", "description": "Modernisation complète de vos pièces d'eau, clé en main."},
    {"title": "Débouchage de canalisation", "description": "Curage et débouchage rapide, sans dégât."},
]
PLUMBER_FAQ: list[dict[str, str]] = [
    {
        "question": "Intervenez-vous en urgence le week-end ?",
        "answer": "Oui, nous intervenons 7j/7 pour les urgences. Appelez, on vous rappelle rapidement.",
    },
    {
        "question": "Le devis est-il gratuit ?",
        "answer": "Le devis est toujours gratuit et sans engagement, remis avant toute intervention.",
    },
    {
        "question": "Quelles zones couvrez-vous ?",
        "answer": "Votre ville et les communes voisines. Appelez pour vérifier, nous nous déplaçons souvent au-delà.",
    },
    {
        "question": "Quels moyens de paiement acceptez-vous ?",
        "answer": "Carte bancaire, chèque et virement, avec facture détaillée.",
    },
    {
        "question": "Proposez-vous une garantie sur vos travaux ?",
        "answer": "Oui, nos installations sont couvertes par la garantie décennale.",
    },
]
ELECTRICIAN_SERVICES: list[dict[str, str]] = [
    {
        "title": "Dépannage électrique",
        "description": "Panne, court-circuit, disjoncteur qui saute : diagnostic et remise en service rapides.",
    },
    {
        "title": "Mise aux normes",
        "description": "Remise à niveau de votre installation (NF C 15-100) et attestation Consuel.",
    },
    {
        "title": "Tableau électrique",
        "description": "Remplacement et modernisation de votre tableau et de vos protections.",
    },
    {
        "title": "Installation & rénovation",
        "description": "Neuf ou rénovation : réseau complet, prises, points lumineux.",
    },
    {
        "title": "Éclairage & domotique",
        "description": "Éclairage intérieur/extérieur, interrupteurs connectés, domotique.",
    },
    {"title": "Borne de recharge", "description": "Installation de bornes de recharge pour véhicule électrique."},
]
ELECTRICIAN_FAQ: list[dict[str, str]] = [
    {
        "question": "Intervenez-vous en urgence ?",
        "answer": "Oui, pour toute panne électrique nous intervenons au plus vite, 7j/7.",
    },
    {
        "question": "Le devis est-il gratuit ?",
        "answer": "Le devis est gratuit et sans engagement, remis avant les travaux.",
    },
    {
        "question": "Délivrez-vous une attestation Consuel ?",
        "answer": "Oui, pour toute installation neuve ou mise aux normes soumise au Consuel.",
    },
    {
        "question": "Quelles zones couvrez-vous ?",
        "answer": "Votre ville et ses alentours. Appelez pour vérifier votre commune.",
    },
    {
        "question": "Vos travaux sont-ils garantis ?",
        "answer": "Oui, nos installations sont conformes et couvertes par la garantie décennale.",
    },
]


def _uid() -> str:
    """Return a fresh Storyblok ``_uid``."""
    return str(uuid.uuid4())


def _dedupe_preserve_order(urls: list[str]) -> list[str]:
    """Drop duplicate URLs while keeping first-seen order.

    A prospect's Google gallery often repeats the same shot; reusing it across hero, about and
    gallery slots is what makes generated sites look templated. Deduping keeps every slot distinct.
    """
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        unique.append(url)
    return unique


# Hosts whose image URLs can't be rehosted server-side. Facebook CDN URLs (fbcdn.net / fbsbx.com)
# are signed and session-bound: the VPS gets 403 fetching them, so they never rehost to Storyblok and
# render broken on the site. Dropping them lets the template's fallback images fill the slot.
_UNREHOSTABLE_PHOTO_HOSTS: tuple[str, ...] = ("fbcdn.net", "fbsbx.com")


def _is_unrehostable_photo(url: str) -> bool:
    """Whether a photo URL would render broken because it can't be fetched/rehosted server-side.

    A complete site with fallback imagery beats one with broken Facebook-CDN tiles. The real fix —
    capturing the bytes at desktop scrape time, where the FB session is available — supersedes this.
    """
    lowered: str = url.lower()
    return any(host in lowered for host in _UNREHOSTABLE_PHOTO_HOSTS)


def usable_site_photos(enrichment: dict[str, Any] | None) -> list[str]:
    """The prospect photos eligible for the site, in order: deduped, logo excluded, broken hosts dropped.

    This is the exact pool the generated site draws from — ``[0]`` hero, ``[1]`` about, ``[2:]`` gallery.
    Exposed so the demo-site image editor shows precisely what will render, and so a user-curated order
    can be validated against the same set.
    """
    enrichment = enrichment or {}
    logo_photo: str = str(enrichment.get("logo_url") or "").strip()
    return [
        url
        for url in _dedupe_preserve_order(
            [p.strip() for p in enrichment.get("photos", []) if isinstance(p, str) and p.strip()]
        )
        if url != logo_photo and not _is_unrehostable_photo(url)
    ]


def format_rating_value(rating: Any) -> str | None:
    """Format a Google rating the French way (``"4,5/5"``), or None when missing/unparseable."""
    if not isinstance(rating, (int, float)):
        return None
    return f"{float(rating):.1f}".replace(".", ",") + "/5"


def format_review_count(count: Any) -> str | None:
    """Format a review count with a French thin-space thousands separator (``"2 227"``).

    Returns None when the count is absent or not positive.
    """
    if not isinstance(count, (int, float)) or int(count) <= 0:
        return None
    # The separator replacing the comma is a narrow no-break space (U+202F), the French convention.
    return f"{int(count):,}".replace(",", " ")


_RATING_VALUE_RE = re.compile(r"^\d(?:[.,]\d)?\s*/\s*5$")


def apply_real_rating_trust(site: dict[str, Any], enrichment: dict[str, Any] | None) -> None:
    """Overwrite the placeholder rating repère with the prospect's real Google rating + review count.

    Called by a template's ``build_site_content`` AFTER ``_EDITORIAL_DEFAULTS`` so the scraped
    numbers win over the hardcoded "4,9/5". Targets the first trust item that already shows a star
    rating (value like "4,9/5") or whose label mentions "avis"; mutates ``site`` in place.

    Args:
        site: The flat SiteContent being built (its ``trustItems`` are mutated).
        enrichment: Scraped enrichment dict, or None — a no-op when no rating was scraped.
    """
    enr = enrichment or {}
    rating_value = format_rating_value(enr.get("rating"))
    if not rating_value:
        return
    items = site.get("trustItems")
    if not isinstance(items, list):
        return
    count = format_review_count(enr.get("reviews_count"))
    for item in items:
        if not isinstance(item, dict):
            continue
        value = str(item.get("value", "")).strip()
        label = str(item.get("label", "")).lower()
        if _RATING_VALUE_RE.match(value) or "avis" in label:
            item["value"] = rating_value
            item["label"] = f"{count} avis" if count else "Avis Google"
            return


def experience_years_from_text(text: Any) -> int | None:
    """Derive years in business from a "depuis 2012" mention in free text, or None.

    Only an explicit founding year is trusted, and only when the elapsed span is a sane 1-80 range,
    so a stray number never invents a fake seniority.
    """
    if not isinstance(text, str):
        return None
    match = re.search(r"depuis\s+(?:le\s+)?((?:19|20)\d{2})", text.lower())
    if not match:
        return None
    years = datetime.now().year - int(match.group(1))
    return years if 1 <= years <= 80 else None


def apply_real_trust_stats(site: dict[str, Any], enrichment: dict[str, Any] | None) -> None:
    """Fill a template's trust badges from real data instead of fabricated numbers.

    By label: a "satisfaction" badge derives its percentage from the real Google rating (4,9/5 → 98 %);
    an "experience" badge shows the real years in business (from a "depuis 20xx" mention), or the real
    review count when the founding year is unknown; a "rating/avis" badge shows the real rating + count.
    Each badge keeps its editorial default only when no real figure exists. Mutates ``site`` in place.
    """
    enr = enrichment or {}
    rating = enr.get("rating")
    satisfaction = round(float(rating) / 5 * 100) if isinstance(rating, (int, float)) and rating > 0 else None
    rating_value = format_rating_value(rating)
    count_value = format_review_count(enr.get("reviews_count"))
    years = experience_years_from_text(site.get("about"))
    items = site.get("trustItems")
    if not isinstance(items, list):
        return
    result: list[Any] = []
    for original in items:
        if not isinstance(original, dict):
            result.append(original)
            continue
        # Copy so the shared, module-level ``_EDITORIAL_DEFAULTS`` is never mutated across generations.
        item = dict(original)
        label = str(item.get("label", "")).lower()
        value = str(item.get("value", "")).strip()
        if "satisfait" in label or "satisfaction" in label:
            if satisfaction is not None:
                item["value"] = f"{satisfaction}%"
        elif "expérience" in label or "année" in label:
            if years is not None:
                item["value"] = f"{years}+"
            elif count_value:
                item["value"], item["label"] = count_value, "avis Google"
        elif "avis" in label or _RATING_VALUE_RE.match(value):
            if rating_value:
                item["value"] = rating_value
                item["label"] = f"{count_value} avis" if count_value else "Avis Google"
        result.append(item)
    site["trustItems"] = result


_PRICE_SUFFIX_RE = re.compile(r"\s*[—–\-]\s*\d+(?:[.,]\d+)?\s*€\s*$")


def without_price(description: Any) -> str:
    """Strip a trailing "— 32 €" price from a service description.

    Template service prices are invented defaults, never the prospect's real prices — showing one next
    to a real scraped service name is misleading. We drop the price and keep the descriptive text.
    """
    if not isinstance(description, str):
        return ""
    return _PRICE_SUFFIX_RE.sub("", description).strip()


def _match_service_description(name: str, defaults: list[dict[str, str]]) -> str:
    """Return the trade default description whose title matches the scraped service name, or ""."""
    key = name.strip().lower()
    if not key:
        return ""
    for service in defaults:
        if service.get("title", "").strip().lower() == key:
            return service.get("description", "")
    for service in defaults:
        default_key = service.get("title", "").strip().lower()
        if default_key and (default_key in key or key in default_key):
            return service.get("description", "")
    return ""


def resolve_trade_services(scraped_names: Any, defaults: list[dict[str, str]]) -> list[dict[str, str]]:
    """Build the services list for a template, never attaching an invented price to a real service.

    Scraped service names (real) are kept and paired with a name-matched default description **with the
    price stripped** (a fuller card than an empty one, without a fake price). With no scraped services,
    the template defaults are shown as a demo fallback — also price-stripped, so no site ever shows a
    made-up price.
    """
    names = [name.strip() for name in (scraped_names or []) if isinstance(name, str) and name.strip()]
    if names:
        return [
            {"title": name, "description": without_price(_match_service_description(name, defaults))} for name in names
        ]
    return [
        {"title": service.get("title", ""), "description": without_price(service.get("description", ""))}
        for service in defaults
    ]


def clean_service_cards(
    cards: Any,
    *,
    allowed_images: list[str] | None = None,
    max_cards: int = MAX_SERVICE_CARDS,
) -> list[dict[str, str]]:
    """Validate operator-curated service cards into ``{"title", "description", "image"}`` rows.

    A card without a title is dropped; texts are trimmed and capped; when ``allowed_images`` is
    given, an image outside that pool is cleared (never a URL the site can't vouch for).

    Args:
        cards: Raw cards (API payload or stored override).
        allowed_images: The site's photo pool; None skips the image check (already-cleaned data).
        max_cards: Hard cap on the number of cards kept.

    Returns:
        The clean cards, in order.
    """
    if not isinstance(cards, list):
        return []
    allowed: set[str] | None = set(allowed_images) if allowed_images is not None else None
    cleaned: list[dict[str, str]] = []
    for entry in cards:
        if not isinstance(entry, dict):
            continue
        title = " ".join(str(entry.get("title", "") or "").split()).strip()[:MAX_SERVICE_CARD_TITLE_CHARS]
        if not title:
            continue
        description = " ".join(str(entry.get("description", "") or "").split()).strip()
        image = str(entry.get("image", "") or "").strip()
        if allowed is not None and image not in allowed:
            image = ""
        cleaned.append(
            {"title": title, "description": description[:MAX_SERVICE_CARD_DESCRIPTION_CHARS], "image": image}
        )
        if len(cleaned) >= max_cards:
            break
    return cleaned


def fill_missing_card_images(site_content: dict[str, Any], enrichment: dict[str, Any] | None) -> None:
    """Give every service card without a photo the best unused real photo of the site.

    Candidates are the gallery photos, then the hero / about photos; the vision labels rank the
    dishes first and keep the truck, menu boards and flyers off the cards. Without labels the
    gallery order is used as before. The layer would otherwise fall back to ``gallery[index]``
    (position only) — which is how the truck ended up under a dish title.
    """
    services = site_content.get("services")
    if not isinstance(services, list) or not services:
        return
    gallery = [
        photo["url"]
        for photo in site_content.get("gallery", [])
        if isinstance(photo, dict) and isinstance(photo.get("url"), str) and photo["url"].strip()
    ]
    extra = [
        url for url in (site_content.get("heroImage"), site_content.get("aboutImage")) if isinstance(url, str) and url
    ]
    labels = labels_for_urls((enrichment or {}).get("photo_labels"), gallery + extra)
    used = {
        card["image"]
        for card in services
        if isinstance(card, dict) and isinstance(card.get("image"), str) and card["image"].strip()
    }
    # Without any label, stay position-based on the gallery (legacy behaviour, hero/about untouched).
    candidates = (
        rank_card_photos(gallery + extra, labels, exclude=used) if labels else [u for u in gallery if u not in used]
    )
    for card in services:
        if not isinstance(card, dict) or (isinstance(card.get("image"), str) and card["image"].strip()):
            continue
        if not candidates:
            break
        card["image"] = candidates.pop(0)


def apply_section_overrides(
    site_content: dict[str, Any],
    overrides: Any,
    enrichment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Replace generated sections with the operator's curated ones (``DemoSite.section_overrides``).

    Currently ``services``: the curated cards replace the generated menu / prestations wholesale
    (title, description, photo); cards saved without a photo get the best unused real photo.
    The override lives on the demo site, so it survives every regeneration — a colour tweak no
    longer wipes the specialties typed by hand.
    """
    if not isinstance(overrides, dict):
        return site_content
    cards = clean_service_cards(overrides.get("services"))
    if cards:
        site_content["services"] = cards
        fill_missing_card_images(site_content, enrichment)
    return site_content


def fixed_trade_services(defaults: list[dict[str, str]]) -> list[dict[str, str]]:
    """Use a template's curated service grid as-is (fake prices stripped), ignoring scraped services.

    A trade's services are standardised, so a fixed, always-complete grid — every card has a
    description, a stable count, and matches its icon — beats a scraped-driven one (variable count,
    empty cards, icon mismatches). Food is the exception: its menu is its identity, so it keeps
    ``resolve_trade_services``.
    """
    return [
        {"title": service.get("title", ""), "description": without_price(service.get("description", ""))}
        for service in defaults
    ]


_WEEKDAYS: frozenset[str] = frozenset(
    {
        "lundi",
        "mardi",
        "mercredi",
        "jeudi",
        "vendredi",
        "samedi",
        "dimanche",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    }
)
# Google truncates a long review to a preview and appends an expand-link label ("… Plus" in FR,
# "More"/"Mehr"/"Más"… otherwise); the scraper captures that label verbatim at the end of the text.
_REVIEW_READMORE_RE = re.compile(r"\s*(?:…|\.\.\.)?\s*(?:Plus|More|Mehr|Más|Mas|Meer|Altro)\s*$")


def _clean_review_text(raw: Any) -> str:
    """Tidy a scraped review for display: collapse inner whitespace and drop the "… Plus" read-more label.

    Google's review previews keep hard newlines and end with an expand-link label ("… Plus") that the
    scraper captures; both read badly on the site. This collapses whitespace runs to single spaces and
    strips the trailing read-more marker (the ellipsis and the label together), leaving a clean end.
    """
    text = re.sub(r"\s+", " ", str(raw)).strip()
    text = _REVIEW_READMORE_RE.sub("", text).strip()
    return text


_SPECIALTY_RE = re.compile(r"sp[ée]cialit[ée]s?\s*:\s*(.+)", re.IGNORECASE)
_GLUED_LABEL_RE = re.compile(r"\s+[A-ZÀ-Ý][\wÀ-ÿ]*\s*:")


def extract_specialty(description: Any) -> str:
    """Pull the cuisine specialty out of a scraped description (« … Spécialité: poulet frit coréen »).

    Google glues attribute labels into the description; the specialty is a food truck's identity and
    worth keeping even when the whole description is too fragmentary to use as an about. Returns the
    first specialty phrase (trimmed, cut before any following glued label / sentence end, capped), or "".
    """
    if not isinstance(description, str):
        return ""
    match = _SPECIALTY_RE.search(description)
    if not match:
        return ""
    specialty = re.split(r"[\n.;]", match.group(1))[0]
    specialty = _GLUED_LABEL_RE.split(specialty)[0].strip()
    return specialty[:60].strip()


_HOURS_DISCLAIMER_RE = re.compile(r"les horaires? peuvent .*|hours (?:might|may) .*", re.IGNORECASE)
_GLUED_RANGES_RE = re.compile(r"(\d{1,2}[:h]\d{2}\s*[–—-]\s*\d{1,2}[:h]\d{2})(?=\d)")
_DAY_ANNOTATION_RE = re.compile(r"\s*\([^)]*\)\s*")


def _clean_opening_hours(raw_hours: list[dict]) -> list[dict[str, str]]:
    """Clean scraped opening-hours rows for display.

    Around a public holiday, Google annotates the affected day ("samedi (Assomption)") and adds an
    "hours may differ" disclaimer, which the scraper captures verbatim — sometimes even as its own
    row. This strips the parenthetical day annotation, drops the disclaimer, separates two glued time
    ranges ("07:45–12:0014:00–18:00" → "07:45–12:00, 14:00–18:00"), and keeps only real weekday rows.
    """
    cleaned: list[dict[str, str]] = []
    for row in raw_hours:
        day = _DAY_ANNOTATION_RE.sub(" ", str(row.get("day", ""))).strip()
        if day.lower() not in _WEEKDAYS:
            continue
        hours = _HOURS_DISCLAIMER_RE.sub("", str(row.get("hours", ""))).strip()
        hours = _GLUED_RANGES_RE.sub(r"\1, ", hours).strip().strip(",").strip()
        cleaned.append({"day": day, "hours": hours})
    return cleaned


def map_prospect_and_enrichment(
    *,
    business_name: str,
    phone: str | None,
    email: str | None,
    city: str | None,
    area: str,
    subtitle: str,
    palette: dict[str, str],
    enrichment: dict[str, Any] | None = None,
    about_default: str = "",
) -> dict[str, Any]:
    """Map prospect fields + enrichment into the common (non-editorial) ``SiteContent`` fields.

    Shared by every template's ``build_site_content``. Enrichment (all keys optional):
    ``photos`` (URL strings) → ``[0]`` heroImage, ``[1]`` aboutImage, ``[2:]`` gallery;
    ``reviews`` (``[{text, author, rating}]``) → reviews; ``opening_hours`` → openingHours;
    ``description`` → about (falls back to ``about_default``). Images stay plain external URLs.

    Returns:
        The common SiteContent fields (no ``services`` / ``faq`` — those are per-template).
    """
    enrichment = enrichment or {}

    # The photo pool the site draws from ([0]→hero, [1]→about, [2:]→gallery): deduped, logo excluded
    # (it has its own slot), broken hosts dropped. A user-curated order arrives already folded into
    # ``enrichment["photos"]`` upstream, so this stays the single mapping rule.
    photos: list[str] = usable_site_photos(enrichment)
    raw_reviews: list[dict] = [r for r in enrichment.get("reviews", []) if isinstance(r, dict)]
    raw_hours: list[dict] = [h for h in enrichment.get("opening_hours", []) if isinstance(h, dict)]
    description = enrichment.get("description")

    reviews: list[dict[str, Any]] = []
    seen_reviews: set[tuple[str, str]] = set()
    for review in raw_reviews:
        text = _clean_review_text(review.get("text", ""))
        if not text:
            continue
        # Sales site: only surface reviews we are SURE are positive. A rating below 4 is a
        # complaint that undermines the pitch; a review whose per-review rating wasn't captured
        # can't be trusted as positive — both are dropped. (The enrichment record keeps every
        # review; this curation happens only for the generated site.)
        rating_value = review.get("rating")
        if not isinstance(rating_value, (int, float)) or rating_value < 4:
            continue
        author = str(review.get("author", "")).strip() or "Client"
        # Drop duplicate reviews at generation time. Scrapers can capture the same review twice, and
        # older enrichment records predate the scrape-time dedup — showing the same testimonial twice
        # cheapens a site sold at 500 €. Keyed on (author, text) so genuine distinct reviews survive.
        review_key: tuple[str, str] = (author.lower(), text.lower())
        if review_key in seen_reviews:
            continue
        seen_reviews.add(review_key)
        entry: dict[str, Any] = {
            "author": author,
            "text": text,
            "rating": int(rating_value),
        }
        reviews.append(entry)

    opening_hours: list[dict[str, str]] = _clean_opening_hours(raw_hours)

    raw_social = enrichment.get("social_links") or {}
    social: list[dict[str, str]] = [
        {"network": str(network), "url": str(url)}
        for network, url in (raw_social.items() if isinstance(raw_social, dict) else [])
        if isinstance(url, str) and url.strip()
    ]

    about = description.strip() if isinstance(description, str) and description.strip() else ""
    # Reject an unusable about before it reaches the site: a platform's own meta description
    # ("Find local businesses…") or scraped attribute fragments glued together
    # ("Food Truck à Poitiers Spécialité: …") — both read badly, so fall back to the clean default.
    if validation_service.is_generic_platform_description(about) or validation_service.is_fragmentary_description(
        about
    ):
        about = ""
    about = about or about_default
    site_city = city or area
    area_label = f"{area} et ses alentours" if city else ""

    logo_raw = enrichment.get("logo_url")
    logo = logo_raw.strip() if isinstance(logo_raw, str) and logo_raw.strip() else ""
    if logo and _is_unrehostable_photo(logo):
        logo = ""

    address_raw = enrichment.get("address")
    address = address_raw.strip() if isinstance(address_raw, str) and address_raw.strip() else ""
    latitude = enrichment.get("lat")
    longitude = enrichment.get("lng")
    rating = enrichment.get("rating")
    reviews_count = enrichment.get("reviews_count")

    return {
        "businessName": business_name,
        "phone": phone or "",
        "email": email or "",
        "address": address,
        "city": site_city,
        "area": area_label,
        "subtitle": subtitle,
        "about": about,
        "logo": logo,
        "heroImage": photos[0] if len(photos) > 0 else "",
        "aboutImage": photos[1] if len(photos) > 1 else "",
        "gallery": [{"url": url, "alt": ""} for url in photos[2:]],
        "rating": float(rating) if isinstance(rating, (int, float)) else None,
        "reviewsCount": (
            int(reviews_count) if isinstance(reviews_count, (int, float)) and int(reviews_count) > 0 else None
        ),
        "lat": float(latitude) if isinstance(latitude, (int, float)) else None,
        "lng": float(longitude) if isinstance(longitude, (int, float)) else None,
        "palette": {
            "primary": palette.get("primary", ""),
            "secondary": palette.get("secondary", ""),
            "accent": palette.get("accent", ""),
        },
        "reviews": reviews,
        "openingHours": opening_hours,
        "social": social,
    }


# Native Storyblok schema for the site content. Instead of ONE big blok with ~29 fields (a jumble
# for the client, and useless for click-to-edit), the page ``body`` is split into small SECTION
# bloks (``section_hero``, ``section_about``…), each a short, focused form. The flat ``SiteContent``
# stays unchanged — only this Storyblok projection is sectioned (``to_storyblok`` splits, the
# bridges merge back). Field labels/descriptions are in FRENCH: it is the CLIENT's editor UI.

# Field schema per flat ``SiteContent`` key (``pos`` is assigned within each section below).
FIELD_SCHEMAS: dict[str, dict[str, Any]] = {
    "heroBadge": {
        "type": "text",
        "display_name": "Badge d'en-tête",
        "description": "Petit libellé au-dessus du titre (ex : « Artisan plombier »)",
    },
    "subtitle": {
        "type": "textarea",
        "display_name": "Phrase d'accroche",
        "description": "Le texte principal en haut du site",
    },
    "heroImage": {
        "type": "asset",
        "filetypes": ["images"],
        "allow_external_url": True,
        "display_name": "Photo principale",
    },
    "heroPoints": {
        "type": "bloks",
        "display_name": "Points forts d'en-tête",
        "description": "3 arguments courts sous l'accroche",
        "restrict_components": True,
        "component_whitelist": ["site_content_hero_point"],
    },
    "ctaCallLabel": {"type": "text", "display_name": "Bouton « appeler »", "description": "Texte du bouton d'appel"},
    "ctaQuoteLabel": {
        "type": "text",
        "display_name": "Bouton « devis »",
        "description": "Texte du bouton de demande de devis",
    },
    "trustItems": {
        "type": "bloks",
        "display_name": "Repères de confiance",
        "description": "Chiffres/garanties affichés sous l'en-tête (ex : 7j/7, Devis 0 €)",
        "restrict_components": True,
        "component_whitelist": ["site_content_trust_item"],
    },
    "aboutHeading": {"type": "text", "display_name": "Titre de la section"},
    "about": {
        "type": "textarea",
        "display_name": "À propos",
        "description": "Votre histoire, votre façon de travailler",
    },
    "aboutImage": {
        "type": "asset",
        "filetypes": ["images"],
        "allow_external_url": True,
        "display_name": "Photo « à propos »",
    },
    "servicesHeading": {"type": "text", "display_name": "Titre de la section"},
    "services": {
        "type": "bloks",
        "display_name": "Services",
        "restrict_components": True,
        "component_whitelist": ["site_content_service"],
    },
    "galleryHeading": {"type": "text", "display_name": "Titre de la section"},
    "gallery": {
        "type": "multiasset",
        "filetypes": ["images"],
        "allow_external_url": True,
        "display_name": "Galerie photos",
    },
    "reviewsHeading": {"type": "text", "display_name": "Titre de la section"},
    "reviews": {
        "type": "bloks",
        "display_name": "Avis clients",
        "restrict_components": True,
        "component_whitelist": ["site_content_review"],
    },
    "faqHeading": {"type": "text", "display_name": "Titre de la section"},
    "faq": {
        "type": "bloks",
        "display_name": "Questions fréquentes",
        "restrict_components": True,
        "component_whitelist": ["site_content_faq"],
    },
    "beforeAfter": {
        "type": "bloks",
        "display_name": "Réalisations avant/après",
        "description": "Paires de photos avant travaux / après travaux",
        "restrict_components": True,
        "component_whitelist": ["site_content_before_after"],
    },
    "contactHeading": {"type": "text", "display_name": "Titre de la section"},
    "businessName": {"type": "text", "display_name": "Nom de l'entreprise"},
    "phone": {"type": "text", "display_name": "Téléphone"},
    "email": {"type": "text", "display_name": "Email de contact"},
    "city": {"type": "text", "display_name": "Ville"},
    "area": {"type": "text", "display_name": "Secteur d'intervention", "description": "Ex : « Lyon et ses alentours »"},
    "logo": {
        "type": "asset",
        "filetypes": ["images"],
        "allow_external_url": True,
        "display_name": "Logo",
        "description": "Logo de l'entreprise — utilisé comme favicon du site",
    },
    "openingHours": {
        "type": "bloks",
        "display_name": "Horaires d'ouverture",
        "restrict_components": True,
        "component_whitelist": ["site_content_hours"],
    },
    "social": {
        "type": "bloks",
        "display_name": "Réseaux sociaux",
        "description": "Liens Facebook, Instagram… affichés en pied de page",
        "restrict_components": True,
        "component_whitelist": ["site_content_social"],
    },
    "teamHeading": {"type": "text", "display_name": "Titre de la section"},
    "teamMembers": {
        "type": "bloks",
        "display_name": "Membres de l'équipe",
        "description": "Photo + nom + rôle de chaque membre présenté",
        "restrict_components": True,
        "component_whitelist": ["site_content_team_member"],
    },
    "portfolioHeading": {"type": "text", "display_name": "Titre de la section"},
    "portfolio": {
        "type": "bloks",
        "display_name": "Réalisations",
        "description": "Photo + titre + catégorie de chaque réalisation présentée",
        "restrict_components": True,
        "component_whitelist": ["site_content_portfolio_item"],
    },
}

# Single-asset fields that map to their own named ``SiteContent`` key (never the generic ``images``
# map). Any OTHER section field carrying an asset is a per-template one-off image, surfaced under
# ``images`` (see from_storyblok_site_content). Excluding ONLY these — not every known key — mirrors
# demo-host's ``StoryblokSiteContentBridge.NAMED_ASSET_KEYS``: a one-off image field that reuses a
# reserved name (e.g. the mechanic template's FAQ photo, named ``faq``) must still reach ``images``.
_NAMED_ASSET_KEYS: frozenset[str] = frozenset({"heroImage", "aboutImage", "logo"})

# Ordered page sections: (component suffix, editor label, the flat ``SiteContent`` keys it owns).
# This is the SINGLE source of truth — schema, ``to_storyblok`` split and the merge share it.
SECTION_DEFINITIONS: list[tuple[str, str, list[str]]] = [
    ("hero", "En-tête", ["heroBadge", "subtitle", "heroImage", "heroPoints", "ctaCallLabel", "ctaQuoteLabel"]),
    ("trust", "Repères de confiance", ["trustItems"]),
    ("about", "À propos", ["aboutHeading", "about", "aboutImage"]),
    ("services", "Services", ["servicesHeading", "services"]),
    ("gallery", "Photos", ["galleryHeading", "gallery"]),
    ("reviews", "Avis clients", ["reviewsHeading", "reviews"]),
    ("faq", "Questions fréquentes", ["faqHeading", "faq"]),
    ("beforeAfter", "Avant / après", ["beforeAfter"]),
    ("team", "Équipe", ["teamHeading", "teamMembers"]),
    ("portfolio", "Réalisations", ["portfolioHeading", "portfolio"]),
    (
        "contact",
        "Contact & informations",
        ["contactHeading", "businessName", "phone", "email", "city", "area", "logo", "openingHours", "social"],
    ),
]

# Storyblok component names of the section bloks (page ``body`` whitelist).
SECTION_COMPONENT_NAMES: list[str] = [f"section_{suffix}" for suffix, _, _ in SECTION_DEFINITIONS]


def _section_component(
    suffix: str, display_name: str, field_keys: list[str], extra_images: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    """Build a ``section_*`` component schema from its field keys, assigning each a ``pos``.

    ``extra_images`` appends this template's one-off image fields (asset), each
    ``{"field": <SiteContent.images key>, "label": <FR label>}`` — grouped in the section the photo
    actually appears in, and flattened back into ``SiteContent.images`` by the bridge.
    """
    schema: dict[str, Any] = {key: {**FIELD_SCHEMAS[key], "pos": index} for index, key in enumerate(field_keys)}
    for offset, extra in enumerate(extra_images or []):
        schema[extra["field"]] = {
            "type": "asset",
            "filetypes": ["images"],
            "allow_external_url": True,
            "pos": len(field_keys) + offset,
            "display_name": extra["label"],
        }
    return {"name": f"section_{suffix}", "display_name": display_name, "schema": schema}


_ITEM_BLOK_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "site_content_social",
        "display_name": "Réseau social",
        "schema": {
            "network": {
                "type": "text",
                "pos": 0,
                "display_name": "Réseau",
                "description": "facebook, instagram, linkedin, tiktok, youtube, twitter",
            },
            "url": {"type": "text", "pos": 1, "display_name": "URL du profil"},
        },
    },
    {
        "name": "site_content_service",
        "display_name": "Service",
        "schema": {
            "title": {"type": "text", "pos": 0, "display_name": "Titre"},
            "description": {"type": "textarea", "pos": 1, "display_name": "Description"},
            "image": {
                "type": "asset",
                "filetypes": ["images"],
                "allow_external_url": True,
                "pos": 2,
                "display_name": "Photo",
            },
        },
    },
    {
        "name": "site_content_team_member",
        "display_name": "Membre de l'équipe",
        "schema": {
            "photo": {
                "type": "asset",
                "filetypes": ["images"],
                "allow_external_url": True,
                "pos": 0,
                "display_name": "Photo",
            },
            "name": {"type": "text", "pos": 1, "display_name": "Nom"},
            "role": {"type": "text", "pos": 2, "display_name": "Rôle / spécialité"},
            "bio": {"type": "textarea", "pos": 3, "display_name": "Présentation"},
        },
    },
    {
        "name": "site_content_portfolio_item",
        "display_name": "Réalisation",
        "schema": {
            "image": {
                "type": "asset",
                "filetypes": ["images"],
                "allow_external_url": True,
                "pos": 0,
                "display_name": "Photo",
            },
            "title": {"type": "text", "pos": 1, "display_name": "Titre"},
            "category": {"type": "text", "pos": 2, "display_name": "Catégorie"},
        },
    },
    {
        "name": "site_content_review",
        "display_name": "Avis client",
        "schema": {
            "author": {"type": "text", "pos": 0, "display_name": "Auteur"},
            "rating": {"type": "number", "pos": 1, "display_name": "Note (0-5)"},
            "text": {"type": "textarea", "pos": 2, "display_name": "Texte de l'avis"},
        },
    },
    {
        "name": "site_content_faq",
        "display_name": "Question fréquente",
        "schema": {
            "question": {"type": "text", "pos": 0, "display_name": "Question"},
            "answer": {"type": "textarea", "pos": 1, "display_name": "Réponse"},
        },
    },
    {
        "name": "site_content_hours",
        "display_name": "Horaire",
        "schema": {
            "day": {"type": "text", "pos": 0, "display_name": "Jour(s)"},
            "hours": {"type": "text", "pos": 1, "display_name": "Heures"},
        },
    },
    {
        "name": "site_content_before_after",
        "display_name": "Avant / après",
        "schema": {
            "before": {
                "type": "asset",
                "filetypes": ["images"],
                "allow_external_url": True,
                "pos": 0,
                "display_name": "Photo avant",
            },
            "after": {
                "type": "asset",
                "filetypes": ["images"],
                "allow_external_url": True,
                "pos": 1,
                "display_name": "Photo après",
            },
            "label": {"type": "text", "pos": 2, "display_name": "Légende"},
        },
    },
    {
        "name": "site_content_hero_point",
        "display_name": "Point fort",
        "schema": {"text": {"type": "text", "pos": 0, "display_name": "Texte"}},
    },
    {
        "name": "site_content_trust_item",
        "display_name": "Repère de confiance",
        "schema": {
            "value": {"type": "text", "pos": 0, "display_name": "Chiffre / valeur"},
            "label": {"type": "text", "pos": 1, "display_name": "Libellé"},
        },
    },
]


def build_content_schemas(
    extra_section_images: dict[str, list[dict[str, str]]] | None = None,
) -> list[dict[str, Any]]:
    """Build the Storyblok component schemas for a template.

    ``extra_section_images`` maps a section suffix to the one-off image fields the template adds to
    that section (each ``{"field", "label"}``); ``None`` yields the shared schema unchanged.
    """
    extra = extra_section_images or {}
    sections: list[dict[str, Any]] = [
        _section_component(suffix, display_name, field_keys, extra.get(suffix))
        for suffix, display_name, field_keys in SECTION_DEFINITIONS
    ]
    return sections + _ITEM_BLOK_SCHEMAS


SITE_CONTENT_SCHEMAS: list[dict[str, Any]] = build_content_schemas()


def _items_to_bloks(items: Any, component: str, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    """Turn a list of flat item dicts into Storyblok item bloks (``_uid`` + ``component`` + keys)."""
    result: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        blok: dict[str, Any] = {"_uid": _uid(), "component": component}
        for key in keys:
            blok[key] = item.get(key, "")
        result.append(blok)
    return result


def _asset(url: Any, alt: str = "") -> dict[str, Any]:
    """Wrap an (external) image URL into a Storyblok ``asset`` object for an ``asset`` field.

    Scraped Google photo URLs are pushed as external-URL assets so the Visual Editor shows each
    one and the client can replace it with a real upload. An empty URL yields an empty asset field.
    """
    filename = url.strip() if isinstance(url, str) else ""
    # Every asset key must be present — Storyblok disables the "replace/edit asset" dialog when any is missing.
    return {
        "fieldtype": "asset",
        "filename": filename,
        "alt": alt,
        "copyright": "",
        "name": "",
        "title": "",
        "focus": "",
        "id": None,
    }


def _content_field_values(site_content: dict[str, Any]) -> dict[str, Any]:
    """Build every Storyblok field value from the flat ``SiteContent`` (scalars, assets, item bloks).

    Keyed by the flat ``SiteContent`` key; ``to_storyblok_site_content`` then distributes these across
    the section bloks (``SECTION_DEFINITIONS``). Palette is excluded — it lives on the page ``theme`` field.
    """
    return {
        "businessName": site_content.get("businessName", ""),
        "phone": site_content.get("phone", ""),
        "email": site_content.get("email", ""),
        "city": site_content.get("city", ""),
        "area": site_content.get("area", ""),
        "subtitle": site_content.get("subtitle", ""),
        "about": site_content.get("about", ""),
        "heroBadge": site_content.get("heroBadge", ""),
        "heroPoints": [
            {"_uid": _uid(), "component": "site_content_hero_point", "text": str(point)}
            for point in site_content.get("heroPoints") or []
            if isinstance(point, str) and point.strip()
        ],
        "ctaCallLabel": site_content.get("ctaCallLabel", ""),
        "ctaQuoteLabel": site_content.get("ctaQuoteLabel", ""),
        "trustItems": _items_to_bloks(site_content.get("trustItems"), "site_content_trust_item", ("value", "label")),
        "servicesHeading": site_content.get("servicesHeading", ""),
        "galleryHeading": site_content.get("galleryHeading", ""),
        "reviewsHeading": site_content.get("reviewsHeading", ""),
        "faqHeading": site_content.get("faqHeading", ""),
        "aboutHeading": site_content.get("aboutHeading", ""),
        "contactHeading": site_content.get("contactHeading", ""),
        "logo": _asset(site_content.get("logo", "")),
        "heroImage": _asset(site_content.get("heroImage", "")),
        "aboutImage": _asset(site_content.get("aboutImage", "")),
        "gallery": [
            _asset(item.get("url", ""), str(item.get("alt", "") or ""))
            for item in site_content.get("gallery") or []
            if isinstance(item, dict) and str(item.get("url", "")).strip()
        ],
        "services": [
            {
                "_uid": _uid(),
                "component": "site_content_service",
                "title": item.get("title", ""),
                "description": item.get("description", ""),
                "image": _asset(item.get("image", "")),
            }
            for item in site_content.get("services") or []
            if isinstance(item, dict)
        ],
        "teamHeading": site_content.get("teamHeading", ""),
        "teamMembers": [
            {
                "_uid": _uid(),
                "component": "site_content_team_member",
                "photo": _asset(item.get("photo", "")),
                "name": item.get("name", ""),
                "role": item.get("role", ""),
                "bio": item.get("bio", ""),
            }
            for item in site_content.get("teamMembers") or []
            if isinstance(item, dict)
        ],
        "portfolioHeading": site_content.get("portfolioHeading", ""),
        "portfolio": [
            {
                "_uid": _uid(),
                "component": "site_content_portfolio_item",
                "image": _asset(item.get("image", "")),
                "title": item.get("title", ""),
                "category": item.get("category", ""),
            }
            for item in site_content.get("portfolio") or []
            if isinstance(item, dict)
        ],
        # Storyblok ``number`` fields store their value as a STRING — an int fails the editor's
        # save/publish validation ("must be a string with numbers"), so stringify the rating.
        "reviews": [
            {
                "_uid": _uid(),
                "component": "site_content_review",
                "author": item.get("author", ""),
                "text": item.get("text", ""),
                "rating": str(item["rating"]) if isinstance(item.get("rating"), (int, float)) else "",
            }
            for item in site_content.get("reviews") or []
            if isinstance(item, dict)
        ],
        "faq": _items_to_bloks(site_content.get("faq"), "site_content_faq", ("question", "answer")),
        "openingHours": _items_to_bloks(site_content.get("openingHours"), "site_content_hours", ("day", "hours")),
        "beforeAfter": [
            {
                "_uid": _uid(),
                "component": "site_content_before_after",
                "before": _asset(item.get("before", "")),
                "after": _asset(item.get("after", "")),
                "label": item.get("label", ""),
            }
            for item in site_content.get("beforeAfter") or []
            if isinstance(item, dict)
        ],
        "social": _items_to_bloks(site_content.get("social"), "site_content_social", ("network", "url")),
    }


def to_storyblok_site_content(
    site_content: dict[str, Any],
    sections: list[str] | None = None,
    extra_section_images: dict[str, list[dict[str, str]]] | None = None,
) -> list[dict[str, Any]]:
    """Project a flat ``SiteContent`` into the Storyblok page ``body`` — a list of SECTION bloks.

    The page is split into small, focused sections (``section_hero``, ``section_about``…) instead of
    one 29-field blok, so the client's editor stays readable and each section is a short form. The flat
    ``SiteContent`` is unchanged; the palette lives on the page ``theme`` field, not in a section.

    Args:
        site_content: The flat ``SiteContent`` dict from a template's ``build_site_content``.
        sections: The section suffixes the template actually renders, in ``SECTION_DEFINITIONS`` order;
            ``None`` emits every section. Sections a template never renders are dropped so the client's
            editor shows no dead sections (safe: an unrendered section carries nothing to lose).

    Returns:
        The page ``body``: an ordered list of ``section_*`` bloks.
    """
    allowed: set[str] | None = set(sections) if sections is not None else None
    extra: dict[str, list[dict[str, str]]] = extra_section_images or {}
    raw_images = site_content.get("images")
    images: dict[str, Any] = raw_images if isinstance(raw_images, dict) else {}
    values = _content_field_values(site_content)
    body: list[dict[str, Any]] = []
    for suffix, _, field_keys in SECTION_DEFINITIONS:
        if allowed is not None and suffix not in allowed:
            continue
        section: dict[str, Any] = {"_uid": _uid(), "component": f"section_{suffix}"}
        for key in field_keys:
            section[key] = values[key]
        # This template's one-off image slots for this section (empty for most): pushed as asset
        # fields so the client edits them; the bridge flattens them back into ``SiteContent.images``.
        for extra_image in extra.get(suffix, []):
            section[extra_image["field"]] = _asset(images.get(extra_image["field"], ""))
        body.append(section)
    return body


def _clean_str(value: Any) -> str:
    """Return the value as a stripped string, or ``""`` when absent/not a string."""
    return value.strip() if isinstance(value, str) else ""


def _asset_url(value: Any) -> str:
    """Extract the URL from a Storyblok ``asset`` field (``{filename}``), or from a plain string.

    Handles both our external-URL push and the object returned after a client uploads a new image,
    and tolerates the pre-asset era where the field was a bare URL string.
    """
    if isinstance(value, dict):
        return _clean_str(value.get("filename"))
    return _clean_str(value)


def _blok_list(value: Any) -> list[dict[str, Any]]:
    """Return the value as a list of blok dicts, or an empty list."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _single_blok(value: Any) -> dict[str, Any]:
    """Return a single-blok field as a dict.

    Our API writes single bloks as plain dicts, but once the story is edited and
    published in Storyblok the field comes back as a LIST of bloks — handle both.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def _collect_content_fields(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Merge the section bloks' fields into one flat dict (keys are unique across sections).

    Accepts the sectioned page (``body: [section_hero, section_about, …]``), a bare section blok,
    or the legacy single ``site_content`` blok. Returns None when no content blok is present.
    """

    def _is_content(component: Any) -> bool:
        return component == "site_content" or (isinstance(component, str) and component.startswith("section_"))

    if _is_content(raw.get("component")):
        blocks: list[dict[str, Any]] = [raw]
    else:
        blocks = [blok for blok in _blok_list(raw.get("body")) if _is_content(blok.get("component"))]
    if not blocks:
        return None
    merged: dict[str, Any] = {}
    for blok in blocks:
        for key, value in blok.items():
            if key not in ("_uid", "component"):
                merged[key] = value
    return merged


def from_storyblok_site_content(raw: dict[str, Any]) -> dict[str, Any] | None:
    """Flatten a published Storyblok story back into the flat ``SiteContent`` shape.

    Inverse of ``to_storyblok_site_content`` and Python mirror of demo-host's
    ``StoryblokSiteContentBridge``: the section bloks are merged, nested item bloks lose their
    ``_uid``/``component``, asset fields are flattened to their URL (``filename``), and the palette is
    read from the page ``theme`` field. Used by the Storyblok publish webhook to sync client edits
    into ``demo_site.content_json`` (what the public site renders).

    Args:
        raw: The story ``content`` object fetched from the Storyblok CDN API.

    Returns:
        A flat ``SiteContent`` dict, or None when no content blok exists.
    """
    blok = _collect_content_fields(raw)
    if blok is None:
        return None
    # Palette lives on the page ``theme`` field now; fall back to a legacy in-content palette.
    palette = _single_blok(raw.get("theme")) or _single_blok(blok.get("palette"))

    reviews: list[dict[str, Any]] = []
    for item in _blok_list(blok.get("reviews")):
        entry: dict[str, Any] = {"author": _clean_str(item.get("author")), "text": _clean_str(item.get("text"))}
        rating_raw = item.get("rating")
        # Storyblok "number" fields may come back as strings — normalise to int.
        if isinstance(rating_raw, (int, float)):
            entry["rating"] = int(rating_raw)
        elif isinstance(rating_raw, str) and rating_raw.strip().isdigit():
            entry["rating"] = int(rating_raw.strip())
        reviews.append(entry)

    result: dict[str, Any] = {
        "businessName": _clean_str(blok.get("businessName")),
        "phone": _clean_str(blok.get("phone")),
        "email": _clean_str(blok.get("email")),
        "city": _clean_str(blok.get("city")),
        "area": _clean_str(blok.get("area")),
        "subtitle": _clean_str(blok.get("subtitle")),
        "about": _clean_str(blok.get("about")),
        "heroBadge": _clean_str(blok.get("heroBadge")),
        "heroPoints": [
            _clean_str(item.get("text")) for item in _blok_list(blok.get("heroPoints")) if _clean_str(item.get("text"))
        ],
        "ctaCallLabel": _clean_str(blok.get("ctaCallLabel")),
        "ctaQuoteLabel": _clean_str(blok.get("ctaQuoteLabel")),
        "trustItems": [
            {"value": _clean_str(item.get("value")), "label": _clean_str(item.get("label"))}
            for item in _blok_list(blok.get("trustItems"))
            if _clean_str(item.get("value")) or _clean_str(item.get("label"))
        ],
        "servicesHeading": _clean_str(blok.get("servicesHeading")),
        "galleryHeading": _clean_str(blok.get("galleryHeading")),
        "reviewsHeading": _clean_str(blok.get("reviewsHeading")),
        "faqHeading": _clean_str(blok.get("faqHeading")),
        "aboutHeading": _clean_str(blok.get("aboutHeading")),
        "contactHeading": _clean_str(blok.get("contactHeading")),
        "logo": _asset_url(blok.get("logo")),
        "heroImage": _asset_url(blok.get("heroImage")),
        "aboutImage": _asset_url(blok.get("aboutImage")),
        "palette": {
            "primary": _clean_str(palette.get("primary")),
            "secondary": _clean_str(palette.get("secondary")),
            "accent": _clean_str(palette.get("accent")),
        },
        "gallery": [
            {"url": _asset_url(item), "alt": _clean_str(item.get("alt"))}
            for item in _blok_list(blok.get("gallery"))
            if _asset_url(item)
        ],
        "services": [
            {
                "title": _clean_str(item.get("title")),
                "description": _clean_str(item.get("description")),
                "image": _asset_url(item.get("image")),
            }
            for item in _blok_list(blok.get("services"))
        ],
        "teamHeading": _clean_str(blok.get("teamHeading")),
        "teamMembers": [
            {
                "photo": _asset_url(item.get("photo")),
                "name": _clean_str(item.get("name")),
                "role": _clean_str(item.get("role")),
                "bio": _clean_str(item.get("bio")),
            }
            for item in _blok_list(blok.get("teamMembers"))
            if _asset_url(item.get("photo")) or _clean_str(item.get("name"))
        ],
        "portfolioHeading": _clean_str(blok.get("portfolioHeading")),
        "portfolio": [
            {
                "image": _asset_url(item.get("image")),
                "title": _clean_str(item.get("title")),
                "category": _clean_str(item.get("category")),
            }
            for item in _blok_list(blok.get("portfolio"))
            if _asset_url(item.get("image")) or _clean_str(item.get("title"))
        ],
        "reviews": reviews,
        "faq": [
            {"question": _clean_str(item.get("question")), "answer": _clean_str(item.get("answer"))}
            for item in _blok_list(blok.get("faq"))
        ],
        "openingHours": [
            {"day": _clean_str(item.get("day")), "hours": _clean_str(item.get("hours"))}
            for item in _blok_list(blok.get("openingHours"))
            if _clean_str(item.get("day")) or _clean_str(item.get("hours"))
        ],
        "beforeAfter": [
            {
                "before": _asset_url(item.get("before")),
                "after": _asset_url(item.get("after")),
                "label": _clean_str(item.get("label")),
            }
            for item in _blok_list(blok.get("beforeAfter"))
            if _asset_url(item.get("before")) or _asset_url(item.get("after"))
        ],
        "social": [
            {"network": _clean_str(item.get("network")), "url": _clean_str(item.get("url"))}
            for item in _blok_list(blok.get("social"))
            if _clean_str(item.get("url"))
        ],
    }
    # Per-template one-off image slots (barber's banner, food's collage, the mechanic FAQ photo…): any
    # section field holding an asset object that isn't one of the named single-asset keys is surfaced
    # under the generic map. Mirrors demo-host's ``StoryblokSiteContentBridge.collectImages`` — a one-off
    # image reusing a reserved field name (mechanic's ``faq``) is an asset dict here, so it lands in images
    # (the standard-key readers above already took the list/text fields, which are never asset dicts).
    images: dict[str, str] = {}
    for key, value in blok.items():
        if key in _NAMED_ASSET_KEYS or not isinstance(value, dict):
            continue
        url = _asset_url(value)
        if url:
            images[key] = url
    if images:
        result["images"] = images
    return result
