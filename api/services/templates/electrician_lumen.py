"""
'electrician-lumen' demo template — fully self-contained registration.

First electrician template. Art direction « Nuit électrique » : deep night
background, high-visibility electric yellow, warm amber accent — the site
"powers on" like a breaker being switched back on.

Every blok is namespaced ``lumen_*`` so the Storyblok schemas never collide
with the shared base bloks nor with other templates (the registry dedupes
schemas by name — namespacing keeps this template fully independent).

Enrichment (photos / reviews / rating / opening hours) is injected by
``services.enrichment_content`` which knows the ``lumen_*`` bloks too.

Rendering component (Nuxt): demo-host/app/components/templates/electrician-lumen/.
"""
from __future__ import annotations

from typing import Any, Optional

TEMPLATE_ID: str = "electrician-lumen"

TEMPLATE_META: dict[str, object] = {
    "id": TEMPLATE_ID,
    "name": "Électricien Lumen",
    "description": (
        "Vitrine « nuit électrique » pour électricien : fond nuit, jaune haute-visibilité, "
        "le site s'allume comme on remonte un disjoncteur. Bande dépannage, tableau des "
        "normes animé (NF C 15-100, Consuel), services dont borne IRVE, process, FAQ. "
        "Avis Google, photos, note et horaires injectés automatiquement — et le design "
        "reste impeccable sans aucune photo."
    ),
    "preview_image_url": None,
    "category": "artisan",
    "default_theme": {
        "primary": "#FFD400",
        "secondary": "#070B14",
        "accent": "#FF9F1C",
    },
}

# Top-level bloks this template adds to the Storyblok page body whitelist.
BODY_COMPONENTS: list[str] = [
    "lumen_hero",
    "lumen_trust",
    "lumen_emergency",
    "lumen_services",
    "lumen_safety",
    "lumen_gallery",
    "lumen_process",
    "lumen_reviews",
    "lumen_zone",
    "lumen_faq",
    "lumen_contact",
]

