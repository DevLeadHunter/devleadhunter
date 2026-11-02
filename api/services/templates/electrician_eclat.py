"""
'electrician-eclat' demo template — self-contained registration.

Second electrician template (« Électricien Éclat »): white page, night-blue buttons and bands, one
accent colour used in touches only. No text ever sits on a photo and every frame has fixed
proportions, so a prospect's own phone pictures render well. Flat ``SiteContent`` path only; the
Nuxt layer is ``devleadhunter-template-electrician-eclat``.

Exposes the stable names consumed by the shared services (see ``registry``):

- ``TEMPLATE_META``       → catalogue entry
- ``build_site_content``  → flat ``SiteContent`` builder
- ``BODY_COMPONENTS`` / ``COMPONENT_SCHEMAS`` → none beyond the shared base
"""

from __future__ import annotations

import re
from typing import Any

from services.templates.site_content import (  # noqa: F401 — re-exported for the registry
    SITE_CONTENT_SCHEMAS,
    apply_real_trust_stats,
    fixed_trade_services,
    map_prospect_and_enrichment,
    to_storyblok_site_content,
)
from services.templates.visitor_data import TemplateVisitorData

TEMPLATE_ID: str = "electrician-eclat"

TEMPLATE_META: dict[str, object] = {
    "id": TEMPLATE_ID,
    "name": "Électricien Éclat",
    "description": (
        "Vitrine claire et sobre pour électricien : en-tête en deux colonnes avec photo découpée, "
        "repères de confiance, six prestations en photo, déroulé d'une intervention, réalisations "
        "à faire défiler, questions fréquentes, formulaire et carte. Fond blanc, boutons bleu nuit, "
        "la couleur du logo en touches. Pensée pour rester propre avec les photos de chantier du "
        "prospect comme sans aucune photo."
    ),
    "preview_image_url": None,
    "category": "artisan",
    "trades": ["electricien", "electrician", "electricite"],
    # Only ``primary`` themes the layer: it is the accent, shown in touches (the city in the title,
    # icons, numbers). Buttons and dark bands stay night blue so any logo colour remains readable.
    "default_theme": {
        "primary": "#F59E0B",
        "secondary": "#0B1B2E",
        "accent": "#F59E0B",
    },
    "color_roles": {"action": "primary"},
    "brand_color_key": "primary",
}

VISITOR_DATA: TemplateVisitorData = TemplateVisitorData(
    has_contact_form=True,
    has_google_fonts=True,
    has_google_map=True,
)

# Shared base bloks only (flat SiteContent).
BODY_COMPONENTS: list[str] = []
COMPONENT_SCHEMAS: list[dict[str, Any]] = []

# Sections this template renders, in page order — drives the client's Storyblok editor so it shows no dead sections.
USED_SECTIONS: list[str] = [
    "hero",
    "trust",
    "services",
    "about",
    "method",
    "gallery",
    "reviews",
    "faq",
    "contact",
]

# One-off photos this template renders beyond hero/about, exposed as dedicated Storyblok asset fields
# grouped in the section where they appear, editable via ``SiteContent.images``.
EXTRA_SECTION_IMAGES: dict[str, list[dict[str, str]]] = {
    "hero": [
        {"field": "heroSecondary", "label": "Deuxième photo de l'en-tête (vide : première photo des réalisations)"}
    ],
    "contact": [{"field": "ctaBackground", "label": "Photo de la bannière « Une panne ou un projet ? »"}],
}

# Per-section field overrides (see registry.to_storyblok_site_content). Each list REPLACES the shared
# default for that section in this template's editor.
SECTION_FIELDS: dict[str, list[str]] = {
    # Hero: the editable H1 replaces ``ctaCallLabel``, which this layer never renders (its call
    # button shows the phone number itself).
    "hero": ["heroBadge", "heroTitle", "subtitle", "heroImage", "heroPoints", "ctaQuoteLabel"],
    "services": ["servicesHeading", "servicesLead", "services"],
    # Contact: the shared fields plus the section intro and the copy of the banner above it.
    "contact": [
        "contactHeading",
        "contactLead",
        "ctaTitle",
        "ctaLead",
        "businessName",
        "phone",
        "email",
        "city",
        "area",
        "professionalLicenseLabel",
        "professionalLicenseNumber",
        "logo",
        "openingHours",
        "social",
    ],
}

