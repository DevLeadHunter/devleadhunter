"""
'plumber-simple' demo template ("Plombier Pro") — self-contained registration.

Exposes the stable names consumed by the shared services (see ``registry``):

- ``TEMPLATE_META``      → catalogue entry (demo_site_service.AVAILABLE_TEMPLATES)
- ``build_content(...)`` → content_json builder (storyblok_service.build_content_json)
- ``BODY_COMPONENTS``    → extra top-level bloks (none beyond the shared base)
- ``COMPONENT_SCHEMAS``  → extra Storyblok blok schemas (none beyond the shared base)

Rendering component (Nuxt): demo-host/app/components/templates/plumber-simple/.
"""
from __future__ import annotations

from typing import Any, Optional

from services.templates._base import build_base_page

TEMPLATE_ID: str = "plumber-simple"

TEMPLATE_META: dict[str, object] = {
    "id": TEMPLATE_ID,
    "name": "Plombier Pro",
    "description": "Site vitrine premium pour artisan plombier : hero animé, services, garanties et contact.",
    "preview_image_url": None,
    "category": "artisan",
    "default_theme": {
        "primary": "#0284c7",
        "secondary": "#0f172a",
        "accent": "#f59e0b",
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
    """Build the content payload for the 'plumber-simple' template."""
    services: list[dict[str, str]] = [
        {
            "label": "Dépannage urgent",
            "description": "Fuite, canalisation bouchée ou chauffe-eau en panne — intervention rapide.",
            "icon": "emergency",
        },
        {
            "label": "Installation sanitaire",
            "description": "Salle de bain, robinetterie, WC et équipements neufs posés proprement.",
            "icon": "install",
        },
        {
            "label": "Chauffe-eau & chaudière",
            "description": "Entretien, remplacement et mise aux normes de vos équipements.",
            "icon": "heater",
        },
        {
            "label": "Recherche de fuite",
            "description": "Diagnostic précis sans casse inutile grâce à des outils professionnels.",
            "icon": "leak",
        },
    ]
    trust_stats: list[dict[str, str]] = [
        {"value": "500+", "label": "Clients satisfaits"},
        {"value": "15 ans", "label": "D'expérience"},
        {"value": "24/7", "label": "Dépannage"},
        {"value": "4,9/5", "label": "Avis Google"},
    ]
    why_us: list[str] = [
        "Devis gratuit et transparent avant intervention",
        "Artisan qualifié — travail soigné et garanti",
        "Intervention en moins de 2 h en urgence",
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
    return site
