"""
Central registry of demo site templates.

Each template lives in its own module (``plumber_signature``, ``plumber_atelier``,
``plumber_simple``…) and exposes the same stable interface:

- ``TEMPLATE_ID``        → unique template identifier
- ``TEMPLATE_META``      → catalogue entry
- ``build_content(...)`` → content_json builder
- ``BODY_COMPONENTS``    → extra Storyblok page bloks (on top of the shared base)
- ``COMPONENT_SCHEMAS``  → extra Storyblok blok schemas

Phase 4b — a template may additionally opt into the FLAT ``SiteContent`` path by
exposing ``build_site_content(...)`` + ``to_storyblok_site_content(...)`` +
``SITE_CONTENT_SCHEMAS`` (currently only ``plumber-cuivre``). Such a template
produces a flat ``SiteContent`` (stored in ``content_json``) and its native
``site_content`` Storyblok blok, instead of the rich per-section bloks.

Adding a new template = create the module + append it to ``TEMPLATE_MODULES``.
"""

from __future__ import annotations

from typing import Any

from services.templates import (
    artisan_edito,
    barber,
    dental,
    electrician_lumen,
    food,
    landscaper_verdure,
    mechanic_pitlane,
    plumber_atelier,
    plumber_cuivre,
    plumber_signature,
)

# Order here defines the order shown in the template picker (default first).
TEMPLATE_MODULES = [
    artisan_edito,
    plumber_signature,
    plumber_atelier,
    plumber_cuivre,
    electrician_lumen,
    mechanic_pitlane,
    dental,
    food,
    barber,
    landscaper_verdure,
]

TEMPLATES_BY_ID: dict[str, Any] = {module.TEMPLATE_ID: module for module in TEMPLATE_MODULES}

AVAILABLE_TEMPLATES: list[dict[str, object]] = [module.TEMPLATE_META for module in TEMPLATE_MODULES]

# The default, multi-trade template (« Édito ») — used when no template is chosen.
DEFAULT_TEMPLATE_ID: str = artisan_edito.TEMPLATE_ID


def get_module(template_id: str) -> Any:
    """Return the template module for an id, falling back to the default template."""
    return TEMPLATES_BY_ID.get(template_id, artisan_edito)


def default_subtitle(template_id: str, area: str) -> str:
    """Trade-aware default subtitle when the prospect has no description.

    Templates may expose ``default_subtitle(area)``; historical plumber wording
    is kept as the fallback so existing templates behave exactly as before.
    """
    builder = getattr(get_module(template_id), "default_subtitle", None)
    if callable(builder):
        return str(builder(area))
    return f"Plombier professionnel — dépannage rapide à {area}"


def default_theme(template_id: str) -> dict[str, str]:
    """Return a template's signature palette (its ``TEMPLATE_META['default_theme']``).

    Used when a demo is generated without an explicit theme, so the site renders in the
    template's own DA colours (e.g. Lumen's yellow) rather than a generic fallback.
    """
    meta = getattr(get_module(template_id), "TEMPLATE_META", {}) or {}
    theme = meta.get("default_theme")
    if isinstance(theme, dict) and theme:
        return {
            "primary": str(theme.get("primary", "#0284c7")),
            "secondary": str(theme.get("secondary", "#0f172a")),
            "accent": str(theme.get("accent", "#f59e0b")),
        }
    return {"primary": "#0284c7", "secondary": "#0f172a", "accent": "#f59e0b"}


def brand_color_key(template_id: str) -> str:
    """Return the palette key a template uses for its action colour, overridden by the prospect's brand colour.

    Most templates drive their buttons/highlights from ``primary`` (mechanic's red, food's green); barber is
    the exception — its ``primary`` is the dark charcoal and the action colour is the gold ``accent``. A
    template declares it via ``TEMPLATE_META['brand_color_key']``; the default is ``primary``.
    """
    meta = getattr(get_module(template_id), "TEMPLATE_META", {}) or {}
    key = meta.get("brand_color_key")
    return key if key in ("primary", "secondary", "accent") else "primary"


def service_cards_meta(template_id: str) -> dict[str, Any] | None:
    """The template's editable-cards section declaration (``TEMPLATE_META['service_cards']``), or None.

    Food declares its « Nos spécialités » menu (4 to 6 dish cards with photos); templates with a
    fixed prestations grid declare nothing, so the dashboard hides the cards editor for them.
    """
    meta = getattr(get_module(template_id), "TEMPLATE_META", {}) or {}
    raw = meta.get("service_cards")
    return raw if isinstance(raw, dict) else None