_SITE_ABOUT_DEFAULT: str = "Électricien pour vos dépannages, vos installations et vos mises aux normes."

# Service grid and FAQ — EXACT mirror of the layer defaults
# (devleadhunter-template-electrician-eclat app/content/eclatDefaults.ts).
ECLAT_SERVICES: list[dict[str, str]] = [
    {
        "title": "Dépannage électrique",
        "description": "Panne, court-circuit, disjoncteur qui saute : diagnostic et remise en service.",
    },
    {
        "title": "Mise aux normes",
        "description": "Remise à niveau de votre installation selon les normes en vigueur.",
    },
    {
        "title": "Tableau électrique",
        "description": "Remplacement et modernisation de votre tableau et de vos protections.",
    },
    {
        "title": "Installation et rénovation",
        "description": "Neuf ou rénovation : réseau complet, prises, points lumineux.",
    },
    {
        "title": "Éclairage",
        "description": "Éclairage intérieur et extérieur, points lumineux et interrupteurs.",
    },
    {
        "title": "Prises et circuits",
        "description": "Ajout de prises et de circuits dédiés : four, plaques de cuisson, chauffe-eau.",
    },
]

ECLAT_FAQ: list[dict[str, str]] = [
    {
        "question": "Comment demander un devis ?",
        "answer": "Par téléphone ou avec le formulaire de contact : décrivez les travaux et l'adresse du chantier.",
    },
    {
        "question": "Dans quel secteur intervenez-vous ?",
        "answer": (
            "Le secteur d'intervention est indiqué dans la partie contact. Un doute sur votre commune ? "
            "Le plus simple est d'appeler."
        ),
    },
    {
        "question": "Que préparer avant d'appeler ?",
        "answer": (
            "Le type de travaux, l'adresse et vos disponibilités. Une photo de l'installation aide aussi à "
            "préparer le devis."
        ),
    },
]

# Editorial copy pre-filled into the CMS so the client sees (and edits) his real texts — EXACT mirror
# of the layer defaults, none of them promising a price, a delay or a guarantee. The "avis" trust slot is
# a placeholder: ``apply_real_trust_stats`` swaps in the real Google rating, or drops it without one.
_EDITORIAL_DEFAULTS: dict[str, Any] = {
    "heroBadge": "Artisan électricien",
    "heroPoints": [],
    "ctaQuoteLabel": "Demander un devis",
    "trustItems": [
        {"value": "4,9/5", "label": "Avis clients"},
        {"value": "Local", "label": "Artisan de proximité"},
        {"value": "Devis", "label": "Sur demande"},
    ],
    "servicesHeading": "Tout ce qu'il faut pour une installation sûre",
    "servicesLead": "Du simple dépannage à la rénovation complète de votre installation électrique.",
    "aboutHeading": "Qui intervient chez vous",
    "stepsHeading": "Comment se passe une intervention",
    "galleryHeading": "Quelques chantiers en photos",
    "reviewsHeading": "Ce que disent nos clients",
    "faqHeading": "Questions fréquentes",
    "ctaTitle": "Une panne ou un projet ?",
    "ctaLead": "Décrivez votre besoin par téléphone ou avec le formulaire ci-dessous.",
    "contactHeading": "Parlons de votre projet",
    "contactLead": "Par téléphone, par e-mail ou avec le formulaire.",
}

_DEFAULT_STEPS: list[dict[str, str]] = [
    {"title": "Premier contact", "description": "Vous décrivez votre besoin par téléphone ou par message."},
    {"title": "Visite et devis", "description": "Passage sur place si besoin, puis devis détaillé."},
    {"title": "Travaux", "description": "Réalisés à la date convenue ensemble."},
    {"title": "Contrôle final", "description": "L'installation est vérifiée avant le départ."},
]


def _unsplash_photo(photo_id: str, width: int) -> str:
    """Unsplash URL of a photo cropped to a width — same shape as the layer's ``unsplashPhoto``."""
    return f"https://images.unsplash.com/{photo_id}?auto=format&fit=crop&w={width}&q=80"