# Storyblok blok schemas specific to this template (all namespaced ``lumen_*``).
COMPONENT_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "lumen_hero",
        "display_name": "Lumen — Hero",
        "schema": {
            "badge": {"type": "text"},
            "title": {"type": "text"},
            "subtitle": {"type": "textarea"},
            "city": {"type": "text"},
            "phone": {"type": "text"},
            "cta_call_label": {"type": "text"},
            "cta_quote_label": {"type": "text"},
            "image": {"type": "text"},
            "image_caption": {"type": "text"},
            "points": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["lumen_hero_point"],
            },
        },
    },
    {
        "name": "lumen_hero_point",
        "display_name": "Lumen — Hero point",
        "schema": {"label": {"type": "text"}},
    },
    {
        "name": "lumen_trust",
        "display_name": "Lumen — Trust strip",
        "schema": {
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["lumen_trust_item"],
            },
        },
    },
    {
        "name": "lumen_trust_item",
        "display_name": "Lumen — Trust item",
        "schema": {
            "value": {"type": "text"},
            "label": {"type": "text"},
        },
    },
    {
        "name": "lumen_emergency",
        "display_name": "Lumen — Emergency band",
        "schema": {
            "heading": {"type": "text"},
            "text": {"type": "textarea"},
            "phone": {"type": "text"},
            "availability_label": {"type": "text"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["lumen_emergency_item"],
            },
        },
    },
    {
        "name": "lumen_emergency_item",
        "display_name": "Lumen — Emergency item",
        "schema": {"label": {"type": "text"}},
    },
    {
        "name": "lumen_services",
        "display_name": "Lumen — Services",
        "schema": {
            "heading": {"type": "text"},
            "subheading": {"type": "textarea"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["lumen_service_item"],
            },
        },
    },
    {
        "name": "lumen_service_item",
        "display_name": "Lumen — Service item",
        "schema": {
            "label": {"type": "text"},
            "description": {"type": "textarea"},
            "icon": {"type": "text"},
        },
    },
    {
        "name": "lumen_safety",
        "display_name": "Lumen — Safety & norms",
        "schema": {
            "kicker": {"type": "text"},
            "heading": {"type": "text"},
            "text": {"type": "textarea"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["lumen_safety_item"],
            },
        },
    },
    {
        "name": "lumen_safety_item",
        "display_name": "Lumen — Safety item",
        "schema": {
            "code": {"type": "text"},
            "label": {"type": "textarea"},
        },
    },
    {
        "name": "lumen_gallery",
        "display_name": "Lumen — Gallery",
        "schema": {
            "heading": {"type": "text"},
            "subheading": {"type": "textarea"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["lumen_gallery_item"],
            },
        },
    },
    {
        "name": "lumen_gallery_item",
        "display_name": "Lumen — Gallery item",
        "schema": {
            "image": {"type": "text"},
            "caption": {"type": "text"},
        },
    },
    {
        "name": "lumen_process",
        "display_name": "Lumen — Process",
        "schema": {
            "heading": {"type": "text"},
            "subheading": {"type": "textarea"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["lumen_process_item"],
            },
        },
    },
    {
        "name": "lumen_process_item",
        "display_name": "Lumen — Process step",
        "schema": {
            "title": {"type": "text"},
            "description": {"type": "textarea"},
        },
    },
    {
        "name": "lumen_reviews",
        "display_name": "Lumen — Reviews",
        "schema": {
            "heading": {"type": "text"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["lumen_review_item"],
            },
        },
    },
    {
        "name": "lumen_review_item",
        "display_name": "Lumen — Review item",
        "schema": {
            "quote": {"type": "textarea"},
            "author": {"type": "text"},
            "rating": {"type": "number"},
        },
    },
    {
        "name": "lumen_zone",
        "display_name": "Lumen — Service area",
        "schema": {
            "heading": {"type": "text"},
            "city": {"type": "text"},
            "area_label": {"type": "text"},
            "note": {"type": "textarea"},
        },
    },
    {
        "name": "lumen_faq",
        "display_name": "Lumen — FAQ",
        "schema": {
            "heading": {"type": "text"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["lumen_faq_item"],
            },
        },
    },
    {
        "name": "lumen_faq_item",
        "display_name": "Lumen — FAQ item",
        "schema": {
            "question": {"type": "text"},
            "answer": {"type": "textarea"},
        },
    },
    {
        "name": "lumen_contact",
        "display_name": "Lumen — Contact",
        "schema": {
            "heading": {"type": "text"},
            "subheading": {"type": "textarea"},
            "phone": {"type": "text"},
            "email": {"type": "text"},
            "city": {"type": "text"},
            "hours": {"type": "text"},
            "cta_label": {"type": "text"},
        },
    },
]


def _place_phrase(area: str) -> str:
    """Phrase de localisation grammaticalement correcte ("à Nantes" / "dans votre secteur")."""
    return f"à {area}" if area and area != "votre secteur" else "dans votre secteur"


def default_subtitle(area: str) -> str:
    """Electrician-flavoured default subtitle (used when the prospect has no description)."""
    return (
        "Dépannage, mise aux normes, rénovation et borne de recharge — "
        f"un travail propre, sécurisé et garanti {_place_phrase(area)}."
    )


