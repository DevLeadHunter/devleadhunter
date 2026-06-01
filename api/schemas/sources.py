"""
Prospect source metadata shared by API and scrapers.

Keep in sync with:
- ``api/enums/source.py``              (Python ``Source`` enum)
- ``web/app/types/index.ts``           (TypeScript ``ProspectSource`` type)
- ``web/app/constants/prospectSources.ts``  (UI display options)
"""
from __future__ import annotations

from enums.source import Source

# Human-readable labels (French) for UI selects.
SOURCE_LABELS: dict[Source, str] = {
    Source.GOOGLE: "Google",
    Source.PAGESJAUNES: "Pages Jaunes",
    Source.YELP: "Yelp",
    Source.OSM: "OpenStreetMap",
    Source.MOCK: "Mock (Test)",
    Source.AUTO: "Auto (recommandé)",
    Source.BRIGHTDATA: "BrightData",
    Source.ALL: "Toutes les sources",
}

# Sources that have a registered scraper (excludes the ALL aggregate sentinel).
SCRAPER_SOURCES: tuple[Source, ...] = (
    Source.GOOGLE,
    Source.PAGESJAUNES,
    Source.YELP,
    Source.OSM,
    Source.MOCK,
    Source.AUTO,
    Source.BRIGHTDATA,
)

# Sources exposed in the search/filter UI (keep mock for dev convenience).
SEARCH_FILTER_SOURCES: tuple[Source, ...] = (
    Source.AUTO,
    Source.GOOGLE,
    Source.PAGESJAUNES,
    Source.OSM,
    Source.BRIGHTDATA,
    Source.YELP,
    Source.MOCK,
)


def source_label(source: Source) -> str:
    """Return the display label for a source enum value."""
    return SOURCE_LABELS.get(source, source.value)


def list_source_options(*, include_all: bool = True, include_mock: bool = True) -> list[dict[str, str]]:
    """
    Build source options for API consumers (web selects).

    Args:
        include_all: When True, prepend the ``all`` aggregate option.
        include_mock: When True, include the mock/test source.

    Returns:
        List of ``{"value": str, "label": str}`` dicts.
    """
    options: list[dict[str, str]] = []
    if include_all:
        options.append({"value": Source.ALL.value, "label": source_label(Source.ALL)})

    for src in SEARCH_FILTER_SOURCES:
        if src == Source.MOCK and not include_mock:
            continue
        options.append({"value": src.value, "label": source_label(src)})
    return options
