"""
'landscaper-verdure' demo template — self-contained registration.

Paysagiste / verdure one-page (Pencil DA « Eco Landscaping » : Inter, vert d'eau,
encre sapin, lime en accent). Flat ``SiteContent`` path only — Storyblok uses the
shared ``site_content`` blok family; the Nuxt layer is
``devleadhunter-template-landscaper-verdure``.

Exposes the stable names consumed by the shared services (see ``registry``):

- ``TEMPLATE_META``       → catalogue entry
- ``build_site_content``  → flat ``SiteContent`` builder
- ``BODY_COMPONENTS`` / ``COMPONENT_SCHEMAS`` → none beyond the shared base
"""

from __future__ import annotations

from typing import Any

from services.templates.site_content import (  # noqa: F401 — re-exported for the registry
    SITE_CONTENT_SCHEMAS,
    fixed_trade_services,
    format_rating_value,
    format_review_count,
    map_prospect_and_enrichment,
    to_storyblok_site_content,
)

TEMPLATE_ID: str = "landscaper-verdure"

TEMPLATE_META: dict[str, object] = {
    "id": TEMPLATE_ID,
    "name": "Paysagiste Verdure",
    "description": (
        "Vitrine one-page paysagiste / verdure « Eco Landscaping » : hero plein cadre, "
        "grille de prestations à encoches, pourquoi nous choisir, méthode en trois "
        "étapes, réalisations, FAQ (crédit d'impôt inclus) et bandeau contact. "
        "Fond vert d'eau, encre sapin, lime en accent."
    ),
    "preview_image_url": None,
    "category": "artisan",
    "trades": ["paysagiste", "jardinier", "fleuriste", "paysagisme", "espaces verts", "elagage", "landscaper"],
    "default_theme": {
        "primary": "#2d746d",
        "secondary": "#00b67a",
        "accent": "#bcff83",
    },
    # Canonical colour roles → palette key (revu 2026-09-09). Only these roles are editable; keys
    # not listed here don't visibly theme this layer, so the editor hides them. The page keeps a
    # fixed cream background — the "fond" role tints the blurred ambient halos, not the flat fill.
    "color_roles": {"action": "primary", "fond": "secondary", "secondaire": "accent"},
    # Action colour = primary, so the prospect's logo colour lands on the buttons.
    "brand_color_key": "primary",
}

# Shared base bloks only (flat SiteContent).
BODY_COMPONENTS: list[str] = []
COMPONENT_SCHEMAS: list[dict[str, Any]] = []

# Sections this template renders — drives the client's Storyblok editor so it shows no dead sections.
# "portfolio" (not "gallery"): the photo grid is the editable ``portfolio`` blok (image + title +
# category), so the client curates the two « réalisations » cards instead of a raw scraped gallery.
# "trust" = the stats band (real Google rating + count), "method" = the « notre méthode » steps,
# "reviews" = the Google reviews section — all editable in the client's Storyblok.
USED_SECTIONS: list[str] = [
    "hero",
    "trust",
    "about",
    "services",
    "method",
    "reviews",
    "faq",
    "portfolio",
    "contact",
]

# One-off photo this template renders that isn't hero/about — exposed as a dedicated, labelled
# Storyblok asset field (grouped in the section it appears in), editable via ``SiteContent.images``.
EXTRA_SECTION_IMAGES: dict[str, list[dict[str, str]]] = {
    "contact": [{"field": "ctaBackground", "label": "Image de fond de la bannière contact"}],
}

# Per-section field overrides (see registry.to_storyblok_site_content). Each list REPLACES the shared
# default for that section in this template's editor.
SECTION_FIELDS: dict[str, list[str]] = {
    # Hero: expose the editable H1 (``heroTitle``); drop the two fields this layer never renders —
    # ``heroBadge`` (decorative SVG, not text) and ``heroPoints``. ``ctaCallLabel`` moves to the contact
    # section, where the banner button it drives actually lives.
    "hero": ["heroTitle", "subtitle", "heroImage", "ctaQuoteLabel"],
    # Services: add the section intro paragraph (``servicesLead``) on top of the shared title + cards.
    "services": ["servicesHeading", "servicesLead", "services"],
    # Contact: the shared default fields + the relabelled banner button (``ctaCallLabel``, see below).
    "contact": [
        "contactHeading",
        "ctaCallLabel",
        "businessName",
        "phone",
        "email",
        "city",
        "area",
        "logo",
        "openingHours",
        "social",
    ],
}

