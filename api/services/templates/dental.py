"""
'dental' demo template (« Family Dental Care ») — self-contained registration.

Dental clinic one-page template (Pencil DA: El Messiri + Nunito, red/beige).
Flat ``SiteContent`` path only (Phase 4b) — Storyblok uses the shared ``site_content``
blok family; the Nuxt layer is ``devleadhunter-template-dental``.

Exposes the stable names consumed by the shared services (see ``registry``):

- ``TEMPLATE_META``       → catalogue entry
- ``build_site_content``  → flat ``SiteContent`` builder
- ``BODY_COMPONENTS`` / ``COMPONENT_SCHEMAS`` → none beyond the shared base
"""
from __future__ import annotations

from typing import Any, Optional

from services.templates.site_content import (  # noqa: F401 — re-exported for the registry
    SITE_CONTENT_SCHEMAS,
    map_prospect_and_enrichment,
    to_storyblok_site_content,
)

TEMPLATE_ID: str = "dental"

TEMPLATE_META: dict[str, object] = {
    "id": TEMPLATE_ID,
    "name": "Dentaire Family Care",
    "description": (
        "Vitrine cabinet dentaire « Family Dental Care » : hero sourire, galerie, "
        "stats, soins (général / esthétique / urgences), à propos, équipe, "
        "assurances, prise de rendez-vous. Direction rouge / beige, typo El Messiri."
    ),
    "preview_image_url": None,
    "category": "sante",
    "default_theme": {
        "primary": "#b1040e",
        "secondary": "#2e333e",
        "accent": "#80060d",
    },
}

BODY_COMPONENTS: list[str] = []
COMPONENT_SCHEMAS: list[dict[str, Any]] = []


def default_subtitle(area: str) -> str:
    """Dental-aware default hero subtitle when the prospect has no description.

    @param area - Service area / city label.
    @returns A dental clinic subtitle.
    """
    return (
        f"Soins dentaires pour toute la famille à {area} — "
        "prévention, esthétique et urgences."
    )


_SITE_ABOUT_DEFAULT: str = (
    "Cabinet dentaire de proximité : prévention, soins généraux et esthétique "
    "avec la même exigence. Accueil bienveillant, parcours clair, technologies "
    "modernes pour préserver votre sourire."
)

# Trade defaults when enrichment provides no services / FAQ.
# Mirror of layer defaults in devleadhunter-template-dental (dental.ts).
DENTAL_SERVICES: list[dict[str, str]] = [
    {
        "title": "Dentisterie générale",
        "description": (
            "Contrôles, détartrage, soins cariés et suivi préventif pour toute "
            "la famille, du plus jeune au plus âgé."
        ),
    },
    {
        "title": "Esthétique du sourire",
        "description": (
            "Blanchiment, facettes, couronnes et aligners : des résultats "
            "naturels pour sourire en confiance."
        ),
    },
    {
        "title": "Urgences dentaires",
        "description": (
            "Douleur, dent cassée ou abcès : contactez-nous rapidement, "
            "nous organisons un créneau prioritaire."
        ),
    },
]

DENTAL_FAQ: list[dict[str, str]] = [
    {
        "question": "Faut-il prendre rendez-vous ?",
        "answer": (
            "Oui, de préférence. Appelez ou utilisez le formulaire : nous "
            "confirmons le créneau sous 24 h ouvrées."
        ),
    },
    {
        "question": "Acceptez-vous les nouveaux patients ?",
        "answer": (
            "Oui. Nous accueillons les nouveaux patients pour un bilan complet "
            "et un plan de soins adapté."
        ),
    },
    {
        "question": "Quelles mutuelles acceptez-vous ?",
        "answer": (
            "Nous travaillons avec la plupart des complémentaires. Apportez "
            "votre carte mutuelle à la première visite."
        ),
    },
    {
        "question": "Proposez-vous des soins d'urgence ?",
        "answer": (
            "Oui. En cas de douleur forte ou de traumatisme, contactez-nous : "
            "nous priorisons un créneau le jour même quand c'est possible."
        ),
    },
]

# Editorial copy pre-filled into the CMS — EXACT mirror of the layer defaults
# (devleadhunter-template-dental app/types/dental.ts).
_EDITORIAL_DEFAULTS: dict[str, Any] = {
    "heroBadge": "FAMILY DENTAL CARE",
    "heroPoints": [
        "Preventive Guidance",
        "Friendly Service",
        "Dental Technology",
    ],
    "ctaCallLabel": "Book an Appointment",
    "ctaQuoteLabel": "Browse our service",
    "trustItems": [
        {"value": "20+", "label": "Years Of Experience"},
        {"value": "200+", "label": "Satisfied Clients"},
        {"value": "20+", "label": "Certified Dentist"},
    ],
    "servicesHeading": "Quality dental services",
    "galleryHeading": "Creating beautiful smiles for all ages",
    "reviewsHeading": "Meet your neighborhood dentists",
    "faqHeading": "Questions fréquentes",
    "aboutHeading": "Your smile is our pride",
    "contactHeading": "Book Appointment",
}


def build_site_content(
    *,
    business_name: str,
    phone: Optional[str],
    email: Optional[str],
    city: Optional[str],
    area: str,
    subtitle: str,
    palette: dict[str, str],
    enrichment: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build the flat ``SiteContent`` for this template (Phase 4b).

    Prospect fields + enrichment map through the shared helper; services come from the
    scraped enrichment when present, else the dental editorial defaults.
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
    scraped = [
        {"title": str(name).strip(), "description": ""}
        for name in enr.get("services", [])
        if isinstance(name, str) and str(name).strip()
    ]
    site["services"] = scraped or DENTAL_SERVICES
    site["faq"] = DENTAL_FAQ
    site.update(_EDITORIAL_DEFAULTS)
    return site