def build_content(
    *,
    business_name: str,
    phone: Optional[str],
    email: Optional[str],
    city: Optional[str],
    area: str,
    subtitle: str,
    palette: dict[str, str],
) -> dict[str, Any]:
    """Build the full content_json for the 'electrician-lumen' template.

    Editorial copy is written for a generic French electrician and stays honest:
    no fabricated reviews, stats or photos — those sections are filled by the
    enrichment layer when real data exists, and stay hidden otherwise.
    """
    city_label = city or area
    hero_subtitle = subtitle or default_subtitle(area)

    return {
        "component": "page",
        "theme": palette,
        "body": [
            {
                "_uid": "lumen-hero-1",
                "component": "lumen_hero",
                "badge": f"Artisan électricien — {city_label}" if city_label else "Artisan électricien",
                "title": business_name,
                "subtitle": hero_subtitle,
                "city": city or "",
                "phone": phone or "",
                "cta_call_label": "Appeler maintenant",
                "cta_quote_label": "Demander un devis",
                "image": "",
                "image_caption": f"Chantier récent — {city_label}" if city_label else "Chantier récent",
                "points": [
                    {"_uid": "lumen-hp-0", "component": "lumen_hero_point", "label": "Devis gratuit"},
                    {"_uid": "lumen-hp-1", "component": "lumen_hero_point", "label": "Déplacement rapide"},
                    {"_uid": "lumen-hp-2", "component": "lumen_hero_point", "label": "Travail garanti"},
                ],
            },
            {
                "_uid": "lumen-trust-1",
                "component": "lumen_trust",
                "items": [
                    {
                        "_uid": "lumen-t-0",
                        "component": "lumen_trust_item",
                        "value": "7j/7",
                        "label": "dépannage & urgences",
                    },
                    {
                        "_uid": "lumen-t-1",
                        "component": "lumen_trust_item",
                        "value": "NF C 15-100",
                        "label": "installations aux normes",
                    },
                    {
                        "_uid": "lumen-t-2",
                        "component": "lumen_trust_item",
                        "value": "10 ans",
                        "label": "garantie décennale",
                    },
                    {
                        "_uid": "lumen-t-3",
                        "component": "lumen_trust_item",
                        "value": "< 24 h",
                        "label": "réponse à votre demande",
                    },
                ],
            },
            {
                "_uid": "lumen-emergency-1",
                "component": "lumen_emergency",
                "heading": "Une panne ? On intervient vite.",
                "text": (
                    "Coupure générale, disjoncteur qui saute, prise qui chauffe ou odeur de "
                    "brûlé : ne restez pas dans le doute. Un électricien vous répond, vous "
                    "guide au téléphone et se déplace si nécessaire."
                ),
                "phone": phone or "",
                "availability_label": "7j/7 — week-ends compris",
                "items": [
                    {
                        "_uid": "lumen-e-0",
                        "component": "lumen_emergency_item",
                        "label": "Recherche de panne & remise en service",
                    },
                    {
                        "_uid": "lumen-e-1",
                        "component": "lumen_emergency_item",
                        "label": "Mise en sécurité de l'installation",
                    },
                    {
                        "_uid": "lumen-e-2",
                        "component": "lumen_emergency_item",
                        "label": "Intervention possible le jour même",
                    },
                ],
            },
            {
                "_uid": "lumen-services-1",
                "component": "lumen_services",
                "heading": "Ce qu'on installe, répare et sécurise",
                "subheading": (
                    f"Pour les particuliers et les professionnels, {_place_phrase(area)} — "
                    "du dépannage ponctuel à la rénovation complète."
                ),
                "items": [
                    {
                        "_uid": "lumen-s-0",
                        "component": "lumen_service_item",
                        "label": "Dépannage & recherche de panne",
                        "description": (
                            "Coupures, courts-circuits, disjoncteur qui saute : diagnostic "
                            "précis et remise en service rapide."
                        ),
                        "icon": "panne",
                    },
                    {
                        "_uid": "lumen-s-1",
                        "component": "lumen_service_item",
                        "label": "Tableau électrique & mise aux normes",
                        "description": (
                            "Remplacement de tableau, différentiels 30 mA, mise en "
                            "conformité NF C 15-100 de l'installation."
                        ),
                        "icon": "tableau",
                    },
                    {
                        "_uid": "lumen-s-2",
                        "component": "lumen_service_item",
                        "label": "Rénovation électrique",
                        "description": (
                            "Rénovation partielle ou complète, en site occupé, avec un "
                            "chantier propre et des finitions soignées."
                        ),
                        "icon": "renovation",
                    },
                    {
                        "_uid": "lumen-s-3",
                        "component": "lumen_service_item",
                        "label": "Éclairage & domotique",
                        "description": (
                            "Éclairage LED intérieur et extérieur, variateurs, volets et "
                            "chauffage pilotés depuis votre téléphone."
                        ),
                        "icon": "domotique",
                    },
                    {
                        "_uid": "lumen-s-4",
                        "component": "lumen_service_item",
                        "label": "Borne de recharge (IRVE)",
                        "description": (
                            "Bornes et prises renforcées pour véhicule électrique, "
                            "dimensionnées selon votre tableau et votre abonnement."
                        ),
                        "icon": "irve",
                    },
                    {
                        "_uid": "lumen-s-5",
                        "component": "lumen_service_item",
                        "label": "Interphone & courants faibles",
                        "description": (
                            "Interphone, visiophone, réseau et TV : des équipements bien "
                            "intégrés, réglés et fiables."
                        ),
                        "icon": "interphone",
                    },
                ],
            },
            {
                "_uid": "lumen-safety-1",
                "component": "lumen_safety",
                "kicker": "Sécurité & conformité",
                "heading": "Une installation aux normes, ça ne se négocie pas.",
                "text": (
                    "Une installation vétuste ou mal protégée, c'est un risque d'incendie et "
                    "d'électrocution. Chaque intervention se termine par une vérification "
                    "complète : protections, différentiels, mise à la terre."
                ),
                "items": [
                    {
                        "_uid": "lumen-n-0",
                        "component": "lumen_safety_item",
                        "code": "NF C 15-100",
                        "label": "La norme de référence, appliquée sur toute installation neuve ou rénovée",
                    },
                    {
                        "_uid": "lumen-n-1",
                        "component": "lumen_safety_item",
                        "code": "Consuel",
                        "label": "Attestation de conformité fournie pour les travaux qui l'exigent",
                    },
                    {
                        "_uid": "lumen-n-2",
                        "component": "lumen_safety_item",
                        "code": "30 mA",
                        "label": "Des différentiels qui coupent avant l'accident, sur chaque rangée",
                    },
                    {
                        "_uid": "lumen-n-3",
                        "component": "lumen_safety_item",
                        "code": "Terre",
                        "label": "Mise à la terre mesurée et contrôlée sur chaque circuit",
                    },
                ],
            },
            {
                "_uid": "lumen-gallery-1",
                "component": "lumen_gallery",
                "heading": "Nos chantiers récents",
                "subheading": (
                    "Tableaux, rénovations, éclairages : un aperçu de ce qu'on fait de nos journées."
                ),
                # Filled by enrichment (Google photos). Hidden by the renderer when empty.
                "items": [],
            },
            {
                "_uid": "lumen-process-1",
                "component": "lumen_process",
                "heading": "Comment ça se passe",
                "subheading": "Du premier appel à la remise en service — simple et sans surprise.",
                "items": [
                    {
                        "_uid": "lumen-p-0",
                        "component": "lumen_process_item",
                        "title": "Vous appelez",
                        "description": "On fait le point sur votre besoin, et on vous guide déjà par téléphone.",
                    },
                    {
                        "_uid": "lumen-p-1",
                        "component": "lumen_process_item",
                        "title": "Diagnostic sur place",
                        "description": "On se déplace, on vérifie l'installation et on mesure ce qui doit l'être.",
                    },
                    {
                        "_uid": "lumen-p-2",
                        "component": "lumen_process_item",
                        "title": "Devis clair",
                        "description": "Un chiffrage détaillé et sans surprise, validé avant toute intervention.",
                    },
                    {
                        "_uid": "lumen-p-3",
                        "component": "lumen_process_item",
                        "title": "Intervention propre",
                        "description": "Travail soigné, chantier nettoyé, installation testée devant vous.",
                    },
                ],
            },
            {
                "_uid": "lumen-reviews-1",
                "component": "lumen_reviews",
                "heading": "Ce que disent nos clients",
                # Filled by enrichment (Google reviews). Hidden by the renderer when empty.
                "items": [],
            },
            {
                "_uid": "lumen-zone-1",
                "component": "lumen_zone",
                "heading": "Zone d'intervention",
                "city": city_label,
                "area_label": f"{area} et ses alentours" if city else "",
                "note": "Le déplacement est inclus dans le devis — pas de frais cachés.",
            },
            {
                "_uid": "lumen-faq-1",
                "component": "lumen_faq",
                "heading": "Questions fréquentes",
                "items": [
                    {
                        "_uid": "lumen-f-0",
                        "component": "lumen_faq_item",
                        "question": "Le devis est-il vraiment gratuit ?",
                        "answer": (
                            "Oui. Le déplacement pour établir le devis et le chiffrage sont "
                            "gratuits et sans engagement. Le prix annoncé est le prix payé."
                        ),
                    },
                    {
                        "_uid": "lumen-f-1",
                        "component": "lumen_faq_item",
                        "question": "En combien de temps pouvez-vous intervenir ?",
                        "answer": (
                            "Pour un dépannage, l'objectif est d'intervenir dans la journée "
                            "selon l'urgence et le planning. Pour des travaux, une date est "
                            "fixée ensemble dès la validation du devis."
                        ),
                    },
                    {
                        "_uid": "lumen-f-2",
                        "component": "lumen_faq_item",
                        "question": "Mon installation est ancienne, faut-il tout refaire ?",
                        "answer": (
                            "Pas forcément. Après un diagnostic, on distingue ce qui doit être "
                            "mis en sécurité immédiatement de ce qui peut être planifié. Vous "
                            "décidez, en connaissance de cause."
                        ),
                    },
                    {
                        "_uid": "lumen-f-3",
                        "component": "lumen_faq_item",
                        "question": "Vos travaux sont-ils garantis ?",
                        "answer": (
                            "Oui. Les travaux sont couverts par la garantie décennale et une "
                            "assurance responsabilité civile professionnelle. Les équipements "
                            "posés conservent leur garantie fabricant."
                        ),
                    },
                    {
                        "_uid": "lumen-f-4",
                        "component": "lumen_faq_item",
                        "question": "Installez-vous des bornes pour véhicule électrique ?",
                        "answer": (
                            "Oui, bornes et prises renforcées (IRVE). On dimensionne la "
                            "solution selon votre tableau, votre abonnement et votre véhicule."
                        ),
                    },
                ],
            },
            {
                "_uid": "lumen-contact-1",
                "component": "lumen_contact",
                "heading": "Parlons de votre projet",
                "subheading": (
                    "Décrivez votre besoin — vous recevez une réponse rapide et un devis gratuit."
                ),
                "phone": phone or "",
                "email": email or "",
                "city": city_label,
                "hours": "",
                "cta_label": "Appeler maintenant",
            },
        ],
    }