# Relabel a shared field this template repurposes (see build_content_schemas). ``ctaCallLabel`` drives
# the contact banner's « Être rappelé » button here, not a generic « appeler » button — so the editor
# labels it accordingly instead of the shared "Bouton « appeler »".
FIELD_SCHEMA_OVERRIDES: dict[str, dict[str, Any]] = {
    "ctaCallLabel": {
        "display_name": "Bouton de la bannière contact",
        "description": "Texte du bouton « Être rappelé » de la bannière au-dessus du contact",
    },
}


def default_subtitle(area: str) -> str:
    """Landscaper-aware default hero subtitle when the prospect has no description.

    Args:
        area: Service area / city label.

    Returns:
        A landscaper subtitle.
    """
    return f"Création, aménagement et entretien de jardins à {area}, avec devis gratuit et pratiques durables."


_SITE_ABOUT_DEFAULT: str = (
    "Paysagiste local, nous accompagnons particuliers et professionnels dans la "
    "création et l'entretien de leurs espaces verts. Chaque projet commence par une "
    "visite et un devis gratuit, et se termine par un extérieur dont on prend "
    "plaisir à profiter."
)

# Trade defaults when enrichment provides no services / FAQ.
# Mirror of layer defaults in devleadhunter-template-landscaper-verdure (verdure.ts).
VERDURE_SERVICES: list[dict[str, str]] = [
    {
        "title": "Création de jardins",
        "description": (
            "Conception et plantation d'un jardin qui vous ressemble, pensé pour durer au fil des saisons."
        ),
    },
    {
        "title": "Entretien & tonte",
        "description": (
            "Tonte, taille, désherbage et soins réguliers pour une pelouse dense et des massifs impeccables."
        ),
    },
    {
        "title": "Terrasses & allées",
        "description": (
            "Terrasses, allées et murets : des aménagements minéraux propres qui structurent votre extérieur."
        ),
    },
    {
        "title": "Arrosage & clôtures",
        "description": ("Arrosage automatique, clôtures et portails posés dans les règles, sans mauvaise surprise."),
    },
]

VERDURE_FAQ: list[dict[str, str]] = [
    {
        "question": "À quelle fréquence intervenez-vous pour l'entretien ?",
        "answer": (
            "Selon vos besoins : au contrat à l'année (passages réguliers planifiés ensemble) ou à la "
            "demande. En pleine saison de pousse, un passage toutes les une à deux semaines garde un "
            "jardin impeccable."
        ),
    },
    {
        "question": "Le devis est-il vraiment gratuit ?",
        "answer": (
            "Oui. Nous nous déplaçons, écoutons votre projet et vous remettons un devis écrit, détaillé "
            "et sans engagement, avant tout début de chantier."
        ),
    },
    {
        "question": "Travaillez-vous avec des produits respectueux de l'environnement ?",
        "answer": (
            "Absolument. Nous privilégions les traitements naturels, le paillage, des végétaux adaptés "
            "au climat local et l'évacuation responsable des déchets verts."
        ),
    },
    {
        "question": "Puis-je bénéficier du crédit d'impôt pour l'entretien de jardin ?",
        "answer": (
            "Oui, les prestations d'entretien courant (tonte, taille de haies…) ouvrent droit au crédit "
            "d'impôt services à la personne de 50 % dans la limite du plafond en vigueur. Nous vous "
            "fournissons l'attestation."
        ),
    },
]

# Editorial copy pre-filled into the CMS — EXACT mirror of the layer defaults
# (devleadhunter-template-landscaper-verdure app/types/verdure.ts fallbacks).
# ``aboutHeading`` is left out on purpose: empty, the layer derives it from the name.
_EDITORIAL_DEFAULTS: dict[str, Any] = {
    "heroTitle": "Des extérieurs pensés, plantés et entretenus",
    "ctaCallLabel": "Être rappelé",
    "ctaQuoteLabel": "Demander un devis gratuit",
    "servicesHeading": "Un seul artisan pour tout votre extérieur",
    "servicesLead": (
        "Du dessin du jardin à son entretien régulier : un interlocuteur unique, un matériel adapté "
        "et des végétaux choisis pour votre terrain."
    ),
    "stepsHeading": "Comment ça se passe ?",
    "reviewsHeading": "Ils nous ont fait confiance",
    "portfolioHeading": "Nos derniers chantiers",
    "faqHeading": "Vos questions, nos réponses",
}

