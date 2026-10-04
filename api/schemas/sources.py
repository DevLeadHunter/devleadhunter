"""
Prospect source metadata shared by the API and the dashboard.

Keep in sync with:
- ``api/enums/source.py``              (Python ``Source`` enum)
- ``web/app/types/index.ts``           (TypeScript ``ProspectSource`` type)
- ``web/app/constants/prospectSources.ts``  (UI display options)
"""

from __future__ import annotations

from enums.source import Source

# Human-readable labels (French) for UI selects. The search writes ``search``; the other
# sources are kept for the prospects created before it replaced the per-source scrapers.
SOURCE_LABELS: dict[Source, str] = {
    Source.SEARCH: "Recherche",
    Source.MANUAL: "Ajout manuel",
    Source.GOOGLE: "Google",
    Source.FACEBOOK: "Facebook",
    Source.PAGESJAUNES: "Pages Jaunes",
    Source.YELP: "Yelp",
    Source.OSM: "OpenStreetMap",
    Source.AUTO: "Auto",
    Source.BRIGHTDATA: "BrightData",
    Source.ALL: "Toutes les sources",
}

# Sources a prospect list can be filtered on, the current ones first.
FILTER_SOURCES: tuple[Source, ...] = (
    Source.SEARCH,
    Source.MANUAL,
    Source.GOOGLE,
    Source.FACEBOOK,
    Source.PAGESJAUNES,
    Source.OSM,
    Source.BRIGHTDATA,
)


def source_label(source: Source) -> str:
    """Return the display label for a source enum value."""
    return SOURCE_LABELS.get(source, source.value)


def list_source_options(*, include_all: bool = True) -> list[dict[str, str]]:
    """
    Build source options for API consumers (web selects).

    Args:
        include_all: When True, prepend the ``all`` aggregate option.

    Returns:
        List of ``{"value": str, "label": str}`` dicts.
    """
    options: list[dict[str, str]] = []
    if include_all:
        options.append({"value": Source.ALL.value, "label": source_label(Source.ALL)})

    for source in FILTER_SOURCES:
        options.append({"value": source.value, "label": source_label(source)})
    return options
