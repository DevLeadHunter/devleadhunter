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
    "hero": [{"field": "heroSecondary", "label": "Deuxième photo de l'en-tête"}],
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

_SITE_ABOUT_DEFAULT: str = (
    "Électricien qualifié à votre service pour vos dépannages, installations et mises aux "
    "normes. Travail conforme, soigné et sécurisé, avec un diagnostic clair et un prix juste."
)

# Service grid and FAQ — EXACT mirror of the layer defaults
# (devleadhunter-template-electrician-eclat app/content/eclatDefaults.ts).
ECLAT_SERVICES: list[dict[str, str]] = [
    {
        "title": "Dépannage électrique",
        "description": "Panne, court-circuit, disjoncteur qui saute : diagnostic et remise en service rapides.",
    },
    {
        "title": "Mise aux normes",
        "description": "Remise à niveau complète de votre installation, aux normes en vigueur, attestation à l'appui.",
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
        "title": "Éclairage et domotique",
        "description": "Éclairage intérieur et extérieur, interrupteurs connectés, domotique.",
    },
    {"title": "Borne de recharge", "description": "Installation de bornes de recharge pour véhicule électrique."},
]

ECLAT_FAQ: list[dict[str, str]] = [
    {
        "question": "Intervenez-vous en urgence ?",
        "answer": "Oui, pour toute panne électrique nous intervenons au plus vite, 7j/7.",
    },
    {
        "question": "Le devis est-il gratuit ?",
        "answer": "Le devis est gratuit et sans engagement, remis avant les travaux.",
    },
    {
        "question": "Délivrez-vous une attestation de conformité ?",
        "answer": "Oui, chaque installation neuve ou mise aux normes est livrée avec son attestation.",
    },
    {
        "question": "Quelles zones couvrez-vous ?",
        "answer": (
            "Nous intervenons dans notre commune et celles des alentours. Un doute sur la vôtre ? Appelez-nous."
        ),
    },
    {
        "question": "Vos travaux sont-ils garantis ?",
        "answer": "Oui, nos installations sont conformes et couvertes par notre assurance professionnelle.",
    },
]

# Editorial copy pre-filled into the CMS so the client sees (and edits) his real texts — EXACT mirror
# of the layer defaults. The "avis" trust slot is a placeholder: ``apply_real_trust_stats`` swaps in
# the real Google rating when one exists, and a neutral "Devis gratuit" claim otherwise.
_EDITORIAL_DEFAULTS: dict[str, Any] = {
    "heroBadge": "Artisan électricien",
    "heroPoints": ["Devis gratuit", "Intervention rapide", "Travail garanti"],
    "ctaQuoteLabel": "Demander un devis",
    "trustItems": [
        {"value": "7j/7", "label": "Dépannage et urgences"},
        {"value": "4,9/5", "label": "Avis clients"},
        {"value": "Travail garanti", "label": "Interventions assurées"},
        {"value": "100% conforme", "label": "Installations aux normes"},
    ],
    "servicesHeading": "Tout ce qu'il faut pour une installation sûre",
    "servicesLead": "Du simple dépannage à la rénovation complète de votre installation électrique.",
    "aboutHeading": "Un travail soigné, du devis au dernier test",
    "stepsHeading": "Comment se passe une intervention",
    "galleryHeading": "Nos chantiers récents",
    "reviewsHeading": "Ce que disent nos clients",
    "faqHeading": "Questions fréquentes",
    "ctaTitle": "Une panne ou un projet ?",
    "ctaLead": "Décrivez votre besoin, vous recevez une réponse rapide et un devis gratuit.",
    "contactHeading": "Parlons de votre projet",
    "contactLead": "Par téléphone, par e-mail ou avec le formulaire : réponse rapide et devis gratuit.",
}

_DEFAULT_STEPS: list[dict[str, str]] = [
    {"title": "Premier contact", "description": "Vous décrivez votre besoin par téléphone ou par message."},
    {"title": "Visite et devis", "description": "Passage sur place, puis devis gratuit et détaillé."},
    {"title": "Travaux", "description": "Réalisés à la date convenue, chantier laissé propre."},
    {"title": "Contrôle final", "description": "Chaque circuit est testé et expliqué avant le départ."},
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
    _unsplash_photo("photo-1653665674648-7cc7fa657547", 900),
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
        The subtitle, in two short sentences.
    """
    return (
        "Dépannage, mise aux normes, rénovation et borne de recharge. "
        f"Un travail propre, sécurisé et garanti {_place_phrase(area)}."
    )


def _hero_title(city: str | None) -> str:
    """Default H1, ending with the city the layer highlights (« à Le Mont » contracts to « au Mont »).

    Args:
        city: The prospect's city, or None when unknown.

    Returns:
        The title, without a city when none is known.
    """
    if not city:
        return "Votre électricien de confiance"
    title = f"Votre électricien de confiance à {city}"
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
    apply_real_trust_stats(site, enrichment)
    # The small photo over the hero: the prospect's first gallery photo when he has one, so his own
    # pictures stay together; the template's otherwise.
    gallery: list[dict[str, str]] = site.get("gallery") or []
    site["images"] = {
        "heroSecondary": gallery[0]["url"] if gallery else _DEFAULT_HERO_SECONDARY,
        "ctaBackground": _DEFAULT_CTA_BACKGROUND,
    }
    return site