# The « notre méthode » steps pre-filled into the CMS — EXACT mirror of the layer defaults
# (verdure.ts ``DEFAULT_HOW``). The layer numbers them (« Étape 1/2/3 ») by index.
_DEFAULT_STEPS: list[dict[str, str]] = [
    {
        "title": "Visite & écoute",
        "description": (
            "Nous venons voir votre terrain, écoutons vos envies et vos contraintes, et prenons les "
            "mesures nécessaires."
        ),
    },
    {
        "title": "Devis détaillé",
        "description": (
            "Vous recevez une proposition claire : prestations, végétaux ou matériaux, délais et budget, sans surprise."
        ),
    },
    {
        "title": "Réalisation soignée",
        "description": (
            "De la préparation du sol aux finitions, nous réalisons le chantier avec soin et laissons un "
            "extérieur propre."
        ),
    },
]


def _real_trust_items(enrichment: dict[str, Any] | None) -> list[dict[str, str]]:
    """Honest stat-band badges: the real Google rating + review count when scraped, then qualitative
    badges — never a fabricated count like « 180+ jardins » or « 100+ clients ».

    Args:
        enrichment: Scraped enrichment dict, or None.

    Returns:
        Up to three ``{"value", "label"}`` badges for the stats band.
    """
    enr = enrichment or {}
    items: list[dict[str, str]] = []
    rating = format_rating_value(enr.get("rating"))
    if rating:
        items.append({"value": rating, "label": "Note Google"})
    count = format_review_count(enr.get("reviews_count"))
    if count:
        items.append({"value": count, "label": "avis clients"})
    for badge in (
        {"value": "Devis 0 €", "label": "Sans engagement"},
        {"value": "Sur mesure", "label": "Chaque jardin est unique"},
        {"value": "Local", "label": "Proche de chez vous"},
    ):
        if len(items) >= 3:
            break
        items.append(dict(badge))
    return items


# Bundled layer photos (served from demo-host), promoted to absolute URLs so Storyblok can preview
# them, and seeded into the CMS so every photo becomes a dedicated, client-editable field. EXACT
# mirror of the layer defaults (verdure.ts ``SERVICE_IMAGES`` / ``PORTFOLIO_IMAGES`` / the CTA bg).
_VERDURE_IMAGE_BASE: str = "https://demo.dibodev.fr/images/verdure"
# One photo per prestation card, index-aligned with the four ``VERDURE_SERVICES``.
_DEFAULT_SERVICE_IMAGES: list[str] = [
    f"{_VERDURE_IMAGE_BASE}/image-import-4.jpg",
    f"{_VERDURE_IMAGE_BASE}/image-import-38.jpg",
    f"{_VERDURE_IMAGE_BASE}/image-import.jpg",
    f"{_VERDURE_IMAGE_BASE}/image-import-6.jpg",
]
# The two « réalisations » cards (photo + title + category), seeded into the editable portfolio blok.
_DEFAULT_PORTFOLIO: list[dict[str, str]] = [
    {
        "image": f"{_VERDURE_IMAGE_BASE}/image-import-12.jpg",
        "title": "Transformation complète d'un jardin : terrasse, massifs et éclairage",
        "category": "Création",
    },
    {
        "image": f"{_VERDURE_IMAGE_BASE}/image-import.jpg",
        "title": "Remise en état d'un extérieur : pelouse, haies et allées rafraîchies",
        "category": "Entretien",
    },
]
# Contact-banner background (was hardcoded CSS ``url('/images/verdure/image-import-3.jpg')``).
_DEFAULT_CTA_BACKGROUND: str = f"{_VERDURE_IMAGE_BASE}/image-import-3.jpg"


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

    Prospect fields + enrichment map through the shared helper; services come from the
    scraped enrichment when present, else the landscaper editorial defaults; the template
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
    site["services"] = fixed_trade_services(VERDURE_SERVICES)
    site["faq"] = VERDURE_FAQ
    site.update(_EDITORIAL_DEFAULTS)
    # Fresh copies so the shared module-level defaults are never mutated across generations.
    site["steps"] = [dict(step) for step in _DEFAULT_STEPS]
    # Real Google rating + count for the stats band (no fabricated numbers); editable afterwards.
    site["trustItems"] = _real_trust_items(enrichment)
    # Seed every remaining photo as a dedicated, client-editable CMS field with the layer's own
    # defaults: one photo per prestation card, the two portfolio « réalisations », and the contact
    # banner background. Absolute demo-host URLs so the Storyblok Visual Editor previews each one.
    for index, service in enumerate(site["services"]):
        service["image"] = _DEFAULT_SERVICE_IMAGES[index % len(_DEFAULT_SERVICE_IMAGES)]
    site["portfolio"] = [dict(item) for item in _DEFAULT_PORTFOLIO]
    site["images"] = {"ctaBackground": _DEFAULT_CTA_BACKGROUND}
    return site
