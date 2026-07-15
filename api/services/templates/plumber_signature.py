"""
'plumber-signature' demo template — fully self-contained registration.

Kept out of the shared ``storyblok_service`` / ``demo_site_service`` modules so this
template can evolve (and coexist with other templates) without overwriting them.
The shared services only reference the stable names below:

- ``TEMPLATE_META``        → catalogue entry (demo_site_service.AVAILABLE_TEMPLATES)
- ``build_content(...)``   → content_json builder (storyblok_service.build_content_json)
- ``BODY_COMPONENTS``      → top-level bloks added to the Storyblok page whitelist
- ``COMPONENT_SCHEMAS``    → Storyblok blok schemas registered for this template

Rendering component (Nuxt): demo-host/app/components/templates/plumber-signature/.
"""
from __future__ import annotations

from typing import Any, Optional

TEMPLATE_ID: str = "plumber-signature"

TEMPLATE_META: dict[str, object] = {
    "id": TEMPLATE_ID,
    "name": "Plombier Signature",
    "description": (
        "Vitrine photographique riche et orientée conversion : bandeau urgence 24h, "
        "galerie de chantiers, comparateur avant/après interactif, étapes d'intervention, "
        "histoire de l'artisan, avis et FAQ. Palette pétrole/corail, photos réelles."
    ),
    "preview_image_url": None,
    "category": "artisan",
    "default_theme": {
        "primary": "#0F5257",
        "secondary": "#14181C",
        "accent": "#E8552D",
    },
}

# Top-level bloks this template adds to the Storyblok page body whitelist
# (on top of the shared hero/trust/services/why_us/contact base).
BODY_COMPONENTS: list[str] = [
    "steps",
    "gallery",
    "before_after",
    "story",
    "testimonials",
    "faq",
    "urgency",
]

