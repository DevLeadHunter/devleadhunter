"""
'plumber-cuivre' demo template — fully self-contained registration.

Retail name « Plombier Source » — art direction « Source » : a clean, fresh
plumber showcase — near-white water-tinted background, deep marine ink, vivid
water blue and turquoise accents, sturdy friendly display type and pill
buttons. (``cuivre`` remains the internal codename of this template: ids,
blok names and CSS prefixes keep it so nothing breaks across the stack.)

Every blok is namespaced ``cuivre_*`` so the Storyblok schemas never collide
with the shared base bloks nor with other templates (the registry dedupes
schemas by name — namespacing keeps this template fully independent).

Enrichment (photos / reviews / rating / opening hours) is injected by
``services.enrichment_content`` which knows the ``cuivre_*`` bloks too.

Rendering component (Nuxt): demo-host/app/components/templates/plumber-cuivre/.
"""

from __future__ import annotations

import uuid
from typing import Any

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
    "default_theme": {
        "primary": "#1080B4",
        "secondary": "#10293D",
        "accent": "#22A8C4",
    },
}

# Top-level bloks this template adds to the Storyblok page body whitelist.
BODY_COMPONENTS: list[str] = [
    "cuivre_hero",
    "cuivre_trust",
    "cuivre_emergency",
    "cuivre_services",
    "cuivre_craft",
    "cuivre_about",
    "cuivre_gallery",
    "cuivre_process",
    "cuivre_reviews",
    "cuivre_brands",
    "cuivre_zone",
    "cuivre_faq",
    "cuivre_contact",
]

