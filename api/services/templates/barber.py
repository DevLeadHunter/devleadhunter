"""
'barber' demo template — self-contained registration.

Barbershop / coiffeur homme one-page (Pencil DA: Barlow + Work Sans, cream & charcoal).
Flat ``SiteContent`` path only — Storyblok uses the shared ``site_content``
blok family; the Nuxt layer is ``devleadhunter-template-barber``.

Exposes the stable names consumed by the shared services (see ``registry``):

- ``TEMPLATE_META``       → catalogue entry
- ``build_site_content``  → flat ``SiteContent`` builder
- ``BODY_COMPONENTS`` / ``COMPONENT_SCHEMAS`` → none beyond the shared base
"""

from __future__ import annotations

from typing import Any

from services.templates.site_content import (  # noqa: F401 — re-exported for the registry
    SITE_CONTENT_SCHEMAS,
    map_prospect_and_enrichment,
    to_storyblok_site_content,
)

TEMPLATE_ID: str = "barber"

TEMPLATE_META: dict[str, object] = {
    "id": TEMPLATE_ID,
    "name": "Barbier / Coiffeur",
    "description": (
        "Vitrine barbershop / coiffeur homme « crème & charcoal » : hero, "
        "à propos avec stats, grille de prestations, bandeau CTA, why + avis, "
        "prise de rendez-vous. One-page vendable inspirée d'une landing barbershop."
    ),
    "preview_image_url": None,
    "category": "artisan",
    "default_theme": {
        "primary": "#121212",
        "secondary": "#f8f5ef",
        "accent": "#dec7a6",
    },
}

# Shared base bloks only (flat SiteContent).
BODY_COMPONENTS: list[str] = []
COMPONENT_SCHEMAS: list[dict[str, Any]] = []


def default_subtitle(area: str) -> str:
    """Barber-aware default hero subtitle when the prospect has no description.

    Args:
        area: Service area / city label.

    Returns:
        A barber subtitle.
    """
    return f"Coupe, barbe et soins pour hommes à {area} — un salon de quartier, sur rendez-vous."


_SITE_ABOUT_DEFAULT: str = (
    "Salon de coiffure pour hommes : coupes classiques et contemporaines, "
    "entretien de barbe et rasage soigné. Accueil sans chichi, diagnostic "
    "clair et un résultat net à chaque passage."
)

# Trade defaults when enrichment provides no services / FAQ.
# Mirror of layer defaults in devleadhunter-template-barber (barber.ts).
BARBER_SERVICES: list[dict[str, str]] = [
    {
        "title": "Coupe homme",
        "description": ("Shampooing, coupe aux ciseaux ou tondeuse, séchage et conseils d'entretien. — 32 €"),
    },
    {
        "title": "Coupe enfant (-12 ans)",
        "description": ("Coupe adaptée aux plus jeunes, en douceur et sans stress. — 22 €"),
    },
    {
        "title": "Taille de barbe",
        "description": ("Contour, volume et finition rasoir — barbe nette et structurée. — 18 €"),
    },
    {
        "title": "Rasage traditionnel",
        "description": ("Serviette chaude, mousse, rasoir droit et after-shave. — 28 €"),
    },
    {
        "title": "Coupe + barbe",
        "description": ("Le duo signature : coupe complète et entretien de barbe. — 45 €"),
    },
    {
        "title": "Soin cuir chevelu",
        "description": ("Massage, masque hydratant et finition adaptée à votre cuir chevelu. — 15 €"),
    },
]

BARBER_FAQ: list[dict[str, str]] = [
    {
        "question": "Faut-il prendre rendez-vous ?",
        "answer": ("Oui, de préférence. Appelez ou utilisez le formulaire : nous confirmons le créneau rapidement."),
    },
    {
        "question": "Proposez-vous coupe + barbe ?",
        "answer": ("Oui — le duo coupe et entretien de barbe est notre formule la plus demandée."),
    },
    {
        "question": "Quels moyens de paiement acceptez-vous ?",
        "answer": "Espèces et carte bancaire, sur place.",
    },
    {
        "question": "Acceptez-vous les enfants ?",
        "answer": ("Oui, nous proposons une coupe adaptée aux moins de 12 ans."),
    },
]

# Editorial copy pre-filled into the CMS — EXACT mirror of the layer defaults
# (devleadhunter-template-barber app/types/barber.ts editorial resolveText fallbacks).
_EDITORIAL_DEFAULTS: dict[str, Any] = {
    "heroBadge": "BARBIER",
    "heroPoints": ["Sur rendez-vous", "Produits soignés", "Salon de quartier"],
    "ctaCallLabel": "Prendre rendez-vous",
    "ctaQuoteLabel": "Voir les prestations",
    "trustItems": [
        {"value": "98%", "label": "Clients satisfaits"},
        {"value": "10+", "label": "Années d'expérience"},
    ],
    "servicesHeading": "Nos prestations",
    "galleryHeading": "En salon",
    "reviewsHeading": "Avis clients",
    "faqHeading": "Pourquoi nous choisir",
    "aboutHeading": "Votre barbier de quartier",
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
    scraped enrichment when present, else the barber editorial defaults; the template
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
    scraped = [
        {"title": str(name).strip(), "description": ""}
        for name in enr.get("services", [])
        if isinstance(name, str) and str(name).strip()
    ]
    site["services"] = scraped or BARBER_SERVICES
    site["faq"] = BARBER_FAQ
    site.update(_EDITORIAL_DEFAULTS)
    return site
