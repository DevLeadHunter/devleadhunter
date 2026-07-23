"""Shared building blocks for the flat ``SiteContent`` path (Phase 4b).

Every template that opts into ``SiteContent`` (exposes ``build_site_content``) reuses the
same, template-AGNOSTIC pieces defined here:

- ``map_prospect_and_enrichment`` — maps the prospect fields + the enrichment dict into the
  common ``SiteContent`` fields (identity, contact, media, palette, reviews, opening hours).
- ``SITE_CONTENT_SCHEMAS`` — the native Storyblok blok schemas for ``site_content`` + its
  nested item bloks, so the Visual Editor can edit every field.
- ``to_storyblok_site_content`` — wraps a flat ``SiteContent`` into those native bloks.
- ``from_storyblok_site_content`` — the inverse bridge (published story → flat ``SiteContent``),
  used by the Storyblok webhook to sync client edits back into ``demo_site.content_json``
  (the public site renders content_json, not Storyblok). Python mirror of demo-host's
  ``storyblokSiteContentToSiteContent.ts``.

A template's own ``build_site_content`` calls ``map_prospect_and_enrichment`` and adds its
editorial ``services`` / ``faq`` (design copy, per trade). The demo-host layer supplies the
remaining boilerplate (section headings, etc.).
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

# Generic, per-trade editorial defaults. A template's build_site_content may pass these
# (or its own) so the services/FAQ sections render and stay editable in Storyblok.
PLUMBER_SERVICES: list[dict[str, str]] = [
    {"title": "Dépannage & urgences", "description": "Fuite, engorgement, panne de chauffe-eau : intervention rapide 7j/7."},
    {"title": "Recherche de fuite", "description": "Détection précise sans casse inutile, puis réparation durable."},
    {"title": "Installation sanitaire", "description": "Salle de bain, cuisine, WC : pose complète et soignée."},
    {"title": "Chauffe-eau & chauffage", "description": "Installation, remplacement et entretien de vos équipements."},
    {"title": "Rénovation de salle de bain", "description": "Modernisation complète de vos pièces d'eau, clé en main."},
    {"title": "Débouchage de canalisation", "description": "Curage et débouchage rapide, sans dégât."},
]
PLUMBER_FAQ: list[dict[str, str]] = [
    {"question": "Intervenez-vous en urgence le week-end ?", "answer": "Oui, nous intervenons 7j/7 pour les urgences. Appelez, on vous rappelle rapidement."},
    {"question": "Le devis est-il gratuit ?", "answer": "Le devis est toujours gratuit et sans engagement, remis avant toute intervention."},
    {"question": "Quelles zones couvrez-vous ?", "answer": "Votre ville et les communes voisines. Appelez pour vérifier, nous nous déplaçons souvent au-delà."},
    {"question": "Quels moyens de paiement acceptez-vous ?", "answer": "Carte bancaire, chèque et virement, avec facture détaillée."},
    {"question": "Proposez-vous une garantie sur vos travaux ?", "answer": "Oui, nos installations sont couvertes par la garantie décennale."},
]
ELECTRICIAN_SERVICES: list[dict[str, str]] = [
    {"title": "Dépannage électrique", "description": "Panne, court-circuit, disjoncteur qui saute : diagnostic et remise en service rapides."},
    {"title": "Mise aux normes", "description": "Remise à niveau de votre installation (NF C 15-100) et attestation Consuel."},
    {"title": "Tableau électrique", "description": "Remplacement et modernisation de votre tableau et de vos protections."},
    {"title": "Installation & rénovation", "description": "Neuf ou rénovation : réseau complet, prises, points lumineux."},
    {"title": "Éclairage & domotique", "description": "Éclairage intérieur/extérieur, interrupteurs connectés, domotique."},
    {"title": "Borne de recharge", "description": "Installation de bornes de recharge pour véhicule électrique."},
]
ELECTRICIAN_FAQ: list[dict[str, str]] = [
    {"question": "Intervenez-vous en urgence ?", "answer": "Oui, pour toute panne électrique nous intervenons au plus vite, 7j/7."},
    {"question": "Le devis est-il gratuit ?", "answer": "Le devis est gratuit et sans engagement, remis avant les travaux."},
    {"question": "Délivrez-vous une attestation Consuel ?", "answer": "Oui, pour toute installation neuve ou mise aux normes soumise au Consuel."},
    {"question": "Quelles zones couvrez-vous ?", "answer": "Votre ville et ses alentours. Appelez pour vérifier votre commune."},
    {"question": "Vos travaux sont-ils garantis ?", "answer": "Oui, nos installations sont conformes et couvertes par la garantie décennale."},
]


def _uid() -> str:
    """Return a fresh Storyblok ``_uid``."""
    return str(uuid.uuid4())


def map_prospect_and_enrichment(
    *,
    business_name: str,
    phone: Optional[str],
    email: Optional[str],
    city: Optional[str],
    area: str,
    subtitle: str,
    palette: dict[str, str],
    enrichment: Optional[dict[str, Any]] = None,
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

    photos: list[str] = [p for p in enrichment.get("photos", []) if isinstance(p, str) and p.strip()]
    raw_reviews: list[dict] = [r for r in enrichment.get("reviews", []) if isinstance(r, dict)]
    raw_hours: list[dict] = [h for h in enrichment.get("opening_hours", []) if isinstance(h, dict)]
    description = enrichment.get("description")

    reviews: list[dict[str, Any]] = []
    for review in raw_reviews:
        text = str(review.get("text", "")).strip()
        if not text:
            continue
        entry: dict[str, Any] = {"author": str(review.get("author", "")).strip() or "Client", "text": text}
        rating_value = review.get("rating")
        if isinstance(rating_value, (int, float)):
            entry["rating"] = int(rating_value)
        reviews.append(entry)

    opening_hours: list[dict[str, str]] = []
    for row in raw_hours:
        day = str(row.get("day", "")).strip()
        hours = str(row.get("hours", "")).strip()
        if not day and not hours:
            continue
        opening_hours.append({"day": day, "hours": hours})

    raw_social = enrichment.get("social_links") or {}
    social: list[dict[str, str]] = [
        {"network": str(network), "url": str(url)}
        for network, url in (raw_social.items() if isinstance(raw_social, dict) else [])
        if isinstance(url, str) and url.strip()
    ]

    about = description.strip() if isinstance(description, str) and description.strip() else about_default
    site_city = city or area
    area_label = f"{area} et ses alentours" if city else ""

    logo_raw = enrichment.get("logo_url")
    logo = logo_raw.strip() if isinstance(logo_raw, str) and logo_raw.strip() else ""

    return {
        "businessName": business_name,
        "phone": phone or "",
        "email": email or "",
        "city": site_city,
        "area": area_label,
        "subtitle": subtitle,
        "about": about,
        "logo": logo,
        "heroImage": photos[0] if len(photos) > 0 else "",
        "aboutImage": photos[1] if len(photos) > 1 else "",
        "gallery": [{"url": url, "alt": ""} for url in photos[2:]],
        "palette": {
            "primary": palette.get("primary", ""),
            "secondary": palette.get("secondary", ""),
            "accent": palette.get("accent", ""),
        },
        "reviews": reviews,
        "openingHours": opening_hours,
        "social": social,
    }


# Native Storyblok blok schemas for the ``site_content`` representation. The flat SiteContent
# expressed as editable bloks so the Visual Editor reaches every field: scalars as text/textarea,
# image URLs as text (external URLs), arrays as nested bloks. Template-agnostic — registered once.
# Field labels/descriptions are in FRENCH: they are what the CLIENT sees in his
# Storyblok editor — the editing experience is part of the product promise.
SITE_CONTENT_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "site_content",
        "display_name": "Contenu du site",
        "schema": {
            # ── Identité & contact ────────────────────────────────────────
            "businessName": {"type": "text", "pos": 0, "display_name": "Nom de l'entreprise"},
            "phone": {"type": "text", "pos": 1, "display_name": "Téléphone"},
            "email": {"type": "text", "pos": 2, "display_name": "Email de contact"},
            "city": {"type": "text", "pos": 3, "display_name": "Ville"},
            "area": {"type": "text", "pos": 4, "display_name": "Secteur d'intervention", "description": "Ex : « Lyon et ses alentours »"},
            # ── Textes principaux ─────────────────────────────────────────
            "subtitle": {"type": "textarea", "pos": 5, "display_name": "Phrase d'accroche", "description": "Le texte principal en haut du site"},
            "about": {"type": "textarea", "pos": 6, "display_name": "À propos", "description": "Votre histoire, votre façon de travailler"},
            # ── Copie éditoriale (vide = texte par défaut du site) ────────
            "heroBadge": {"type": "text", "pos": 7, "display_name": "Badge d'en-tête", "description": "Petit libellé au-dessus du titre (ex : « Artisan plombier »)"},
            "heroPoints": {"type": "bloks", "pos": 8, "display_name": "Points forts d'en-tête", "description": "3 arguments courts sous l'accroche", "restrict_components": True, "component_whitelist": ["site_content_hero_point"]},
            "ctaCallLabel": {"type": "text", "pos": 9, "display_name": "Bouton « appeler »", "description": "Texte du bouton d'appel"},
            "ctaQuoteLabel": {"type": "text", "pos": 10, "display_name": "Bouton « devis »", "description": "Texte du bouton de demande de devis"},
            "trustItems": {"type": "bloks", "pos": 11, "display_name": "Repères de confiance", "description": "Chiffres/garanties affichés sous l'en-tête (ex : 7j/7, Devis 0 €)", "restrict_components": True, "component_whitelist": ["site_content_trust_item"]},
            "servicesHeading": {"type": "text", "pos": 12, "display_name": "Titre de la section Services"},
            "galleryHeading": {"type": "text", "pos": 13, "display_name": "Titre de la section Photos"},
            "reviewsHeading": {"type": "text", "pos": 14, "display_name": "Titre de la section Avis"},
            "faqHeading": {"type": "text", "pos": 15, "display_name": "Titre de la section Questions"},
            "aboutHeading": {"type": "text", "pos": 16, "display_name": "Titre de la section À propos"},
            "contactHeading": {"type": "text", "pos": 17, "display_name": "Titre de la section Contact"},
            # ── Médias ────────────────────────────────────────────────────
            "logo": {"type": "text", "pos": 18, "display_name": "Logo (URL)", "description": "Logo de l'entreprise — utilisé comme favicon du site"},
            "heroImage": {"type": "text", "pos": 19, "display_name": "Photo principale (URL)"},
            "aboutImage": {"type": "text", "pos": 20, "display_name": "Photo « à propos » (URL)"},
            "gallery": {"type": "bloks", "pos": 21, "display_name": "Galerie photos", "restrict_components": True, "component_whitelist": ["site_content_gallery_item"]},
            "beforeAfter": {"type": "bloks", "pos": 22, "display_name": "Réalisations avant/après", "description": "Paires de photos avant travaux / après travaux", "restrict_components": True, "component_whitelist": ["site_content_before_after"]},
            # ── Contenu structuré ─────────────────────────────────────────
            "services": {"type": "bloks", "pos": 23, "display_name": "Services", "restrict_components": True, "component_whitelist": ["site_content_service"]},
            "reviews": {"type": "bloks", "pos": 24, "display_name": "Avis clients", "restrict_components": True, "component_whitelist": ["site_content_review"]},
            "faq": {"type": "bloks", "pos": 25, "display_name": "Questions fréquentes", "restrict_components": True, "component_whitelist": ["site_content_faq"]},
            "openingHours": {"type": "bloks", "pos": 26, "display_name": "Horaires d'ouverture", "restrict_components": True, "component_whitelist": ["site_content_hours"]},
            "social": {"type": "bloks", "pos": 27, "display_name": "Réseaux sociaux", "description": "Liens Facebook, Instagram… affichés en pied de page", "restrict_components": True, "component_whitelist": ["site_content_social"]},
            # ── Design ────────────────────────────────────────────────────
            "palette": {"type": "blok", "pos": 28, "display_name": "Couleurs du site", "restrict_components": True, "component_whitelist": ["theme_palette"], "maximum": 1},
        },
    },
    {"name": "site_content_social", "display_name": "Réseau social", "schema": {"network": {"type": "text", "pos": 0, "display_name": "Réseau", "description": "facebook, instagram, linkedin, tiktok, youtube, twitter"}, "url": {"type": "text", "pos": 1, "display_name": "URL du profil"}}},
    {"name": "site_content_service", "display_name": "Service", "schema": {"title": {"type": "text", "pos": 0, "display_name": "Titre"}, "description": {"type": "textarea", "pos": 1, "display_name": "Description"}}},
    {"name": "site_content_review", "display_name": "Avis client", "schema": {"author": {"type": "text", "pos": 0, "display_name": "Auteur"}, "rating": {"type": "number", "pos": 1, "display_name": "Note (0-5)"}, "text": {"type": "textarea", "pos": 2, "display_name": "Texte de l'avis"}}},
    {"name": "site_content_faq", "display_name": "Question fréquente", "schema": {"question": {"type": "text", "pos": 0, "display_name": "Question"}, "answer": {"type": "textarea", "pos": 1, "display_name": "Réponse"}}},
    {"name": "site_content_hours", "display_name": "Horaire", "schema": {"day": {"type": "text", "pos": 0, "display_name": "Jour(s)"}, "hours": {"type": "text", "pos": 1, "display_name": "Heures"}}},
    {"name": "site_content_gallery_item", "display_name": "Photo de galerie", "schema": {"url": {"type": "text", "pos": 0, "display_name": "URL de la photo"}, "alt": {"type": "text", "pos": 1, "display_name": "Description (référencement)"}}},
    {"name": "site_content_before_after", "display_name": "Avant / après", "schema": {"before": {"type": "text", "pos": 0, "display_name": "Photo avant (URL)"}, "after": {"type": "text", "pos": 1, "display_name": "Photo après (URL)"}, "label": {"type": "text", "pos": 2, "display_name": "Légende"}}},
    {"name": "site_content_hero_point", "display_name": "Point fort", "schema": {"text": {"type": "text", "pos": 0, "display_name": "Texte"}}},
    {"name": "site_content_trust_item", "display_name": "Repère de confiance", "schema": {"value": {"type": "text", "pos": 0, "display_name": "Chiffre / valeur"}, "label": {"type": "text", "pos": 1, "display_name": "Libellé"}}},
]


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


def to_storyblok_site_content(site_content: dict[str, Any]) -> dict[str, Any]:
    """Wrap a flat ``SiteContent`` into the native Storyblok ``site_content`` blok.

    Scalars stay as-is; image URLs stay text; each array becomes a list of nested item bloks;
    the palette becomes a ``theme_palette`` blok. Every field is editable in the Visual Editor.
    Template-agnostic (the SiteContent shape is shared).

    Args:
        site_content: The flat ``SiteContent`` dict from a template's ``build_site_content``.

    Returns:
        A ``site_content`` blok ready to drop into the page ``body``.
    """
    palette_raw = site_content.get("palette") or {}
    palette: dict[str, Any] = palette_raw if isinstance(palette_raw, dict) else {}

    return {
        "_uid": _uid(),
        "component": "site_content",
        "businessName": site_content.get("businessName", ""),
        "phone": site_content.get("phone", ""),
        "email": site_content.get("email", ""),
        "city": site_content.get("city", ""),
        "area": site_content.get("area", ""),
        "subtitle": site_content.get("subtitle", ""),
        "about": site_content.get("about", ""),
        # Editorial copy (empty = template default)
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
        "logo": site_content.get("logo", ""),
        "heroImage": site_content.get("heroImage", ""),
        "aboutImage": site_content.get("aboutImage", ""),
        "palette": {
            "_uid": _uid(),
            "component": "theme_palette",
            "primary": str(palette.get("primary", "")),
            "secondary": str(palette.get("secondary", "")),
            "accent": str(palette.get("accent", "")),
        },
        "gallery": _items_to_bloks(site_content.get("gallery"), "site_content_gallery_item", ("url", "alt")),
        "services": _items_to_bloks(site_content.get("services"), "site_content_service", ("title", "description")),
        "reviews": _items_to_bloks(site_content.get("reviews"), "site_content_review", ("author", "rating", "text")),
        "faq": _items_to_bloks(site_content.get("faq"), "site_content_faq", ("question", "answer")),
        "openingHours": _items_to_bloks(site_content.get("openingHours"), "site_content_hours", ("day", "hours")),
        "beforeAfter": _items_to_bloks(
            site_content.get("beforeAfter"), "site_content_before_after", ("before", "after", "label")
        ),
        "social": _items_to_bloks(site_content.get("social"), "site_content_social", ("network", "url")),
    }


def _clean_str(value: Any) -> str:
    """Return the value as a stripped string, or ``""`` when absent/not a string."""
    return value.strip() if isinstance(value, str) else ""


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


def find_site_content_blok(raw: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Locate the ``site_content`` blok inside a resolved story content object.

    Handles both shapes: page-wrapped (``{component: 'page', body: [site_content]}``)
    and the bare ``site_content`` blok itself.

    Args:
        raw: The story content (from the CDN API or content_json).

    Returns:
        The ``site_content`` blok, or None when absent.
    """
    if raw.get("component") == "site_content":
        return raw
    for blok in _blok_list(raw.get("body")):
        if blok.get("component") == "site_content":
            return blok
    return None