# Storyblok blok schemas specific to this template (all namespaced ``cuivre_*``).
COMPONENT_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "cuivre_hero",
        "display_name": "Source — Hero",
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
                "component_whitelist": ["cuivre_hero_point"],
            },
        },
    },
    {
        "name": "cuivre_hero_point",
        "display_name": "Source — Hero point",
        "schema": {"label": {"type": "text"}},
    },
    {
        "name": "cuivre_trust",
        "display_name": "Source — Trust band",
        "schema": {
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["cuivre_trust_item"],
            },
        },
    },
    {
        "name": "cuivre_trust_item",
        "display_name": "Source — Trust item",
        "schema": {
            "value": {"type": "text"},
            "label": {"type": "text"},
        },
    },
    {
        "name": "cuivre_emergency",
        "display_name": "Source — Emergency card",
        "schema": {
            "heading": {"type": "text"},
            "text": {"type": "textarea"},
            "phone": {"type": "text"},
            "availability_label": {"type": "text"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["cuivre_emergency_item"],
            },
        },
    },
    {
        "name": "cuivre_emergency_item",
        "display_name": "Source — Emergency item",
        "schema": {"label": {"type": "text"}},
    },
    {
        "name": "cuivre_services",
        "display_name": "Source — Services index",
        "schema": {
            "heading": {"type": "text"},
            "subheading": {"type": "textarea"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["cuivre_service_item"],
            },
        },
    },
    {
        "name": "cuivre_service_item",
        "display_name": "Source — Service item",
        "schema": {
            "label": {"type": "text"},
            "description": {"type": "textarea"},
        },
    },
    {
        "name": "cuivre_craft",
        "display_name": "Source — Rules of the craft",
        "schema": {
            "kicker": {"type": "text"},
            "heading": {"type": "text"},
            "text": {"type": "textarea"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["cuivre_craft_item"],
            },
        },
    },
    {
        "name": "cuivre_craft_item",
        "display_name": "Source — Craft item",
        "schema": {
            "label": {"type": "text"},
            "description": {"type": "textarea"},
        },
    },
    {
        "name": "cuivre_about",
        "display_name": "Source — About the plumber",
        "schema": {
            "kicker": {"type": "text"},
            "heading": {"type": "text"},
            "text": {"type": "textarea"},
            "image": {"type": "text"},
            "image_caption": {"type": "text"},
            "points": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["cuivre_about_point"],
            },
        },
    },
    {
        "name": "cuivre_about_point",
        "display_name": "Source — About point",
        "schema": {"label": {"type": "text"}},
    },
    {
        "name": "cuivre_gallery",
        "display_name": "Source — Gallery",
        "schema": {
            "heading": {"type": "text"},
            "subheading": {"type": "textarea"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["cuivre_gallery_item"],
            },
        },
    },
    {
        "name": "cuivre_gallery_item",
        "display_name": "Source — Gallery item",
        "schema": {
            "image": {"type": "text"},
            "caption": {"type": "text"},
        },
    },
    {
        "name": "cuivre_process",
        "display_name": "Source — Process",
        "schema": {
            "heading": {"type": "text"},
            "subheading": {"type": "textarea"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["cuivre_process_item"],
            },
        },
    },
    {
        "name": "cuivre_process_item",
        "display_name": "Source — Process step",
        "schema": {
            "title": {"type": "text"},
            "description": {"type": "textarea"},
        },
    },
    {
        "name": "cuivre_reviews",
        "display_name": "Source — Reviews",
        "schema": {
            "heading": {"type": "text"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["cuivre_review_item"],
            },
        },
    },
    {
        "name": "cuivre_review_item",
        "display_name": "Source — Review item",
        "schema": {
            "quote": {"type": "textarea"},
            "author": {"type": "text"},
            "rating": {"type": "number"},
        },
    },
    {
        "name": "cuivre_brands",
        "display_name": "Source — Brands",
        "schema": {
            "heading": {"type": "text"},
            "subheading": {"type": "textarea"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["cuivre_brand_item"],
            },
        },
    },
    {
        "name": "cuivre_brand_item",
        "display_name": "Source — Brand item",
        "schema": {"label": {"type": "text"}},
    },
    {
        "name": "cuivre_zone",
        "display_name": "Source — Service area",
        "schema": {
            "heading": {"type": "text"},
            "city": {"type": "text"},
            "area_label": {"type": "text"},
            "note": {"type": "textarea"},
        },
    },
    {
        "name": "cuivre_faq",
        "display_name": "Source — FAQ",
        "schema": {
            "heading": {"type": "text"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["cuivre_faq_item"],
            },
        },
    },
    {
        "name": "cuivre_faq_item",
        "display_name": "Source — FAQ item",
        "schema": {
            "question": {"type": "text"},
            "answer": {"type": "textarea"},
        },
    },
    {
        "name": "cuivre_contact",
        "display_name": "Source — Contact",
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
    """Phrase de localisation grammaticalement correcte ("à Rennes" / "dans votre secteur")."""
    return f"à {area}" if area and area != "votre secteur" else "dans votre secteur"


def default_subtitle(area: str) -> str:
    """Plumber-flavoured default subtitle for this template (no prospect description)."""
    return (
        "Dépannage, débouchage, chauffe-eau et salle de bain — un travail propre, "
        f"garanti, au juste prix {_place_phrase(area)}."
    )


# Shared editorial copy — the honest, generic plumber content this template owns.
# Both the rich ``build_content`` and the flat ``build_site_content`` reference
# these so the two paths render the exact same services / FAQ / about copy.

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


def build_content(
    *,
    business_name: str,
    phone: str | None,
    email: str | None,
    city: str | None,
    area: str,
    subtitle: str,
    palette: dict[str, str],
) -> dict[str, Any]:
    """Build the full content_json for the 'plumber-cuivre' (« Plombier Source ») template.

    Editorial copy is written for a generic French plumber and stays honest:
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
                "_uid": "cuivre-hero-1",
                "component": "cuivre_hero",
                "badge": f"Artisan plombier — {city_label}" if city_label else "Artisan plombier",
                "title": business_name,
                "subtitle": hero_subtitle,
                "city": city or "",
                "phone": phone or "",
                "cta_call_label": "Appeler maintenant",
                "cta_quote_label": "Demander un devis",
                "image": "",
                "image_caption": f"Chantier récent — {city_label}" if city_label else "Chantier récent",
                "points": [
                    {"_uid": "cuivre-hp-0", "component": "cuivre_hero_point", "label": "Devis gratuit"},
                    {"_uid": "cuivre-hp-1", "component": "cuivre_hero_point", "label": "Prix annoncé avant travaux"},
                    {"_uid": "cuivre-hp-2", "component": "cuivre_hero_point", "label": "Chantier laissé propre"},
                ],
            },
            {
                "_uid": "cuivre-trust-1",
                "component": "cuivre_trust",
                "items": [
                    {
                        "_uid": "cuivre-t-0",
                        "component": "cuivre_trust_item",
                        "value": "7j/7",
                        "label": "dépannage & urgences",
                    },
                    {
                        "_uid": "cuivre-t-1",
                        "component": "cuivre_trust_item",
                        "value": "10 ans",
                        "label": "garantie décennale",
                    },
                    {
                        "_uid": "cuivre-t-2",
                        "component": "cuivre_trust_item",
                        "value": "0 €",
                        "label": "le devis, toujours gratuit",
                    },
                    {
                        "_uid": "cuivre-t-3",
                        "component": "cuivre_trust_item",
                        "value": "< 24 h",
                        "label": "réponse à votre demande",
                    },
                ],
            },
            {
                "_uid": "cuivre-emergency-1",
                "component": "cuivre_emergency",
                "heading": "Une fuite ? Réagissez vite, on s'occupe du reste.",
                "text": (
                    "Fuite d'eau, dégât des eaux, canalisation bouchée ou ballon en panne : "
                    "coupez l'eau, appelez — un plombier vous guide au téléphone et "
                    "intervient rapidement."
                ),
                "phone": phone or "",
                "availability_label": "7j/7 — week-ends compris",
                "items": [
                    {
                        "_uid": "cuivre-e-0",
                        "component": "cuivre_emergency_item",
                        "label": "Recherche de fuite sans casse inutile",
                    },
                    {
                        "_uid": "cuivre-e-1",
                        "component": "cuivre_emergency_item",
                        "label": "Débouchage et remise en service",
                    },
                    {
                        "_uid": "cuivre-e-2",
                        "component": "cuivre_emergency_item",
                        "label": "Intervention possible le jour même",
                    },
                ],
            },
            {
                "_uid": "cuivre-services-1",
                "component": "cuivre_services",
                "heading": "Ce qu'on répare, pose et rénove",
                "subheading": (
                    f"Pour les particuliers et les professionnels, {_place_phrase(area)} — "
                    "de la fuite réparée dans l'heure à la salle de bain livrée clé en main."
                ),
                "items": [
                    {
                        "_uid": f"cuivre-s-{index}",
                        "component": "cuivre_service_item",
                        "label": item["label"],
                        "description": item["description"],
                    }
                    for index, item in enumerate(_SERVICE_ITEMS)
                ],
            },
            {
                "_uid": "cuivre-craft-1",
                "component": "cuivre_craft",
                "kicker": "Les règles de l'art",
                "heading": "Un chantier bien fait, ça se voit aux détails.",
                "text": (
                    "Derrière chaque intervention, il y a des gestes de métier : protéger "
                    "les lieux, poser du matériel de qualité, tester l'étanchéité, et "
                    "laisser le chantier plus propre qu'en arrivant."
                ),
                "items": [
                    {
                        "_uid": "cuivre-c-0",
                        "component": "cuivre_craft_item",
                        "label": "Matériel de qualité",
                        "description": "Cuivre, laiton et marques éprouvées — pas de premier prix qui lâche dans deux ans.",
                    },
                    {
                        "_uid": "cuivre-c-1",
                        "component": "cuivre_craft_item",
                        "label": "Étanchéité testée",
                        "description": "Chaque raccord est mis en pression et contrôlé avant de refermer.",
                    },
                    {
                        "_uid": "cuivre-c-2",
                        "component": "cuivre_craft_item",
                        "label": "Chantier protégé",
                        "description": "Sols bâchés, meubles couverts, évacuation des gravats comprise.",
                    },
                    {
                        "_uid": "cuivre-c-3",
                        "component": "cuivre_craft_item",
                        "label": "Règles de l'art",
                        "description": "Des installations conformes aux DTU et aux normes en vigueur.",
                    },
                ],
            },
            {
                "_uid": "cuivre-about-1",
                "component": "cuivre_about",
                "kicker": "Votre plombier",
                "heading": "Un artisan d'ici, pas une plateforme.",
                "text": _ABOUT_TEXT,
                "image": "",
                "image_caption": f"Au travail — {city_label}" if city_label else "Au travail",
                "points": [
                    {
                        "_uid": "cuivre-a-0",
                        "component": "cuivre_about_point",
                        "label": "Artisan assuré — RC Pro & garantie décennale",
                    },
                    {
                        "_uid": "cuivre-a-1",
                        "component": "cuivre_about_point",
                        "label": "Réponse sous 24 h, devis détaillé sous 48 h",
                    },
                    {
                        "_uid": "cuivre-a-2",
                        "component": "cuivre_about_point",
                        "label": "Conseils francs : on ne vend que ce qui est utile",
                    },
                ],
            },
            {
                "_uid": "cuivre-gallery-1",
                "component": "cuivre_gallery",
                "heading": "Nos chantiers récents",
                "subheading": ("Salles de bain, chaufferies, cuisines : un aperçu de nos derniers chantiers."),
                # Filled by enrichment (Google photos). Hidden by the renderer when empty.
                "items": [],
            },
            {
                "_uid": "cuivre-process-1",
                "component": "cuivre_process",
                "heading": "Comment ça se passe",
                "subheading": "Du premier appel à la remise en eau — simple et sans surprise.",
                "items": [
                    {
                        "_uid": "cuivre-p-0",
                        "component": "cuivre_process_item",
                        "title": "Vous appelez",
                        "description": (
                            "On qualifie votre besoin et, en urgence, on vous donne les premiers gestes au téléphone."
                        ),
                    },
                    {
                        "_uid": "cuivre-p-1",
                        "component": "cuivre_process_item",
                        "title": "Visite & devis",
                        "description": (
                            "On se déplace, on constate, et vous recevez un devis clair, gratuit et détaillé."
                        ),
                    },
                    {
                        "_uid": "cuivre-p-2",
                        "component": "cuivre_process_item",
                        "title": "Intervention",
                        "description": ("Travail soigné, matériel de qualité, étanchéité testée avant de refermer."),
                    },
                    {
                        "_uid": "cuivre-p-3",
                        "component": "cuivre_process_item",
                        "title": "Contrôle & nettoyage",
                        "description": "On vérifie tout avec vous et on laisse le chantier propre.",
                    },
                ],
            },
            {
                "_uid": "cuivre-reviews-1",
                "component": "cuivre_reviews",
                "heading": "Ce que disent nos clients",
                # Filled by enrichment (Google reviews). Hidden by the renderer when empty.
                "items": [],
            },
            {
                "_uid": "cuivre-brands-1",
                "component": "cuivre_brands",
                "heading": "Du matériel qui dure",
                "subheading": (
                    "Des marques couramment posées et garanties — choisies pour leur fiabilité, pas pour la marge."
                ),
                "items": [
                    {"_uid": "cuivre-b-0", "component": "cuivre_brand_item", "label": "Grohe"},
                    {"_uid": "cuivre-b-1", "component": "cuivre_brand_item", "label": "Hansgrohe"},
                    {"_uid": "cuivre-b-2", "component": "cuivre_brand_item", "label": "Geberit"},
                    {"_uid": "cuivre-b-3", "component": "cuivre_brand_item", "label": "Jacob Delafon"},
                    {"_uid": "cuivre-b-4", "component": "cuivre_brand_item", "label": "Atlantic"},
                    {"_uid": "cuivre-b-5", "component": "cuivre_brand_item", "label": "Thermor"},
                    {"_uid": "cuivre-b-6", "component": "cuivre_brand_item", "label": "De Dietrich"},
                    {"_uid": "cuivre-b-7", "component": "cuivre_brand_item", "label": "Villeroy & Boch"},
                ],
            },
            {
                "_uid": "cuivre-zone-1",
                "component": "cuivre_zone",
                "heading": "Secteur d'intervention",
                "city": city_label,
                "area_label": f"{area} et ses alentours" if city else "",
                "note": "Le déplacement est inclus dans le devis — pas de frais cachés.",
            },
            {
                "_uid": "cuivre-faq-1",
                "component": "cuivre_faq",
                "heading": "Questions fréquentes",
                "items": [
                    {
                        "_uid": f"cuivre-f-{index}",
                        "component": "cuivre_faq_item",
                        "question": item["question"],
                        "answer": item["answer"],
                    }
                    for index, item in enumerate(_FAQ_ITEMS)
                ],
            },
            {
                "_uid": "cuivre-contact-1",
                "component": "cuivre_contact",
                "heading": "Parlons de votre projet",
                "subheading": (
                    "Une fuite, un chauffe-eau, une salle de bain : décrivez votre besoin, "
                    "vous recevez une réponse rapide et un devis gratuit."
                ),
                "phone": phone or "",
                "email": email or "",
                "city": city_label,
                "hours": "",
                "cta_label": "Appeler maintenant",
            },
        ],
    }


# Phase 4b — flat SiteContent path
#
# The contract with the demo-host template layer (@devleadhunter/website-content):
# the API produces a FLAT ``SiteContent`` (plain object, image URLs as strings,
# arrays of plain objects). The template layer owns all editorial copy (section
# headings, craft/process/brands/emergency, trust items…) and hides any section
# whose SiteContent array is empty — so the variable fields it DOES consume
# (services, faq, reviews, gallery, hours, about, palette…) must be provided here
# for the rendered page to match the historical rich look.

# Short editorial default (used when the prospect has no enrichment description).
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
        {"value": "Devis 0 €", "label": "Sans engagement"},
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
    """Build the FLAT ``SiteContent`` dict for the 'plumber-cuivre' template.

    Variable prospect data (services, faq, reviews, gallery, opening hours, about,
    palette, contact) is emitted here; the template layer supplies section
    headings and all remaining boilerplate.

    Enrichment (all keys optional) is consumed directly:
    - ``photos`` (URL strings): ``[0]`` → heroImage, ``[1]`` → aboutImage,
      ``[2:]`` → gallery items (``{url, alt}``).
    - ``reviews`` (``[{text, author, rating}]``) → reviews (``{author, rating, text}``).
    - ``opening_hours`` (``[{day, hours}]``) → openingHours (same shape).
    - ``description`` → about (falls back to the template's editorial about text).

    Images stay plain external URLs (Google photos are never uploaded assets).

    Returns:
        A flat ``SiteContent`` object (see ``@devleadhunter/website-content``).
    """
    enrichment = enrichment or {}

    photos: list[str] = [p for p in enrichment.get("photos", []) if isinstance(p, str) and p.strip()]
    raw_reviews: list[dict] = [r for r in enrichment.get("reviews", []) if isinstance(r, dict)]
    raw_hours: list[dict] = [h for h in enrichment.get("opening_hours", []) if isinstance(h, dict)]
    description: str | None = enrichment.get("description")

    hero_image: str = photos[0] if len(photos) > 0 else ""
    about_image: str = photos[1] if len(photos) > 1 else ""
    gallery: list[dict[str, str]] = [{"url": url, "alt": ""} for url in photos[2:]]

    reviews: list[dict[str, Any]] = []
    for review in raw_reviews:
        text: str = str(review.get("text", "")).strip()
        if not text:
            continue
        rating_value = review.get("rating")
        entry: dict[str, Any] = {
            "author": str(review.get("author", "")).strip() or "Client",
            "text": text,
        }
        if isinstance(rating_value, (int, float)):
            entry["rating"] = int(rating_value)
        reviews.append(entry)

    opening_hours: list[dict[str, str]] = []
    for row in raw_hours:
        day: str = str(row.get("day", "")).strip()
        hours: str = str(row.get("hours", "")).strip()
        if not day and not hours:
            continue
        opening_hours.append({"day": day, "hours": hours})

    about: str = description.strip() if isinstance(description, str) and description.strip() else _ABOUT_TEXT_SHORT

    # zone.city renders from ``city``; keep it non-empty even when only the area is
    # known, so the "service area" section stays visible (matches the rich builder,
    # which used ``city or area`` for the zone city). areaLabel mirrors the rich
    # builder's "<area> et ses alentours" when a real city is present.
    site_city: str = city or area
    area_label: str = f"{area} et ses alentours" if city else ""

    return {
        "businessName": business_name,
        "phone": phone or "",
        "email": email or "",
        "city": site_city,
        "area": area_label,
        "subtitle": subtitle or default_subtitle(area),
        "about": about,
        "heroImage": hero_image,
        "aboutImage": about_image,
        "gallery": gallery,
        "palette": {
            "primary": palette.get("primary", ""),
            "secondary": palette.get("secondary", ""),
            "accent": palette.get("accent", ""),
        },
        "services": [{"title": item["label"], "description": item["description"]} for item in _SERVICE_ITEMS],
        "reviews": reviews,
        "faq": [{"question": item["question"], "answer": item["answer"]} for item in _FAQ_ITEMS],
        "openingHours": opening_hours,
        # Pre-fill editorial copy (client edits his real texts in the CMS).
        **_EDITORIAL_DEFAULTS,
    }


# Storyblok blok schemas for the native ``site_content`` representation (Phase 4b).
# The flat SiteContent expressed as editable bloks so the Visual Editor can reach
# every field: scalars as text/textarea, image URLs as text (external URLs), and
# arrays as nested bloks. Namespaced ``site_content_*`` — no collision with the
# rich ``cuivre_*`` bloks nor the shared base bloks.
SITE_CONTENT_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "site_content",
        "display_name": "Site content",
        "schema": {
            "businessName": {"type": "text"},
            "phone": {"type": "text"},
            "email": {"type": "text"},
            "city": {"type": "text"},
            "area": {"type": "text"},
            "subtitle": {"type": "textarea"},
            "about": {"type": "textarea"},
            "heroImage": {"type": "text"},
            "aboutImage": {"type": "text"},
            "gallery": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["site_content_gallery_item"],
            },
            "palette": {
                "type": "blok",
                "restrict_components": True,
                "component_whitelist": ["theme_palette"],
                "maximum": 1,
            },
            "services": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["site_content_service"],
            },
            "reviews": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["site_content_review"],
            },
            "faq": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["site_content_faq"],
            },
            "openingHours": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["site_content_hours"],
            },
        },
    },
    {
        "name": "site_content_service",
        "display_name": "Site content — Service",
        "schema": {
            "title": {"type": "text"},
            "description": {"type": "textarea"},
        },
    },
    {
        "name": "site_content_review",
        "display_name": "Site content — Review",
        "schema": {
            "author": {"type": "text"},
            "rating": {"type": "number"},
            "text": {"type": "textarea"},
        },
    },
    {
        "name": "site_content_faq",
        "display_name": "Site content — FAQ item",
        "schema": {
            "question": {"type": "text"},
            "answer": {"type": "textarea"},
        },
    },
    {
        "name": "site_content_hours",
        "display_name": "Site content — Opening hours",
        "schema": {
            "day": {"type": "text"},
            "hours": {"type": "text"},
        },
    },
    {
        "name": "site_content_gallery_item",
        "display_name": "Site content — Gallery item",
        "schema": {
            "url": {"type": "text"},
            "alt": {"type": "text"},
        },
    },
]


def _uid() -> str:
    """Return a fresh Storyblok ``_uid``."""
    return str(uuid.uuid4())


def to_storyblok_site_content(site_content: dict[str, Any]) -> dict[str, Any]:
    """Wrap a flat ``SiteContent`` into the native Storyblok ``site_content`` blok.

    Scalars stay as-is; image URLs stay text; each array becomes a list of nested
    bloks (``site_content_service`` / ``_review`` / ``_faq`` / ``_hours`` /
    ``_gallery_item``), each with its own ``_uid`` + ``component``. The palette is
    expressed as a ``theme_palette`` blok so the Visual Editor edits it like the
    rich templates. Every field is editable in the Storyblok Visual Editor.

    Args:
        site_content: The flat ``SiteContent`` dict from ``build_site_content``.

    Returns:
        A ``site_content`` blok ready to drop into the page ``body``.
    """
    palette_raw = site_content.get("palette") or {}
    palette: dict[str, str] = palette_raw if isinstance(palette_raw, dict) else {}

    gallery = site_content.get("gallery") or []
    services = site_content.get("services") or []
    reviews = site_content.get("reviews") or []
    faq = site_content.get("faq") or []
    opening_hours = site_content.get("openingHours") or []

    return {
        "_uid": _uid(),
        "component": "site_content",
        "businessName": site_content.get("businessName", ""),
        "phone": site_content.get("phone", ""),
        "email": site_content.get("email", ""),
        "city": site_content.get("city", ""),
        "area": site_content.get("area", ""),
        "subtitle": site_content.get("subtitle", ""),
        "about": site_content.get("about", ""),
        "heroImage": site_content.get("heroImage", ""),
        "aboutImage": site_content.get("aboutImage", ""),
        "palette": {
            "_uid": _uid(),
            "component": "theme_palette",
            "primary": str(palette.get("primary", "")),
            "secondary": str(palette.get("secondary", "")),
            "accent": str(palette.get("accent", "")),
        },
        "gallery": [
            {
                "_uid": _uid(),
                "component": "site_content_gallery_item",
                "url": str((item or {}).get("url", "")),
                "alt": str((item or {}).get("alt", "")),
            }
            for item in gallery
            if isinstance(item, dict)
        ],
        "services": [
            {
                "_uid": _uid(),
                "component": "site_content_service",
                "title": str((item or {}).get("title", "")),
                "description": str((item or {}).get("description", "")),
            }
            for item in services
            if isinstance(item, dict)
        ],
        "reviews": [
            {
                "_uid": _uid(),
                "component": "site_content_review",
                "author": str((item or {}).get("author", "")),
                "rating": (item or {}).get("rating", ""),
                "text": str((item or {}).get("text", "")),
            }
            for item in reviews
            if isinstance(item, dict)
        ],
        "faq": [
            {
                "_uid": _uid(),
                "component": "site_content_faq",
                "question": str((item or {}).get("question", "")),
                "answer": str((item or {}).get("answer", "")),
            }
            for item in faq
            if isinstance(item, dict)
        ],
        "openingHours": [
            {
                "_uid": _uid(),
                "component": "site_content_hours",
                "day": str((item or {}).get("day", "")),
                "hours": str((item or {}).get("hours", "")),
            }
            for item in opening_hours
            if isinstance(item, dict)
        ],
    }