# Storyblok blok schemas specific to this template (registered in addition to the base).
COMPONENT_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "steps",
        "display_name": "Steps",
        "schema": {
            "heading": {"type": "text"},
            "subheading": {"type": "textarea"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["step_item"],
            },
        },
    },
    {
        "name": "step_item",
        "display_name": "Step item",
        "schema": {
            "title": {"type": "text"},
            "description": {"type": "textarea"},
            "icon": {"type": "text"},
        },
    },
    {
        "name": "gallery",
        "display_name": "Gallery",
        "schema": {
            "heading": {"type": "text"},
            "subheading": {"type": "textarea"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["gallery_item"],
            },
        },
    },
    {
        "name": "gallery_item",
        "display_name": "Gallery item",
        "schema": {
            "image": {"type": "text"},
            "caption": {"type": "text"},
            "location": {"type": "text"},
        },
    },
    {
        "name": "before_after",
        "display_name": "Before / after",
        "schema": {
            "heading": {"type": "text"},
            "subheading": {"type": "textarea"},
            "before_image": {"type": "text"},
            "after_image": {"type": "text"},
            "before_label": {"type": "text"},
            "after_label": {"type": "text"},
            "caption": {"type": "text"},
        },
    },
    {
        "name": "story",
        "display_name": "Story",
        "schema": {
            "kicker": {"type": "text"},
            "heading": {"type": "text"},
            "image": {"type": "text"},
            "signature_name": {"type": "text"},
            "signature_role": {"type": "text"},
            "values": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["value_item"],
            },
            "stats": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["story_stat"],
            },
        },
    },
    {
        "name": "value_item",
        "display_name": "Value item",
        "schema": {
            "label": {"type": "text"},
            "description": {"type": "textarea"},
            "icon": {"type": "text"},
        },
    },
    {
        "name": "story_stat",
        "display_name": "Story stat",
        "schema": {
            "value": {"type": "text"},
            "label": {"type": "text"},
        },
    },
    {
        "name": "testimonials",
        "display_name": "Testimonials",
        "schema": {
            "heading": {"type": "text"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["testimonial_item"],
            },
        },
    },
    {
        "name": "testimonial_item",
        "display_name": "Testimonial item",
        "schema": {
            "quote": {"type": "textarea"},
            "author": {"type": "text"},
            "location": {"type": "text"},
            "rating": {"type": "number"},
        },
    },
    {
        "name": "faq",
        "display_name": "FAQ",
        "schema": {
            "heading": {"type": "text"},
            "items": {
                "type": "bloks",
                "restrict_components": True,
                "component_whitelist": ["faq_item"],
            },
        },
    },
    {
        "name": "faq_item",
        "display_name": "FAQ item",
        "schema": {
            "question": {"type": "text"},
            "answer": {"type": "textarea"},
        },
    },
    {
        "name": "urgency",
        "display_name": "Urgency",
        "schema": {
            "heading": {"type": "text"},
            "subheading": {"type": "textarea"},
            "phone": {"type": "text"},
        },
    },
]


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
    """Build the rich content payload for the photographic 'plumber-signature' template."""
    u: str = "https://images.unsplash.com/photo-"
    hero_image: str = f"{u}1620626011761-996317b8d101"
    story_image: str = f"{u}1558618666-fcd25c85cd64"
    ba_before: str = f"{u}1604709177225-055f99402ea3"
    ba_after: str = f"{u}1584622650111-993a426fbf0a"
    gallery: list[dict[str, str]] = [
        {"image": f"{u}1584622650111-993a426fbf0a", "caption": "Rénovation complète de salle de bain", "location": area},
        {"image": f"{u}1604709177225-055f99402ea3", "caption": "Création d'une salle d'eau", "location": area},
        {"image": f"{u}1600585152220-90363fe7e115", "caption": "Remplacement d'évier et mitigeur", "location": area},
        {"image": f"{u}1556909211-36987daf7b4d", "caption": "Robinetterie et plan de travail", "location": area},
        {"image": f"{u}1600566753086-00f18fb6b3ea", "caption": "Réfection de réseau après dégât des eaux", "location": area},
        {"image": f"{u}1635274605638-d44babc08a4f", "caption": "Aménagement et sanitaires", "location": area},
    ]
    services: list[dict[str, str]] = [
        {"label": "Dépannage d'urgence", "description": "Fuite, canalisation bouchée ou chauffe-eau en panne — on intervient vite, 7 j/7.", "icon": "emergency"},
        {"label": "Recherche de fuite", "description": "Diagnostic précis sans casse inutile, grâce à des outils de détection professionnels.", "icon": "leak"},
        {"label": "Rénovation salle de bain", "description": "Douche, robinetterie, WC et sanitaires posés proprement, du devis à la finition.", "icon": "bath"},
        {"label": "Chauffe-eau & chaudière", "description": "Entretien, remplacement et mise aux normes de vos équipements d'eau chaude.", "icon": "heater"},
        {"label": "Débouchage canalisations", "description": "Évacuations et colonnes dégagées durablement, sans abîmer vos installations.", "icon": "drain"},
        {"label": "Installation sanitaire", "description": "Pose de robinetterie, WC, lavabos et raccordements neufs aux normes.", "icon": "install"},
    ]
    steps: list[dict[str, str]] = [
        {"title": "Votre appel", "description": "On échange sur votre problème et on évalue l'urgence.", "icon": "phone"},
        {"title": "Le diagnostic", "description": "On identifie précisément la panne, sans casse inutile.", "icon": "search"},
        {"title": "Le devis", "description": "Un prix clair et détaillé, validé avant toute intervention.", "icon": "doc"},
        {"title": "L'intervention", "description": "On répare proprement et on vérifie tout avant de partir.", "icon": "install"},
    ]
    trust_stats: list[dict[str, str]] = [
        {"value": "4,9/5", "label": "Avis Google"},
        {"value": "15 ans", "label": "D'expérience"},
        {"value": "< 2h", "label": "En urgence"},
        {"value": "24/7", "label": "Disponible"},
    ]
    values: list[dict[str, str]] = [
        {"label": "Travail garanti", "description": "Chaque intervention est couverte et suivie.", "icon": "shield"},
        {"label": "Prix transparents", "description": "Un devis clair, validé avant de commencer.", "icon": "euro"},
        {"label": "Ponctualité", "description": "On respecte le créneau convenu avec vous.", "icon": "clock"},
        {"label": "Conseil honnête", "description": "On répare ce qui doit l'être, rien de plus.", "icon": "hand"},
    ]
    testimonials: list[dict[str, Any]] = [
        {"quote": "Fuite réparée le soir même, proprement et efficacement. Je recommande sans hésiter.", "author": "Sophie M.", "location": area, "rating": 5},
        {"quote": "Devis clair, intervention rapide et tarif respecté. Un vrai professionnel.", "author": "Karim B.", "location": area, "rating": 5},
        {"quote": "Rénovation de notre salle de bain impeccable, dans les délais annoncés.", "author": "Laurent D.", "location": area, "rating": 5},
    ]
    faqs: list[dict[str, str]] = [
        {"question": "Intervenez-vous en urgence le week-end ?", "answer": "Oui. Nous assurons un dépannage 24 h/24 et 7 j/7 pour les urgences : fuite, dégât des eaux, absence d'eau chaude. Un seul numéro, à toute heure."},
        {"question": "Le devis est-il vraiment gratuit ?", "answer": "Toujours. Nous évaluons votre besoin et vous communiquons un prix clair et détaillé avant toute intervention, sans engagement."},
        {"question": "Dans quelles zones intervenez-vous ?", "answer": f"Nous intervenons à {area} et dans les communes alentour. Appelez-nous pour vérifier votre secteur."},
        {"question": "Combien de temps pour une intervention ?", "answer": "En urgence, nous visons une intervention en moins de deux heures. Pour les travaux planifiés, nous convenons ensemble d'un créneau qui vous arrange."},
        {"question": "Vos travaux sont-ils garantis ?", "answer": "Oui. Nos interventions et les équipements posés sont garantis, et nous restons votre interlocuteur après le chantier."},
    ]
    paragraphs: list[str] = [
        f"Depuis plus de quinze ans, {business_name} intervient chez les particuliers et les professionnels de {area}. "
        "Chaque chantier est mené de bout en bout par le même artisan — celui qui répond au téléphone est celui qui vient chez vous.",
        "La plomberie est un métier de confiance : on entre chez vous, souvent dans l'urgence. On y répond par un travail "
        "soigné, des explications claires et des tarifs annoncés à l'avance.",
        "Pas de sous-traitance, pas de mauvaise surprise sur la facture : juste le geste juste, garanti.",
    ]

    def nested(items: list[dict[str, Any]], component: str, prefix: str) -> list[dict[str, Any]]:
        return [{"_uid": f"{prefix}-{i}", "component": component, **item} for i, item in enumerate(items)]

    return {
        "component": "page",
        "theme": palette,
        "body": [
            {
                "_uid": "hero-1",
                "component": "hero",
                "title": business_name,
                "subtitle": subtitle,
                "phone": phone or "",
                "cta_label": "Appeler maintenant",
                "badge": "Dépannage & rénovation",
                "city": city or "",
                "image": hero_image,
                "points": ["Devis gratuit sous 24 h", "Intervention en moins de 2 h", "Travail garanti"],
            },
            {
                "_uid": "trust-1",
                "component": "trust",
                "heading": "La confiance de nos clients",
                "items": nested(trust_stats, "trust_item", "t"),
            },
            {
                "_uid": "services-1",
                "component": "services",
                "heading": "Ce que nous prenons en charge",
                "subheading": f"Dépannage, recherche de fuite et rénovation pour particuliers et professionnels à {area}.",
                "items": nested(services, "service_item", "s"),
            },
            {
                "_uid": "steps-1",
                "component": "steps",
                "heading": "Comment ça se passe",
                "subheading": "De votre appel à la fin du chantier, un déroulé simple et sans surprise.",
                "items": nested(steps, "step_item", "st"),
            },
            {
                "_uid": "gallery-1",
                "component": "gallery",
                "heading": "Quelques chantiers récents",
                "subheading": "Un aperçu de nos interventions et rénovations.",
                "items": nested(gallery, "gallery_item", "g"),
            },
            {
                "_uid": "ba-1",
                "component": "before_after",
                "heading": "Le résultat parle de lui-même",
                "subheading": "Glissez le curseur pour comparer l'avant et l'après d'une rénovation.",
                "before_image": ba_before,
                "after_image": ba_after,
                "before_label": "Avant",
                "after_label": "Après",
                "caption": "Rénovation de salle de bain — exemple de transformation.",
            },
            {
                "_uid": "story-1",
                "component": "story",
                "kicker": "L'artisan",
                "heading": "Un savoir-faire transmis, pas sous-traité",
                "paragraphs": paragraphs,
                "values": nested(values, "value_item", "v"),
                "image": story_image,
                "signature_name": business_name,
                "signature_role": "Artisan plombier",
                "stats": nested(
                    [{"value": "500+", "label": "Interventions"}, {"value": "15 ans", "label": "De métier"}],
                    "story_stat",
                    "ss",
                ),
            },
            {
                "_uid": "reviews-1",
                "component": "testimonials",
                "heading": "Ce que disent nos clients",
                "items": nested(testimonials, "testimonial_item", "r"),
            },
            {
                "_uid": "faq-1",
                "component": "faq",
                "heading": "Vous vous demandez peut-être…",
                "items": nested(faqs, "faq_item", "f"),
            },
            {
                "_uid": "urgent-1",
                "component": "urgency",
                "heading": "Une fuite, une panne, une urgence ?",
                "subheading": "On décroche et on intervient vite. 24 h/24, 7 j/7.",
                "phone": phone or "",
            },
            {
                "_uid": "contact-1",
                "component": "contact",
                "heading": "Parlons de votre projet",
                "subheading": "Un devis gratuit, une question, une urgence — écrivez ou appelez, on vous répond vite.",
                "email": email or "",
                "phone": phone or "",
                "city": city or "",
                "hours": "Lun–Sam 8 h–20 h · Urgences 24 h/24",
            },
        ],
    }


