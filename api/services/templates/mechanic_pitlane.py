"""
'mechanic-pitlane' demo template (« Pitlane ») — self-contained registration.

Garage / mécanicien template: dark asphalt + racing red DA (AutoWorks-inspired).
Flat ``SiteContent`` path only (Phase 4b) — Storyblok uses the shared ``site_content``
blok family; the Nuxt layer is ``devleadhunter-template-mechanic-pitlane``.

Exposes the stable names consumed by the shared services (see ``registry``):

- ``TEMPLATE_META``       → catalogue entry
- ``build_site_content``  → flat ``SiteContent`` builder
- ``BODY_COMPONENTS`` / ``COMPONENT_SCHEMAS`` → none beyond the shared base
"""

from __future__ import annotations

from typing import Any

from services.templates.site_content import (  # noqa: F401 — re-exported for the registry
    SITE_CONTENT_SCHEMAS,
    apply_real_trust_stats,
    fixed_trade_services,
    map_prospect_and_enrichment,
    resolve_trade_services,
    to_storyblok_site_content,
)

TEMPLATE_ID: str = "mechanic-pitlane"

TEMPLATE_META: dict[str, object] = {
    "id": TEMPLATE_ID,
    "name": "Mécanicien Pitlane",
    "description": (
        "Vitrine garage / mécanicien « asphalt & racing red » : hero atelier, stats, "
        "prestations photo, pourquoi nous, à propos, galerie lightbox, process, avis, "
        "formulaire RDV (plaque), FAQ, carte. Direction sombre type AutoWorks — "
        "vendable one-page."
    ),
    "preview_image_url": None,
    "category": "artisan",
    "trades": ["garagiste", "mecanicien", "garage", "mechanic", "automobile"],
    "default_theme": {
        "primary": "#E11D2E",
        "secondary": "#0C0C0D",
        "accent": "#F4F4F5",
    },
    # Canonical colour roles → palette key (audit 2026-08-17). Only these roles are editable;
    # keys not listed here don't visibly theme this layer, so the editor hides them.
    "color_roles": {"action": "primary", "fond": "secondary", "secondaire": "accent"},
}

# Shared base bloks only (flat SiteContent).
BODY_COMPONENTS: list[str] = []
COMPONENT_SCHEMAS: list[dict[str, Any]] = []

# Sections this template renders — drives the client's Storyblok editor so it shows no dead sections.
USED_SECTIONS: list[str] = ["hero", "trust", "about", "services", "gallery", "reviews", "faq", "contact"]

# One-off photos this template renders that aren't hero/about/gallery — exposed as dedicated, labelled
# Storyblok fields (grouped in the section they appear in), editable by the client via ``SiteContent.images``.
EXTRA_SECTION_IMAGES: dict[str, list[dict[str, str]]] = {
    "about": [{"field": "aboutSecondary", "label": "Deuxième photo à propos"}],
    "faq": [{"field": "faq", "label": "Photo de la section FAQ"}],
}

# Default photo pool for the per-service card images + the two one-off slots — EXACT mirror of the layer
# defaults (devleadhunter-template-mechanic-pitlane app/types/pitlane.ts ``defaults.images.gallery``).
_DEFAULT_SERVICE_IMAGES: list[str] = [
    "https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1619642751034-765dfdf7c58e?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1637640125496-31852f042a60?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1723099971299-3789db53604c?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1711386689622-1cda23e10217?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1735361039382-d78a0a0cc185?auto=format&fit=crop&w=1200&q=80",
]
# The two one-off slots fall back, in the layer, to gallery photos: aboutSecondary → gallery[1], faq → gallery[0].
_DEFAULT_ABOUT_SECONDARY: str = _DEFAULT_SERVICE_IMAGES[1]
_DEFAULT_FAQ_IMAGE: str = _DEFAULT_SERVICE_IMAGES[0]


def default_subtitle(area: str) -> str:
    """Garage-aware default hero subtitle when the prospect has no description.

    Args:
        area: Service area / city label.

    Returns:
        A garage subtitle.
    """
    return f"Entretien, diagnostic et réparations à {area} — un atelier de confiance, devis avant intervention."


_SITE_ABOUT_DEFAULT: str = (
    "Garage multi-marques de proximité : entretien, diagnostic électronique et "
    "réparations avec le même soin. Devis clair avant intervention, pièces de qualité, "
    "restitution dans les délais annoncés."
)

