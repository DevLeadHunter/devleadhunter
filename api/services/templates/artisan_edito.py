"""
'artisan-edito' demo template ("Édito") — self-contained registration.

The DEFAULT, multi-trade template: an editorial black-and-white + honey-amber DA
that mirrors the DevLeadHunter landing. Trade-agnostic copy (plumber, electrician,
garagiste, menuisier…) — the real services/FAQ come from enrichment when present,
else these generic defaults.

Exposes the stable names consumed by the shared services (see ``registry``):
- ``TEMPLATE_META``       → catalogue entry
- ``build_site_content`` → flat ``SiteContent`` builder (Phase 4b path)
- ``BODY_COMPONENTS`` / ``COMPONENT_SCHEMAS`` → none beyond the shared base

Rendering component (Nuxt layer): devleadhunter-template-artisan-edito (ArtisanEditoRoot).
"""
from __future__ import annotations

from typing import Any, Optional

from services.templates.site_content import map_prospect_and_enrichment

TEMPLATE_ID: str = "artisan-edito"

TEMPLATE_META: dict[str, object] = {
    "id": TEMPLATE_ID,
    "name": "Édito (multi-métier)",
    "description": (
        "Template par défaut, passe-partout tous corps de métier : direction éditoriale "
        "papier & encre + accent ambre, façon magazine — reprise de la DA de la landing "
        "DevLeadHunter. Hero asymétrique, index de services numéroté, avant/après, avis, FAQ. "
        "Fonctionne pour plombier, électricien, garagiste, menuisier…"
    ),
    "preview_image_url": None,
    "category": "artisan",
    # Editorial B&W + honey amber (the landing DA). Palette drives the template's
    # ink / secondary / accent tones.
    "default_theme": {
        "primary": "#1B1813",
        "secondary": "#6B6355",
        "accent": "#E8A33C",
    },
}

# This template only uses the shared base bloks.
BODY_COMPONENTS: list[str] = []
COMPONENT_SCHEMAS: list[dict[str, Any]] = []


def default_subtitle(area: str) -> str:
    """Trade-neutral default hero subtitle when the prospect has no description.

    @param area - Service area / city label.
    @returns A generic artisan subtitle (any trade).
    """
    return f"Artisan de confiance à {area} — un travail soigné, un devis clair, un interlocuteur unique."

_SITE_ABOUT_DEFAULT: str = (
    "Artisan de confiance, j'interviens avec le même soin sur chaque chantier : "
    "diagnostic honnête, travail propre et fini, prix juste. Vous parlez à la personne "
    "qui fait le travail, pas à un standard."
)

# Trade-neutral services (used only when enrichment provides none). Deliberately
# generic so the default template reads well for any trade.
GENERIC_SERVICES: list[dict[str, str]] = [
    {"title": "Conseil & devis", "description": "On fait le point sur votre besoin et vous recevez un devis clair, gratuit et sans engagement."},
    {"title": "Intervention & pose", "description": "Installation ou pose réalisée dans les règles de l'art, avec du matériel de qualité."},
    {"title": "Dépannage", "description": "Un imprévu ? Intervention rapide pour remettre les choses en état, proprement."},
    {"title": "Entretien", "description": "Un suivi régulier pour éviter les pannes et faire durer vos installations."},
    {"title": "Rénovation", "description": "Un projet plus ambitieux mené du premier échange à la finition, sans mauvaise surprise."},
]

GENERIC_FAQ: list[dict[str, str]] = [
    {"question": "Le devis est-il gratuit ?", "answer": "Oui, le devis est toujours gratuit et sans engagement, remis avant toute intervention."},
    {"question": "Intervenez-vous en urgence ?", "answer": "Selon les disponibilités, oui — appelez-nous, on vous dit tout de suite ce qu'on peut faire."},
    {"question": "Quelles zones couvrez-vous ?", "answer": "Votre ville et les communes voisines. Appelez pour vérifier, on se déplace souvent au-delà."},
    {"question": "Quels moyens de paiement acceptez-vous ?", "answer": "Carte, chèque et virement, avec une facture détaillée."},
    {"question": "Vos travaux sont-ils garantis ?", "answer": "Oui, nos interventions sont réalisées dans les règles et couvertes par les garanties en vigueur."},
]

# Editorial copy pre-filled into the CMS so the client sees (and edits) his real
# texts instead of blank fields. Generic, multi-trade — mirror of the layer defaults
# of devleadhunter-template-artisan-edito.
_EDITORIAL_DEFAULTS: dict[str, Any] = {
    "heroBadge": "Artisan à votre service",
    "heroPoints": ["Devis gratuit", "Intervention soignée", "Travail garanti"],
    "ctaCallLabel": "Appeler",
    "ctaQuoteLabel": "Demander un devis",
    "trustItems": [
        {"value": "Réactif", "label": "Réponse rapide"},
        {"value": "Devis 0 €", "label": "Sans engagement"},
        {"value": "Local", "label": "Près de chez vous"},
        {"value": "Garanti", "label": "Travail assuré"},
    ],
    "servicesHeading": "Nos prestations",
    "galleryHeading": "Nos réalisations",
    "reviewsHeading": "Ils nous font confiance",
    "faqHeading": "Questions fréquentes",
    "aboutHeading": "L'artisan derrière l'entreprise",
    "contactHeading": "Parlons de votre projet",
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
    """Build the flat ``SiteContent`` for the default multi-trade template.

    Prospect fields + enrichment map through the shared helper; services come from the
    scraped enrichment when present, else the generic trade-neutral defaults; the editorial
    copy is pre-filled so the client edits his real texts in the CMS. See ``site_content.py``.
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
    site["services"] = scraped or GENERIC_SERVICES
    site["faq"] = GENERIC_FAQ
    # Pre-fill editorial copy (client edits his real texts in the CMS).
    site.update(_EDITORIAL_DEFAULTS)
    return site