# --- Phase 4b: flat SiteContent path (shared with the other migrated templates) ------------
from .site_content import (  # noqa: E402, F401
    PLUMBER_FAQ,
    PLUMBER_SERVICES,
    SITE_CONTENT_SCHEMAS,
    map_prospect_and_enrichment,
    to_storyblok_site_content,
)

_SITE_ABOUT_DEFAULT: str = (
    "Artisan plombier de confiance, je prends en charge vos dépannages, installations et "
    "rénovations avec le même soin. Diagnostic honnête, travail propre et prix juste."
)


# Editorial copy pre-filled into the CMS so the client sees (and edits) his real
# texts instead of blank fields silently falling back to template defaults.
# Values mirror the layer defaults of devleadhunter-template-plumber-signature.
_EDITORIAL_DEFAULTS: dict[str, Any] = {
    "heroBadge": "Artisan plombier",
    "heroPoints": ["Devis gratuit", "Intervention rapide", "Travail garanti"],
    "ctaCallLabel": "Appeler maintenant",
    "ctaQuoteLabel": "",
    "trustItems": [
        {"value": "7j/7", "label": "Urgences 24 h/24"},
        {"value": "Devis 0 €", "label": "Sans engagement"},
        {"value": "Garantie", "label": "Travail assuré"},
        {"value": "Local", "label": "Artisan proche de vous"},
    ],
    "servicesHeading": "Ce que nous prenons en charge",
    "galleryHeading": "Quelques chantiers récents",
    "reviewsHeading": "Ce que disent nos clients",
    "faqHeading": "Vous vous demandez peut-être…",
    "aboutHeading": "Un savoir-faire transmis, pas sous-traité",
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
    site["services"] = scraped or PLUMBER_SERVICES
    site["faq"] = PLUMBER_FAQ
    # Pre-fill editorial copy (client edits his real texts in the CMS).
    site.update(_EDITORIAL_DEFAULTS)
    return site