# Trade defaults when enrichment provides no services / FAQ.
# Mirror of layer defaults in devleadhunter-template-mechanic-pitlane (pitlane.ts).
MECHANIC_SERVICES: list[dict[str, str]] = [
    {
        "title": "Révision & entretien",
        "description": (
            "Vidange, filtres, freins, climatisation : on suit le carnet constructeur "
            "et on vous prévient avant usure critique."
        ),
    },
    {
        "title": "Diagnostic électronique",
        "description": (
            "Valise multi-marques, lecture des défauts, recherche de panne. "
            "Le devis part du diagnostic — pas l'inverse."
        ),
    },
    {
        "title": "Freinage & trains roulants",
        "description": (
            "Plaquettes, disques, amortisseurs, silentblocs, géométrie : sécurité et tenue de route remises en état."
        ),
    },
    {
        "title": "Distribution & mécanique",
        "description": (
            "Courroie / chaîne, pompe à eau, embrayage, joints — interventions "
            "planifiées avec devis ferme et délai clair."
        ),
    },
    {
        "title": "Pneus & géométrie",
        "description": (
            "Montage, équilibrage, crevaison, conseil usure. On vous dit quand le "
            "pneu peut encore rouler — et quand non."
        ),
    },
    {
        "title": "Carrosserie légère",
        "description": (
            "Rayures, chocs de parking, pare-chocs : remises en état propres pour un véhicule présentable."
        ),
    },
]

MECHANIC_FAQ: list[dict[str, str]] = [
    {
        "question": "Faut-il prendre rendez-vous ?",
        "answer": (
            "Oui, de préférence. Ça nous permet de préparer le créneau et les pièces "
            "éventuelles. En urgence, appelez : on voit ce qui est possible le jour même."
        ),
    },
    {
        "question": "Le devis est-il gratuit ?",
        "answer": (
            "Le devis de réparation est établi après diagnostic. On vous l'explique "
            "clairement avant toute intervention — rien n'est lancé sans votre accord."
        ),
    },
    {
        "question": "Intervenez-vous sur toutes les marques ?",
        "answer": (
            "Oui, atelier multi-marques : citadines, breaks, SUV et utilitaires légers. "
            "Diagnostic électronique adapté aux véhicules récents."
        ),
    },
    {
        "question": "Puis-je laisser la voiture la journée ?",
        "answer": (
            "Oui. Indiquez-nous à la prise de rendez-vous si vous avez besoin d'un créneau de restitution précis."
        ),
    },
]

# Editorial copy pre-filled into the CMS — EXACT mirror of the layer defaults
# (devleadhunter-template-mechanic-pitlane app/types/pitlane.ts).
_EDITORIAL_DEFAULTS: dict[str, Any] = {
    "heroBadge": "Garage multi-marques",
    "heroPoints": ["Devis avant réparation", "Toutes marques", "Pièces garanties"],
    "ctaCallLabel": "Appeler l'atelier",
    "ctaQuoteLabel": "Prendre rendez-vous",
    "trustItems": [
        {"value": "4,9/5", "label": "Avis clients"},
        {"value": "RDV", "label": "Sur rendez-vous"},
        {"value": "Pièces", "label": "Garantie fabricant"},
        {"value": "Local", "label": "Atelier de proximité"},
    ],
    "servicesHeading": "Nos prestations",
    "galleryHeading": "L'atelier en images",
    "reviewsHeading": "Avis clients",
    "faqHeading": "Questions fréquentes",
    "aboutHeading": "L'atelier",
    "contactHeading": "Prendre rendez-vous",
}


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
    """Build the flat ``SiteContent`` for this template (Phase 4b).

    Prospect fields + enrichment map through the shared helper; services come from the
    scraped enrichment when present, else the garage editorial defaults; the template
    layer supplies section headings and remaining boilerplate. See ``site_content.py``.
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
    enr = enrichment or {}
    site["services"] = fixed_trade_services(MECHANIC_SERVICES)
    site["faq"] = MECHANIC_FAQ
    site.update(_EDITORIAL_DEFAULTS)
    apply_real_trust_stats(site, enrichment)
    # Each service card, the second "about" photo and the FAQ photo are dedicated, editable CMS fields now,
    # seeded with the template's own default photos so the client sees them (and can replace them) in Storyblok.
    # Per-service image: a distinct default per card (no "% length" repeat within the 6-card grid).
    for index, service in enumerate(site["services"]):
        service["image"] = _DEFAULT_SERVICE_IMAGES[index % len(_DEFAULT_SERVICE_IMAGES)]
    site["images"] = {"aboutSecondary": _DEFAULT_ABOUT_SECONDARY, "faq": _DEFAULT_FAQ_IMAGE}
    return site
