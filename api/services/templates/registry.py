"""
Central registry of demo site templates.

Each template lives in its own module (``plumber_signature``, ``plumber_atelier``,
``plumber_simple``…) and exposes the same stable interface:

- ``TEMPLATE_ID``        → unique template identifier
- ``TEMPLATE_META``      → catalogue entry
- ``build_content(...)`` → content_json builder
- ``BODY_COMPONENTS``    → extra Storyblok page bloks (on top of the shared base)
- ``COMPONENT_SCHEMAS``  → extra Storyblok blok schemas

Adding a new template = create the module + append it to ``TEMPLATE_MODULES``.
"""
from __future__ import annotations

from typing import Any, Optional

from services.templates import electrician_lumen, plumber_atelier, plumber_cuivre, plumber_signature, plumber_simple

# Order here defines the order shown in the template picker.
TEMPLATE_MODULES = [plumber_signature, plumber_atelier, plumber_simple, plumber_cuivre, electrician_lumen]

TEMPLATES_BY_ID: dict[str, Any] = {module.TEMPLATE_ID: module for module in TEMPLATE_MODULES}

AVAILABLE_TEMPLATES: list[dict[str, object]] = [module.TEMPLATE_META for module in TEMPLATE_MODULES]

DEFAULT_TEMPLATE_ID: str = plumber_simple.TEMPLATE_ID


def get_module(template_id: str) -> Any:
    """Return the template module for an id, falling back to the default template."""
    return TEMPLATES_BY_ID.get(template_id, plumber_simple)


def default_subtitle(template_id: str, area: str) -> str:
    """Trade-aware default subtitle when the prospect has no description.

    Templates may expose ``default_subtitle(area)``; historical plumber wording
    is kept as the fallback so existing templates behave exactly as before.
    """
    builder = getattr(get_module(template_id), "default_subtitle", None)
    if callable(builder):
        return str(builder(area))
    return f"Plombier professionnel — dépannage rapide à {area}"


def build_content(
    *,
    template_id: str,
    business_name: str,
    phone: Optional[str],
    email: Optional[str],
    city: Optional[str],
    area: str,
    subtitle: str,
    palette: dict[str, str],
) -> dict[str, Any]:
    """Dispatch content_json building to the right template module."""
    return get_module(template_id).build_content(
        business_name=business_name,
        phone=phone,
        email=email,
        city=city,
        area=area,
        subtitle=subtitle,
        palette=palette,
    )


def body_components() -> list[str]:
    """Aggregate extra page bloks contributed by every template (deduplicated)."""
    seen: set[str] = set()
    result: list[str] = []
    for module in TEMPLATE_MODULES:
        for component in module.BODY_COMPONENTS:
            if component not in seen:
                seen.add(component)
                result.append(component)
    return result


def component_schemas() -> list[dict[str, Any]]:
    """Aggregate extra Storyblok blok schemas contributed by every template (deduplicated by name)."""
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for module in TEMPLATE_MODULES:
        for schema in module.COMPONENT_SCHEMAS:
            name = str(schema.get("name", ""))
            if name and name not in seen:
                seen.add(name)
                result.append(schema)
    return result
