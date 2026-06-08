"""
Shared content builder for the "base" plumber templates.

Templates that use only the base bloks (hero / trust / services / why_us / contact)
build their content_json through :func:`build_base_page`. Each template module
provides its own service list, trust stats and selling points, keeping the page
structure consistent while leaving the editorial content per template.
"""
from __future__ import annotations

from typing import Any, Optional


def build_base_page(
    *,
    business_name: str,
    phone: Optional[str],
    email: Optional[str],
    city: Optional[str],
    area: str,
    subtitle: str,
    palette: dict[str, str],
    services: list[dict[str, str]],
    trust_stats: list[dict[str, str]],
    why_us: list[str],
) -> dict[str, Any]:
    """Build the shared hero/trust/services/why_us/contact page payload."""
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
                "badge": "Intervention 24h/24",
                "city": city or "",
            },
            {
                "_uid": "trust-1",
                "component": "trust",
                "heading": "La confiance de nos clients",
                "items": [
                    {"_uid": f"t-{i}", "component": "trust_item", **item}
                    for i, item in enumerate(trust_stats)
                ],
            },
            {
                "_uid": "services-1",
                "component": "services",
                "heading": "Nos services",
                "subheading": f"Des solutions complètes pour particuliers et professionnels à {area}.",
                "items": [
                    {"_uid": f"s-{i}", "component": "service_item", **item}
                    for i, item in enumerate(services)
                ],
            },
            {
                "_uid": "why-1",
                "component": "why_us",
                "heading": "Pourquoi nous choisir ?",
                "items": [
                    {"_uid": f"w-{i}", "component": "why_item", "label": label}
                    for i, label in enumerate(why_us)
                ],
            },
            {
                "_uid": "contact-1",
                "component": "contact",
                "heading": "Contactez-nous",
                "subheading": "Un devis gratuit en quelques minutes — réponse rapide garantie.",
                "email": email or "",
                "phone": phone or "",
                "city": city or "",
            },
        ],
    }
