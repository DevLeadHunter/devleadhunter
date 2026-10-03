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

from typing import Any

from services.templates.site_content import (  # noqa: F401 — re-exported for the registry
    SITE_CONTENT_SCHEMAS,
    fixed_trade_services,
    map_prospect_and_enrichment,
    to_storyblok_site_content,
)
from services.templates.visitor_data import TemplateVisitorData

TEMPLATE_ID: str = "dental"

TEMPLATE_META: dict[str, object] = {
    "id": TEMPLATE_ID,
    "name": "Dentaire Family Care",
    "description": (
        "Vitrine cabinet dentaire : hero sourire, galerie, stats, soins "
        "(général / esthétique / urgences), à propos, équipe, prise de "
        "rendez-vous (mailto). Couleurs thémables via palette, typo El Messiri."
    ),
    "preview_image_url": None,
    "category": "sante",
    "trades": ["dentiste", "dentist", "orthodontiste", "dentaire"],
    "default_theme": {
        "primary": "#b1040e",
        "secondary": "#2e333e",
        "accent": "#80060d",
    },
    # Canonical colour roles → palette key (audit 2026-08-17). Only these roles are editable;
    # keys not listed here don't visibly theme this layer, so the editor hides them.
    "color_roles": {"action": "primary", "secondaire": "secondary"},
}

VISITOR_DATA: TemplateVisitorData = TemplateVisitorData(
    has_contact_form=True,
    has_google_fonts=True,
)

BODY_COMPONENTS: list[str] = []
COMPONENT_SCHEMAS: list[dict[str, Any]] = []

# Sections this template renders — drives the client's Storyblok editor so it shows no dead sections.
# "team" replaces "reviews": the team grid is now fed by dedicated ``teamMembers`` bloks (photo + name +
# role + bio) instead of being repurposed from the reviews blok, and dental renders no testimonials — so a
# "reviews" section would only be a dead editor section.
USED_SECTIONS: list[str] = ["hero", "trust", "about", "services", "gallery", "team", "contact"]

# One-off photos this template renders that aren't hero/about-row-1/gallery — exposed as dedicated, labelled
# Storyblok fields (grouped in the section they appear in), editable by the client via ``SiteContent.images``.
EXTRA_SECTION_IMAGES: dict[str, list[dict[str, str]]] = {
    "about": [{"field": "aboutSecondary", "label": "Photo « nouveaux patients »"}],
}

# Default photos, mirror of the Nuxt layer's STOCK (devleadhunter-template-dental app/types/dental.ts) —
# seeded into the CMS so the client sees them and can replace each one. All absolute (Unsplash) URLs.
# ``aboutSecondary`` is the about row 2 ("nouveaux patients") fallback; the service list gets one image per
# card; the team grid gets a full default roster (photo + name + role + bio).
_DEFAULT_ABOUT_SECONDARY: str = (
    "https://images.unsplash.com/photo-1629909613654-28e377c37b09?auto=format&fit=crop&w=1200&q=80"
)
_DEFAULT_SERVICE_IMAGES: list[str] = [
    "https://images.unsplash.com/photo-1606811841689-23dfddce3e95?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1609840114035-3c981b782dfe?auto=format&fit=crop&w=900&q=80",
    "https://images.unsplash.com/photo-1598256989800-fe5f95da9787?auto=format&fit=crop&w=900&q=80",
]
_TEAM_HEADING: str = "Votre équipe soignante"
_DEFAULT_TEAM_MEMBERS: list[dict[str, str]] = [
    {
        "photo": "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=600&q=80",
        "name": "Dr Sophie Martin",
        "role": "CHIRURGIEN-DENTISTE",
        "bio": "Soins familiaux, prévention et accompagnement au long cours.",
    },
    {
        "photo": "https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&w=600&q=80",
        "name": "Dr Marc Lefèvre",
        "role": "CHIRURGIEN-DENTISTE",
        "bio": "Esthétique du sourire, couronnes et réhabilitation implantaire.",
    },
    {
        "photo": "https://images.unsplash.com/photo-1594824476967-48c8b964273f?auto=format&fit=crop&w=600&q=80",
        "name": "Dr Amina Benali",
        "role": "CHIRURGIEN-DENTISTE",
        "bio": "Soins pédiatriques et premier contact en douceur pour les enfants.",
    },
]


def default_subtitle(area: str) -> str:
    """Dental-aware default hero subtitle when the prospect has no description.

    Args:
        area: Service area / city label.

    Returns:
        A dental clinic subtitle.
    """
    return f"Soins dentaires pour toute la famille à {area} — prévention, esthétique et urgences."


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
            "Contrôles, détartrage, soins cariés et suivi préventif pour toute la famille, du plus jeune au plus âgé."
        ),
    },
    {
        "title": "Esthétique du sourire",
        "description": (
            "Blanchiment, facettes, couronnes et aligners : des résultats naturels pour sourire en confiance."
        ),
    },
    {
        "title": "Urgences dentaires",
        "description": (
            "Douleur, dent cassée ou abcès : contactez-nous rapidement, nous organisons un créneau prioritaire."
        ),
    },
]

DENTAL_FAQ: list[dict[str, str]] = [
    {
        "question": "Faut-il prendre rendez-vous ?",
        "answer": (
            "Oui, de préférence. Appelez ou utilisez le formulaire : nous confirmons le créneau sous 24 h ouvrées."
        ),
    },
    {
        "question": "Acceptez-vous les nouveaux patients ?",
        "answer": ("Oui. Nous accueillons les nouveaux patients pour un bilan complet et un plan de soins adapté."),
    },
    {
        "question": "Quelles mutuelles acceptez-vous ?",
        "answer": (
            "Nous travaillons avec la plupart des complémentaires. Apportez votre carte mutuelle à la première visite."
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
    "heroBadge": "CABINET DENTAIRE",
    "heroPoints": [
        "Prévention & hygiène",
        "Accueil bienveillant",
        "Technologies modernes",
    ],
    "ctaCallLabel": "Prendre rendez-vous",
    "ctaQuoteLabel": "Nos soins",
    "trustItems": [
        {"value": "20+", "label": "Années d'expérience"},
        {"value": "2000+", "label": "Patients suivis"},
        {"value": "5", "label": "Praticiens"},
    ],
    "servicesHeading": "Des soins dentaires de qualité",
    "galleryHeading": "Des sourires pour tous les âges",
    "faqHeading": "Questions fréquentes",
    "aboutHeading": "Votre sourire, notre fierté",
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
    site["services"] = fixed_trade_services(DENTAL_SERVICES)
    site["faq"] = DENTAL_FAQ
    site.update(_EDITORIAL_DEFAULTS)
    # Every remaining photo is a dedicated, editable CMS field now, seeded with the template's own default
    # photos (mirror of dental.ts STOCK) so the client sees them — and can swap each one: the "nouveaux
    # patients" about row, one image per service card, and each practitioner portrait (photo/name/role/bio).
    site["images"] = {"aboutSecondary": _DEFAULT_ABOUT_SECONDARY}
    for index, service in enumerate(site["services"]):
        service["image"] = _DEFAULT_SERVICE_IMAGES[index % len(_DEFAULT_SERVICE_IMAGES)]
    site["teamHeading"] = _TEAM_HEADING
    site["teamMembers"] = [dict(member) for member in _DEFAULT_TEAM_MEMBERS]
    return site
