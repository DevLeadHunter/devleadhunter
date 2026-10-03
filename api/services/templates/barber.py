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

import re
from typing import Any

from services.templates.site_content import (  # noqa: F401 — re-exported for the registry
    SITE_CONTENT_SCHEMAS,
    apply_real_trust_stats,
    fixed_trade_services,
    map_prospect_and_enrichment,
    resolve_trade_services,
    to_storyblok_site_content,
)
from services.templates.visitor_data import TemplateVisitorData

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
    "trades": ["barbier", "coiffeur", "barber", "coiffure"],
    "default_theme": {
        "primary": "#121212",
        "secondary": "#f8f5ef",
        "accent": "#dec7a6",
    },
    # Canonical colour roles → palette key (audit 2026-08-17). Only these roles are editable;
    # keys not listed here don't visibly theme this layer, so the editor hides them.
    "color_roles": {"action": "accent"},
    # Barber's action colour is the gold accent (its primary is the dark charcoal).
    "brand_color_key": "accent",
}

VISITOR_DATA: TemplateVisitorData = TemplateVisitorData(
    has_contact_form=True,
    has_google_fonts=True,
    has_google_map=True,
)

# Shared base bloks only (flat SiteContent).
BODY_COMPONENTS: list[str] = []
COMPONENT_SCHEMAS: list[dict[str, Any]] = []

# Sections this template renders — drives the client's Storyblok editor so it shows no dead sections.
# No "gallery": barber shows no photo grid; its extra photos are dedicated fields below.
USED_SECTIONS: list[str] = ["hero", "trust", "about", "services", "reviews", "faq", "contact"]

# One-off photos this template renders that aren't hero/about/gallery — exposed as dedicated, labelled
# Storyblok fields (grouped in the section they appear in), editable by the client via ``SiteContent.images``.
EXTRA_SECTION_IMAGES: dict[str, list[dict[str, str]]] = {
    "about": [{"field": "midCta", "label": "Photo du bandeau « le luxe d'un vrai salon »"}],
    "contact": [{"field": "contactBackground", "label": "Photo de fond de la section contact"}],
}
_DEFAULT_MID_CTA: str = "https://images.unsplash.com/photo-1621605815971-fbc98d665033?auto=format&fit=crop&w=1400&q=80"
_DEFAULT_CONTACT: str = "https://images.unsplash.com/photo-1521590832167-7bcbfaaae1b0?auto=format&fit=crop&w=1400&q=80"


def default_subtitle(area: str) -> str:
    """Gender-neutral default hero subtitle when the prospect has no description.

    Kept neutral (no "pour hommes") because this helper has no business name to tell a men-only
    barbershop from a mixed salon; the gendered wording lives in the about + hero title instead.

    Args:
        area: Service area / city label.

    Returns:
        A barber subtitle.
    """
    return f"Coupe, barbe et soins à {area} — un salon de quartier, sur rendez-vous."


# Same template, two audiences: a men's barbershop keeps the "pour hommes" framing; a mixed salon
# (or an ambiguous name) gets the neutral one. Which about is used is decided by ``_is_masculine_barber``.
_ABOUT_MEN: str = (
    "Salon de coiffure pour hommes : coupes classiques et contemporaines, "
    "entretien de barbe et rasage soigné. Accueil sans chichi, diagnostic "
    "clair et un résultat net à chaque passage."
)
_ABOUT_MIXED: str = (
    "Salon de coiffure : coupes classiques et contemporaines, entretien de "
    "barbe et rasage soigné. Accueil sans chichi, diagnostic clair et un "
    "résultat net à chaque passage."
)
# Kept for the shared helper's signature; a men-only default is the safe base since the DA is a barbershop.
_SITE_ABOUT_DEFAULT: str = _ABOUT_MEN

_MASCULINE_TRADE_RE = re.compile(r"barbi(?:er|ère)|\bbarber\b|barbershop|\bhomme|\bmen\b|messieurs", re.IGNORECASE)
_MIXED_TRADE_RE = re.compile(r"coiffure|coiffeu(?:r|se)|\bsalon\b|mixte|\bdames?\b|\bfemme", re.IGNORECASE)


def _is_masculine_barber(business_name: str, enrichment: dict[str, Any]) -> bool:
    """Whether this prospect reads as a men's barbershop (vs a mixed salon), from its name + category.

    Heuristic (Léo's call): masculine only when a barber signal is present AND no mixed/salon signal is —
    so a clear "Barbier …" is men's, "… Coiffure/Salon" is mixed, and anything ambiguous falls back to the
    neutral (mixed) wording, which is the safe default.
    """
    haystack: str = f"{business_name} {enrichment.get('category', '')}"
    masculine: bool = bool(_MASCULINE_TRADE_RE.search(haystack))
    mixed: bool = bool(_MIXED_TRADE_RE.search(haystack))
    return masculine and not mixed


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
    enr = enrichment or {}
    masculine: bool = _is_masculine_barber(business_name, enr)
    site = map_prospect_and_enrichment(
        business_name=business_name,
        phone=phone,
        email=email,
        city=city,
        area=area,
        subtitle=subtitle,
        palette=palette,
        enrichment=enrichment,
        about_default=_ABOUT_MEN if masculine else _ABOUT_MIXED,
    )
    site["services"] = fixed_trade_services(BARBER_SERVICES)
    site["faq"] = BARBER_FAQ
    site.update(_EDITORIAL_DEFAULTS)
    # Same template, gendered content: a men's barbershop keeps "barbier"/"pour hommes"; a mixed salon
    # (or an ambiguous name) gets neutral wording. ``audience`` lets the layer gender the hero title too.
    site["audience"] = "men" if masculine else "all"
    if not masculine:
        site["aboutHeading"] = "Votre salon de quartier"
        # heroBadge survives the Storyblok round-trip (``audience`` doesn't), so the layer reads it to
        # pick the mixed-salon copy instead of the barbershop wording. "COIFFEUR" for a mixed salon.
        site["heroBadge"] = "COIFFEUR"
    apply_real_trust_stats(site, enrichment)
    # The mid-CTA banner + contact background are dedicated, editable CMS fields now, seeded with the
    # template's own default photos so the client sees them (and can replace them) in Storyblok.
    site["images"] = {"midCta": _DEFAULT_MID_CTA, "contactBackground": _DEFAULT_CONTACT}
    return site