def from_storyblok_site_content(raw: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Flatten a published Storyblok story back into the flat ``SiteContent`` shape.

    Inverse of ``to_storyblok_site_content`` and Python mirror of demo-host's
    ``storyblokSiteContentToSiteContent.ts``: nested item bloks lose their
    ``_uid``/``component``, the palette is read from the nested ``theme_palette``
    blok, images stay plain URL strings. Used by the Storyblok publish webhook to
    sync client edits into ``demo_site.content_json`` (what the public site renders).

    Args:
        raw: The story ``content`` object fetched from the Storyblok CDN API.

    Returns:
        A flat ``SiteContent`` dict, or None when no ``site_content`` blok exists.
    """
    blok = find_site_content_blok(raw)
    if blok is None:
        return None
    palette = _single_blok(blok.get("palette"))

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

    return {
        "businessName": _clean_str(blok.get("businessName")),
        "phone": _clean_str(blok.get("phone")),
        "email": _clean_str(blok.get("email")),
        "city": _clean_str(blok.get("city")),
        "area": _clean_str(blok.get("area")),
        "subtitle": _clean_str(blok.get("subtitle")),
        "about": _clean_str(blok.get("about")),
        "heroBadge": _clean_str(blok.get("heroBadge")),
        "heroPoints": [
            _clean_str(item.get("text"))
            for item in _blok_list(blok.get("heroPoints"))
            if _clean_str(item.get("text"))
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
        "logo": _clean_str(blok.get("logo")),
        "heroImage": _clean_str(blok.get("heroImage")),
        "aboutImage": _clean_str(blok.get("aboutImage")),
        "palette": {
            "primary": _clean_str(palette.get("primary")),
            "secondary": _clean_str(palette.get("secondary")),
            "accent": _clean_str(palette.get("accent")),
        },
        "gallery": [
            {"url": _clean_str(item.get("url")), "alt": _clean_str(item.get("alt"))}
            for item in _blok_list(blok.get("gallery"))
            if _clean_str(item.get("url"))
        ],
        "services": [
            {"title": _clean_str(item.get("title")), "description": _clean_str(item.get("description"))}
            for item in _blok_list(blok.get("services"))
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
                "before": _clean_str(item.get("before")),
                "after": _clean_str(item.get("after")),
                "label": _clean_str(item.get("label")),
            }
            for item in _blok_list(blok.get("beforeAfter"))
            if _clean_str(item.get("before")) or _clean_str(item.get("after"))
        ],
        "social": [
            {"network": _clean_str(item.get("network")), "url": _clean_str(item.get("url"))}
            for item in _blok_list(blok.get("social"))
            if _clean_str(item.get("url"))
        ],
    }
