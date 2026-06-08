"""
'plumber-atelier' demo template ("Plombier Atelier") — self-contained registration.

Exposes the stable names consumed by the shared services (see ``registry``):

- ``TEMPLATE_META``      → catalogue entry (demo_site_service.AVAILABLE_TEMPLATES)
- ``build_content(...)`` → content_json builder (storyblok_service.build_content_json)
- ``BODY_COMPONENTS``    → extra top-level bloks (none beyond the shared base)
- ``COMPONENT_SCHEMAS``  → extra Storyblok blok schemas (none beyond the shared base)

Rendering component (Nuxt): demo-host/app/components/templates/plumber-atelier/.
"""
from __future__ import annotations

from typing import Any, Optional

from services.templates._base import build_base_page

TEMPLATE_ID: str = "plumber-atelier"

TEMPLATE_META: dict[str, object] = {
    "id": TEMPLATE_ID,
    "name": "Plombier Atelier",
    "description": (
        "Direction éditoriale artisan (papier chaud, laiton, plan technique) : "
        "hero asymétrique, services en index numéroté, garanties et contact. "
        "Look sur-mesure, à l'opposé d'une landing générique."
    ),
    "preview_image_url": None,
    "category": "artisan",
    "default_theme": {
        "primary": "#B8732E",
        "secondary": "#1C1B19",
        "accent": "#2E5B6B",
    },
}

# This template only uses the shared base bloks.
BODY_COMPONENTS: list[str] = []
COMPONENT_SCHEMAS: list[dict[str, Any]] = []


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
    """Build the content payload for the 'plumber-atelier' template."""
    services: list[dict[str, str]] = [
        {
            "label": "Dépannage d'urgence",
            "description": "Fuite, canalisation bouchée ou chauffe-eau en panne — intervention rapide, 7j/7.",
            "icon": "emergency",
        },
        {
            "label": "Recherche de fuite",
            "description": "Diagnostic précis sans casse inutile, grâce à des outils de détection professionnels.",
            "icon": "leak",
        },
        {
            "label": "Rénovation salle de bain",
            "description": "Douche, robinetterie, WC et sanitaires neufs posés proprement, du devis à la finition.",
            "icon": "bath",
        },
        {
            "label": "Chauffe-eau & chaudière",
            "description": "Entretien, remplacement et mise aux normes de vos équipements de production d'eau chaude.",
            "icon": "heater",
        },
        {
            "label": "Débouchage & canalisations",
            "description": "Évacuations, colonnes et réseaux dégagés durablement, sans abîmer vos installations.",
            "icon": "drain",
        },
    ]
    trust_stats: list[dict[str, str]] = [
        {"value": "15 ans", "label": "D'expérience"},
        {"value": "< 2h", "label": "En urgence"},
        {"value": "4,9/5", "label": "Avis Google"},
        {"value": "Gratuit", "label": "Devis"},
    ]
    why_us: list[str] = [
        "Devis gratuit et transparent avant chaque intervention",
        "Un artisan qualifié de A à Z — jamais de sous-traitance",
        "Intervention en moins de 2 h en cas d'urgence",
        "Travail soigné, garanti et facturé au juste prix",
    ]
    return build_base_page(
        business_name=business_name,
        phone=phone,
        email=email,
        city=city,
        area=area,
        subtitle=subtitle,
        palette=palette,
        services=services,
        trust_stats=trust_stats,
        why_us=why_us,
    )
