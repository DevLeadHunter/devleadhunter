"""
'plumber-cuivre' demo template — self-contained registration.

Retail name « Plombier Source » — art direction « Source »: a clean, fresh
plumber showcase (near-white water-tinted background, deep marine ink, vivid
water blue and turquoise accents, sturdy display type and pill buttons).
Flat ``SiteContent`` path only — Storyblok uses the shared ``site_content``
blok family; the Nuxt layer is ``devleadhunter-template-plumber-cuivre``.

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

TEMPLATE_ID: str = "plumber-cuivre"

TEMPLATE_META: dict[str, object] = {
    "id": TEMPLATE_ID,
    "name": "Plombier Source",
    "description": (
        "Vitrine claire et fraîche pour plombier : bleu eau, blanc et turquoise, "
        "manchette, services en liste numérotée, encart urgence marine, section "
        "« votre plombier », règles de l'art, marques posées, méthode en timeline, "
        "secteur entouré au trait. Avis Google, photos, note et horaires injectés "
        "automatiquement — impeccable même sans aucune photo."
    ),
    "preview_image_url": None,
    "category": "artisan",
    "trades": ["plombier", "plumber", "chauffagiste", "plomberie"],
    "default_theme": {
        "primary": "#1080B4",
        "secondary": "#10293D",
        "accent": "#22A8C4",
    },
    # Canonical colour roles → palette key (audit 2026-08-17). Only these roles are editable;
    # keys not listed here don't visibly theme this layer, so the editor hides them.
    "color_roles": {"action": "primary", "fond": "secondary", "secondaire": "accent"},
}

# Shared base bloks only (flat SiteContent) — like every other template.
BODY_COMPONENTS: list[str] = []
COMPONENT_SCHEMAS: list[dict[str, Any]] = []

# Sections this template renders — drives the client's Storyblok editor so it shows no dead sections.
USED_SECTIONS: list[str] = ["hero", "trust", "about", "services", "gallery", "reviews", "faq", "contact"]


def _place_phrase(area: str) -> str:
    """Phrase de localisation grammaticalement correcte ("à Rennes" / "dans votre secteur")."""
    return f"à {area}" if area and area != "votre secteur" else "dans votre secteur"


def default_subtitle(area: str) -> str:
    """Plumber-flavoured default subtitle for this template (no prospect description)."""
    return (
        "Dépannage, débouchage, chauffe-eau et salle de bain — un travail propre, "
        f"garanti, au juste prix {_place_phrase(area)}."
    )


# Editorial copy this template owns — services / FAQ / about, consumed by build_site_content.

# Services (label + description) — the "table of contents" list of the template.
_SERVICE_ITEMS: list[dict[str, str]] = [
    {
        "label": "Dépannage & recherche de fuite",
        "description": ("Fuites visibles ou cachées : détection précise, réparation durable, dégâts limités."),
    },
    {
        "label": "Débouchage de canalisations",
        "description": (
            "WC, éviers, douches, colonnes : un débouchage propre, au furet "
            "ou à la pompe, sans abîmer vos installations."
        ),
    },
    {
        "label": "Chauffe-eau & ballon",
        "description": (
            "Remplacement, entretien et réglage — de l'électrique au thermodynamique, dimensionné pour votre foyer."
        ),
    },
    {
        "label": "Chauffage & radiateurs",
        "description": (
            "Purge, équilibrage, remplacement de radiateurs et raccordements — pour un hiver sans mauvaise surprise."
        ),
    },
    {
        "label": "Salle de bain clé en main",
        "description": (
            "De la dépose à la pose finale : douche, baignoire, meubles — coordonné avec les bons corps de métier."
        ),
    },
    {
        "label": "Robinetterie & sanitaires",
        "description": ("Pose et remplacement de robinets, WC, éviers — des marques fiables, posées dans les règles."),
    },
    {
        "label": "Cuisine & électroménager",
        "description": (
            "Évier, lave-vaisselle, lave-linge : arrivées d'eau, évacuations "
            "et pose soignée, sans fuite au premier cycle."
        ),
    },
    {
        "label": "Entretien & mise en conformité",
        "description": (
            "Adoucisseur, groupe de sécurité, arrivées d'eau : une installation saine, durable et aux normes."
        ),
    },
]

# FAQ (question + answer).
_FAQ_ITEMS: list[dict[str, str]] = [
    {
        "question": "Le devis est-il vraiment gratuit ?",
        "answer": (
            "Oui. Le déplacement pour constater et le chiffrage sont "
            "gratuits et sans engagement. Le prix validé ensemble est le "
            "prix payé."
        ),
    },
    {
        "question": "En combien de temps intervenez-vous pour une fuite ?",
        "answer": (
            "Les urgences passent en priorité : l'objectif est d'intervenir "
            "dans la journée. Au téléphone, on vous donne aussi les premiers "
            "gestes pour limiter les dégâts."
        ),
    },
    {
        "question": "Travaillez-vous avec les assurances en cas de dégât des eaux ?",
        "answer": (
            "Oui. On vous fournit les éléments nécessaires à votre dossier "
            "(constat, factures, photos) et, si besoin, une recherche de "
            "fuite documentée."
        ),
    },
    {
        "question": "Vos travaux sont-ils garantis ?",
        "answer": (
            "Oui. Les travaux sont couverts par la garantie décennale et une "
            "assurance responsabilité civile professionnelle ; le matériel "
            "posé conserve sa garantie fabricant."
        ),
    },
    {
        "question": "Pouvez-vous rénover une salle de bain complète ?",
        "answer": (
            "Oui, en coordonnant les corps de métier nécessaires (carrelage, "
            "électricité) pour livrer une salle de bain terminée, prête à "
            "utiliser."
        ),
    },
    {
        "question": "Quels moyens de paiement acceptez-vous ?",
        "answer": (
            "Carte, virement ou chèque, avec une facture détaillée remise "
            "après chaque intervention. Pour les gros chantiers, un "
            "échéancier peut être convenu au devis."
        ),
    },
    {
        "question": "Quels délais pour des travaux planifiés ?",
        "answer": (
            "Après validation du devis, une date est calée ensemble — en "
            "général sous une à trois semaines selon la saison et l'ampleur "
            "du chantier. La date convenue est tenue."
        ),
    },
    {
        "question": "Intervenez-vous pour les copropriétés et les professionnels ?",
        "answer": (
            "Oui : syndics, gestionnaires, commerces et petites entreprises. "
            "Interventions documentées (photos, rapport) et facturation "
            "adaptée."
        ),
    },
]

# Editorial "about the plumber" text (used when the prospect has no description).
_ABOUT_TEXT: str = (
    "Quand vous appelez, c'est un plombier qui répond — pas un centre "
    "d'appels. Le diagnostic est honnête, le devis est clair, et le travail "
    "est fait avec le même soin que s'il s'agissait de notre propre maison. "
    "Vous savez toujours qui entre chez vous, ce qui sera fait, et pour "
    "quel prix."
)

_ABOUT_TEXT_SHORT: str = _ABOUT_TEXT


# Editorial copy pre-filled into the CMS so the client sees (and edits) his real
# texts instead of blank fields silently falling back to template defaults.
# Values mirror the layer defaults of devleadhunter-template-plumber-cuivre.
_EDITORIAL_DEFAULTS: dict[str, Any] = {
    "heroBadge": "Artisan plombier",
    "heroPoints": ["Devis gratuit", "Intervention rapide", "Travail garanti"],
    "ctaCallLabel": "Appeler maintenant",
    "ctaQuoteLabel": "Demander un devis",
    "trustItems": [
        {"value": "7j/7", "label": "Dépannage & urgences"},
        {"value": "Garantie décennale", "label": "Travaux assurés"},
        {"value": "Devis gratuit", "label": "Sans engagement"},
        {"value": "Artisan local", "label": "Proche de chez vous"},
    ],
    "servicesHeading": "Nos services",
    "galleryHeading": "Nos chantiers récents",
    "reviewsHeading": "Ce que disent nos clients",
    "faqHeading": "Questions fréquentes",
    "aboutHeading": "Un artisan, pas une plateforme",
    "contactHeading": "Parlons de votre projet",
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

    Prospect fields + enrichment map through the shared helper; services and FAQ come from this
    template's editorial copy; the layer supplies section headings. See ``site_content.py``.
    """
    site = map_prospect_and_enrichment(
        business_name=business_name,
        phone=phone,
        email=email,
        city=city,
        area=area,
        subtitle=subtitle or default_subtitle(area),
        palette=palette,
        enrichment=enrichment,
        about_default=_ABOUT_TEXT_SHORT,
    )
    site["services"] = [{"title": item["label"], "description": item["description"]} for item in _SERVICE_ITEMS]
    site["faq"] = [{"question": item["question"], "answer": item["answer"]} for item in _FAQ_ITEMS]
    site.update(_EDITORIAL_DEFAULTS)
    return site
