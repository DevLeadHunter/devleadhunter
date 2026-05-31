"""
Prospect source metadata shared by API and scrapers.
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
    Source.ALL: "Toutes les sources",
}

# Sources that have a registered scraper (excludes ALL filter).
SCRAPER_SOURCES: tuple[Source, ...] = (
    Source.GOOGLE,
    Source.PAGESJAUNES,
    Source.YELP,
    Source.OSM,
    Source.MOCK,
)

# Sources exposed in search/filter UI (excludes mock in production UI — kept for dev).
SEARCH_FILTER_SOURCES: tuple[Source, ...] = (
    Source.GOOGLE,
    Source.PAGESJAUNES,
    Source.YELP,
    Source.OSM,
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