# --- Phase 4b: flat SiteContent path (shared with the other migrated templates) ------------
from .site_content import (  # noqa: E402, F401
    ELECTRICIAN_FAQ,
    ELECTRICIAN_SERVICES,
    SITE_CONTENT_SCHEMAS,
    map_prospect_and_enrichment,
    to_storyblok_site_content,
)

_SITE_ABOUT_DEFAULT: str = (
    "Électricien qualifié à votre service pour vos dépannages, installations et mises aux "
    "normes. Travail conforme, soigné et sécurisé, avec un diagnostic clair et un prix juste."
)


# Editorial copy pre-filled into the CMS so the client sees (and edits) his real
# texts instead of blank fields silently falling back to template defaults.
# Values mirror the layer defaults of devleadhunter-template-electrician-lumen.
_EDITORIAL_DEFAULTS: dict[str, Any] = {
    "heroBadge": "Artisan électricien",
    "heroPoints": ["Devis gratuit", "Intervention rapide", "Travail garanti"],
    "ctaCallLabel": "Appeler maintenant",
    "ctaQuoteLabel": "Demander un devis",
    "trustItems": [
        {"value": "7j/7", "label": "Dépannage & urgences"},
        {"value": "NF C 15-100", "label": "Installations aux normes"},
        {"value": "Garantie décennale", "label": "Travaux assurés"},
        {"value": "Devis 0 €", "label": "Sans engagement"},
    ],
    "servicesHeading": "Nos services",
    "galleryHeading": "Nos chantiers récents",
    "reviewsHeading": "Ce que disent nos clients",
    "faqHeading": "Questions fréquentes",
    "aboutHeading": "Une installation sûre, aux normes",
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
    """Build the flat ``SiteContent`` for this template (Phase 4b).

    Prospect fields + enrichment map through the shared helper; services come from the
    scraped enrichment services when present, else the trade editorial defaults; the template
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
    site["services"] = scraped or ELECTRICIAN_SERVICES
    site["faq"] = ELECTRICIAN_FAQ
    # Pre-fill editorial copy (client edits his real texts in the CMS).
    site.update(_EDITORIAL_DEFAULTS)
    return site
