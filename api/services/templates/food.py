"""
'food' demo template — self-contained registration.

Food truck / street food template: cream & forest-green DA (Pencil food trucks landing).
Flat ``SiteContent`` path only — Storyblok uses the shared ``site_content``
blok family; the Nuxt layer is ``devleadhunter-template-food``.

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

TEMPLATE_ID: str = "food"

TEMPLATE_META: dict[str, object] = {
    "id": TEMPLATE_ID,
    "name": "Food Truck",
    "description": (
        "Vitrine food truck / street food « crème & vert forêt » : hero, à propos "
        "avec collage photo, menu spécialités, avis, formulaire de réservation. "
        "One-page vendable inspirée d'une landing food trucks."
    ),
    "preview_image_url": None,
    "category": "artisan",
    "default_theme": {
        "primary": "#055346",
        "secondary": "#f9efe6",
        "accent": "#f3c395",
    },
}

# Shared base bloks only (flat SiteContent).
BODY_COMPONENTS: list[str] = []
COMPONENT_SCHEMAS: list[dict[str, Any]] = []


def default_subtitle(area: str) -> str:
    """Food-truck-aware default hero subtitle when the prospect has no description.

    Args:
        area: Service area / city label.

    Returns:
        A food-truck subtitle.
    """
    return f"Street food maison à {area} — burgers, wings et classics préparés à la minute, sur place ou à emporter."


_SITE_ABOUT_DEFAULT: str = (
    "Food truck de quartier : cuisine simple et généreuse, sauces maison et "
    "service rapide. On privilégie les produits frais et on vient à vous — "
    "sur vos places préférées ou pour vos événements."
)

# Trade defaults when enrichment provides no services / FAQ.
# Mirror of layer defaults in devleadhunter-template-food (food.ts).
FOOD_SERVICES: list[dict[str, str]] = [
    {
        "title": "Burger dinde, œuf & fromage",
        "description": ("Pain brioché, dinde grillée, œuf coulant, cheddar et sauce maison. — 12 €"),
    },
    {
        "title": "Hot wings & frites",
        "description": ("Ailes marinées, sauce piquante et frites croustillantes. — 11 €"),
    },
    {
        "title": "Duo hot-dog & soda",
        "description": "Deux hot-dogs garnis, frites et boisson au choix. — 13 €",
    },
    {
        "title": "Soda float glacé",
        "description": ("Boisson gazeuse et boule de glace vanille — le classique. — 6 €"),
    },
]

FOOD_FAQ: list[dict[str, str]] = [
    {
        "question": "Où vous trouver cette semaine ?",
        "answer": (
            "On publie chaque lundi notre planning sur Instagram et Facebook. "
            "Appelez-nous aussi : on vous indique la place du jour."
        ),
    },
    {
        "question": "Acceptez-vous les groupes et événements ?",
        "answer": (
            "Oui — mariages, séminaires, festivals. Écrivez-nous ou réservez via "
            "le formulaire, on revient vers vous rapidement."
        ),
    },
    {
        "question": "Proposez-vous des options végétariennes ?",
        "answer": ("Oui, un burger veggie et des sides (frites, salade) sont toujours au menu."),
    },
    {
        "question": "Quels moyens de paiement acceptez-vous ?",
        "answer": "Espèces et carte bancaire, sur place.",
    },
]

# Editorial copy pre-filled into the CMS — EXACT mirror of the layer defaults
# (devleadhunter-template-food app/types/food.ts).
_EDITORIAL_DEFAULTS: dict[str, Any] = {
    "heroBadge": "Food truck",
    "heroPoints": ["Fait maison", "Produits frais", "Sur place ou à emporter"],
    "ctaCallLabel": "Envoyer la demande",
    "ctaQuoteLabel": "Voir le menu",
    "trustItems": [
        {"value": "4,9/5", "label": "Avis clients"},
        {"value": "12K+", "label": "Sur Instagram"},
    ],
    "servicesHeading": "Nos spécialités",
    "galleryHeading": "En images",
    "reviewsHeading": "Ce qu’ils en disent",
    "faqHeading": "Questions fréquentes",
    "aboutHeading": "Notre histoire gourmande",
    "contactHeading": "Réserver une table",
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
    scraped enrichment when present, else the food-truck editorial defaults; the template
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
    site["services"] = scraped or FOOD_SERVICES
    site["faq"] = FOOD_FAQ
    site.update(_EDITORIAL_DEFAULTS)
    return site