# Photos seeded into the CMS so each one is a dedicated, client-editable field — EXACT mirror of the
# layer's ``ECLAT_DEFAULT_IMAGES`` (hero, about and gallery live in ``default_images.py``).
_DEFAULT_SERVICE_IMAGES: list[str] = [
    _unsplash_photo("photo-1758101755915-462eddc23f57", 900),
    _unsplash_photo("photo-1751486289947-4f5f5961b3aa", 900),
    _unsplash_photo("photo-1544724569-5f546fd6f2b5", 900),
    _unsplash_photo("photo-1665242043190-0ef29390d289", 900),
    _unsplash_photo("photo-1782457696919-08e1aa4f7427", 900),
    _unsplash_photo("photo-1508920291026-c344bbfca1ab", 900),
]
_DEFAULT_HERO_SECONDARY: str = _unsplash_photo("photo-1682345262055-8f95f3c513ea", 900)
_DEFAULT_CTA_BACKGROUND: str = _unsplash_photo("photo-1547393947-a6a221f74e59", 1400)


def _place_phrase(area: str) -> str:
    """Grammatical location phrase (« à Nantes » / « dans votre secteur »)."""
    return f"à {area}" if area and area != "votre secteur" else "dans votre secteur"


def default_subtitle(area: str) -> str:
    """Electrician default hero subtitle when the prospect has no description.

    Args:
        area: Service area / city label.

    Returns:
        The subtitle, the template's default services where the business works.
    """
    return f"Dépannage, mise aux normes, tableau électrique, installation et rénovation {_place_phrase(area)}."


def _hero_title(city: str | None) -> str:
    """Default H1, ending with the city the layer highlights (« à Le Mont » contracts to « au Mont »).

    Args:
        city: The prospect's city, or None when unknown.

    Returns:
        The title, without a city when none is known.
    """
    if not city:
        return "Votre électricien"
    title = f"Votre électricien à {city}"
    title = re.sub(r"\bà Le (?=[A-ZÀ-Ý])", "au ", title)
    return re.sub(r"\bà Les (?=[A-ZÀ-Ý])", "aux ", title)


def build_site_content(
    *,
    business_name: str,
    phone: str | None,
    email: str | None,
    city: str | None,
    area: str,
    subtitle: str,
    palette: dict[str, str],
    enrichment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the flat ``SiteContent`` for this template.

    Prospect fields + enrichment map through the shared helper; the service grid, FAQ, method steps
    and editorial copy are this template's own defaults, pre-filled so the client edits real texts.
    See ``site_content.py``.
    """
    site = map_prospect_and_enrichment(
        business_name=business_name,
        phone=phone,
        email=email,
        city=city,
        area=area,
        subtitle=subtitle,
        palette=palette,
        enrichment=enrichment,
        about_default=_SITE_ABOUT_DEFAULT,
    )
    if not city:
        # The shared mapper falls back to the « votre secteur » placeholder, which this layer would
        # print as a city (« Basé à votre secteur »): an unknown city stays empty here.
        site["city"] = ""
    site["services"] = fixed_trade_services(ECLAT_SERVICES)
    for index, service in enumerate(site["services"]):
        service["image"] = _DEFAULT_SERVICE_IMAGES[index % len(_DEFAULT_SERVICE_IMAGES)]
    # Fresh copies so the shared module-level defaults are never mutated across generations.
    site["faq"] = [dict(item) for item in ECLAT_FAQ]
    site.update(_EDITORIAL_DEFAULTS)
    site["heroPoints"] = list(_EDITORIAL_DEFAULTS["heroPoints"])
    site["heroTitle"] = _hero_title(city)
    site["steps"] = [dict(step) for step in _DEFAULT_STEPS]
    apply_real_trust_stats(site, enrichment, unrated_trust_item=None)
    site["images"] = {"ctaBackground": _DEFAULT_CTA_BACKGROUND}
    # The small photo over the hero is left empty when the prospect has gallery photos: the layer then
    # shows his first gallery photo, so it follows any reordering (live preview included) instead of
    # freezing a copy here. Without gallery photos the template's own photo is seeded.
    if not site.get("gallery"):
        site["images"]["heroSecondary"] = _DEFAULT_HERO_SECONDARY
    return site