def color_roles(template_id: str) -> dict[str, str]:
    """Return the template's canonical colour roles → palette key (``{"action": "primary", …}``).

    Only the roles a layer visibly consumes are listed (from the CSS audit), so the editor hides dead
    fields. ``action`` always equals ``brand_color_key``. Empty when a template declares none.
    """
    meta = getattr(get_module(template_id), "TEMPLATE_META", {}) or {}
    roles = meta.get("color_roles")
    if not isinstance(roles, dict):
        return {}
    return {str(role): str(key) for role, key in roles.items() if key in ("primary", "secondary", "accent")}


def build_content(
    *,
    template_id: str,
    business_name: str,
    phone: str | None,
    email: str | None,
    city: str | None,
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


def uses_site_content(template_id: str) -> bool:
    """Return True when a template opts into the flat ``SiteContent`` path (Phase 4b).

    A template opts in simply by exposing ``build_site_content`` — currently only
    ``plumber-cuivre``. Every other template keeps the rich ``build_content`` path.
    """
    return callable(getattr(get_module(template_id), "build_site_content", None))


def build_site_content(
    *,
    template_id: str,
    business_name: str,
    phone: str | None,
    email: str | None,
    city: str | None,
    area: str,
    subtitle: str,
    palette: dict[str, str],
    enrichment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatch flat ``SiteContent`` building to a template that opts in.

    The flat builder consumes enrichment itself (no separate enrichment merge).
    """
    return get_module(template_id).build_site_content(
        business_name=business_name,
        phone=phone,
        email=email,
        city=city,
        area=area,
        subtitle=subtitle,
        palette=palette,
        enrichment=enrichment,
    )


def to_storyblok_site_content(template_id: str, site_content: dict[str, Any]) -> list[dict[str, Any]]:
    """Project a flat ``SiteContent`` into the template's Storyblok page ``body`` (list of section bloks).

    A template may declare ``USED_SECTIONS`` (the sections it actually renders) so its client editor
    shows no dead sections, and ``SECTION_FIELDS`` (per-section field-key overrides) to expose or hide
    specific fields; a template without them gets every section with its default fields.
    """
    module = get_module(template_id)
    used_sections: list[str] | None = getattr(module, "USED_SECTIONS", None)
    extra_section_images: dict[str, list[dict[str, str]]] | None = getattr(module, "EXTRA_SECTION_IMAGES", None)
    section_field_overrides: dict[str, list[str]] | None = getattr(module, "SECTION_FIELDS", None)
    return module.to_storyblok_site_content(site_content, used_sections, extra_section_images, section_field_overrides)


def content_schemas(template_id: str) -> list[dict[str, Any]]:
    """Return the Storyblok component schemas for a template — its per-template image fields included.

    A template declares its one-off image slots in ``EXTRA_SECTION_IMAGES`` ({section: [{field, label}]});
    they become editable asset fields grouped in that section.
    """
    from services.templates.site_content import build_content_schemas

    module = get_module(template_id)
    extra_section_images: dict[str, list[dict[str, str]]] | None = getattr(module, "EXTRA_SECTION_IMAGES", None)
    section_field_overrides: dict[str, list[str]] | None = getattr(module, "SECTION_FIELDS", None)
    field_schema_overrides: dict[str, dict[str, Any]] | None = getattr(module, "FIELD_SCHEMA_OVERRIDES", None)
    return build_content_schemas(extra_section_images, section_field_overrides, field_schema_overrides)


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
    """Aggregate extra Storyblok blok schemas contributed by every template (deduplicated by name).

    Includes both the rich ``COMPONENT_SCHEMAS`` and, for templates that opt into
    the flat path, the ``SITE_CONTENT_SCHEMAS`` (native ``site_content`` bloks) so
    every editable field registers in Storyblok.
    """
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for module in TEMPLATE_MODULES:
        schemas: list[dict[str, Any]] = list(getattr(module, "COMPONENT_SCHEMAS", []))
        schemas.extend(getattr(module, "SITE_CONTENT_SCHEMAS", []))
        for schema in schemas:
            name = str(schema.get("name", ""))
            if name and name not in seen:
                seen.add(name)
                result.append(schema)
    return result
