"""
Pure helpers around photo labels (what a prospect photo shows) — no I/O, no model imports.

Shared by site generation (templates), the demo-site service and the vision labelling service, so
the template modules can rank photos without pulling the LLM client in.

A label is ``{"kind": str, "description": str, "dishes": list[str], "appeal": int}`` keyed by
photo URL in ``ProspectEnrichment.photo_labels``.
"""

from __future__ import annotations

from typing import Any

# Photo kinds the vision model chooses from. ``dish`` / ``drink`` are the only card-worthy ones.
PHOTO_KIND_DISH = "dish"
PHOTO_KIND_DRINK = "drink"
PHOTO_KIND_TRUCK = "truck"
PHOTO_KIND_MENU_BOARD = "menu_board"
PHOTO_KIND_INTERIOR = "interior"
PHOTO_KIND_PEOPLE = "people"
PHOTO_KIND_EVENT = "event"
PHOTO_KIND_LOGO_OR_FLYER = "logo_or_flyer"
PHOTO_KIND_OTHER = "other"
PHOTO_KINDS: frozenset[str] = frozenset(
    {
        PHOTO_KIND_DISH,
        PHOTO_KIND_DRINK,
        PHOTO_KIND_TRUCK,
        PHOTO_KIND_MENU_BOARD,
        PHOTO_KIND_INTERIOR,
        PHOTO_KIND_PEOPLE,
        PHOTO_KIND_EVENT,
        PHOTO_KIND_LOGO_OR_FLYER,
        PHOTO_KIND_OTHER,
    }
)
CARD_WORTHY_KINDS: frozenset[str] = frozenset({PHOTO_KIND_DISH, PHOTO_KIND_DRINK})

# Bump when the labelling prompt changes materially: stored labels with an older version are
# re-labelled at the next use instead of living forever with the old reading.
PHOTO_LABEL_VERSION = 2

# Wordings the model uses instead of the canonical kinds (French, synonyms): mapped, never dropped.
# Ordered from the most specific to the most generic wording, because a wording that is not an
# exact key is matched by substring in this order (« food truck exterior » must read as truck).
_KIND_SYNONYMS: dict[str, str] = {
    "camion": PHOTO_KIND_TRUCK,
    "truck": PHOTO_KIND_TRUCK,
    "van": PHOTO_KIND_TRUCK,
    "exterior": PHOTO_KIND_TRUCK,
    "storefront": PHOTO_KIND_TRUCK,
    "facade": PHOTO_KIND_TRUCK,
    "façade": PHOTO_KIND_TRUCK,
    "menuboard": PHOTO_KIND_MENU_BOARD,
    "menu board": PHOTO_KIND_MENU_BOARD,
    "menu": PHOTO_KIND_MENU_BOARD,
    "board": PHOTO_KIND_MENU_BOARD,
    "carte": PHOTO_KIND_MENU_BOARD,
    "ardoise": PHOTO_KIND_MENU_BOARD,
    "logo": PHOTO_KIND_LOGO_OR_FLYER,
    "flyer": PHOTO_KIND_LOGO_OR_FLYER,
    "affiche": PHOTO_KIND_LOGO_OR_FLYER,
    "poster": PHOTO_KIND_LOGO_OR_FLYER,
    "text": PHOTO_KIND_LOGO_OR_FLYER,
    "intérieur": PHOTO_KIND_INTERIOR,
    "interieur": PHOTO_KIND_INTERIOR,
    "kitchen": PHOTO_KIND_INTERIOR,
    "cuisine": PHOTO_KIND_INTERIOR,
    "personnes": PHOTO_KIND_PEOPLE,
    "team": PHOTO_KIND_PEOPLE,
    "équipe": PHOTO_KIND_PEOPLE,
    "staff": PHOTO_KIND_PEOPLE,
    "événement": PHOTO_KIND_EVENT,
    "evenement": PHOTO_KIND_EVENT,
    "boisson": PHOTO_KIND_DRINK,
    "beverage": PHOTO_KIND_DRINK,
    "plat": PHOTO_KIND_DISH,
    "meal": PHOTO_KIND_DISH,
    "dessert": PHOTO_KIND_DISH,
    "nourriture": PHOTO_KIND_DISH,
    "food": PHOTO_KIND_DISH,
    "autre": PHOTO_KIND_OTHER,
}

_MAX_DESCRIPTION_CHARS = 140
_MAX_DISHES_PER_PHOTO = 24
_MAX_DISH_CHARS = 60


def canonical_kind(raw_kind: Any) -> str | None:
    """The canonical kind for a model wording (``dish``, ``plat``, ``menu board``…), or None when empty."""
    kind = str(raw_kind or "").strip().lower().replace("_", " ").replace("-", " ")
    if not kind:
        return None
    if kind.replace(" ", "_") in PHOTO_KINDS:
        return kind.replace(" ", "_")
    if kind in _KIND_SYNONYMS:
        return _KIND_SYNONYMS[kind]
    for synonym, canonical in _KIND_SYNONYMS.items():
        if synonym in kind:
            return canonical
    return PHOTO_KIND_OTHER


def normalize_label(raw: Any) -> dict[str, Any] | None:
    """Coerce a raw model entry (or stored label) into the canonical label shape, or None when unusable."""
    if not isinstance(raw, dict):
        return None
    kind = canonical_kind(raw.get("kind"))
    if kind is None:
        return None
    description = str(raw.get("description", "") or "").strip()[:_MAX_DESCRIPTION_CHARS]
    dishes_raw = raw.get("dishes")
    dishes: list[str] = []
    if isinstance(dishes_raw, list):
        for item in dishes_raw:
            text = str(item or "").strip()[:_MAX_DISH_CHARS]
            if text and text not in dishes:
                dishes.append(text)
            if len(dishes) >= _MAX_DISHES_PER_PHOTO:
                break
    try:
        appeal = int(raw.get("appeal", 0))
    except (TypeError, ValueError):
        appeal = 0
    try:
        version = int(raw.get("version", PHOTO_LABEL_VERSION))
    except (TypeError, ValueError):
        version = PHOTO_LABEL_VERSION
    return {
        "kind": kind,
        "description": description,
        "dishes": dishes,
        "appeal": max(0, min(5, appeal)),
        "version": version,
    }


def is_current_label(label: dict[str, Any] | None) -> bool:
    """Whether a stored label was produced by the current prompt (older ones are re-labelled on use)."""
    return isinstance(label, dict) and int(label.get("version", 0)) == PHOTO_LABEL_VERSION


def is_card_worthy(label: dict[str, Any] | None) -> bool:
    """Whether a labelled photo can illustrate a menu / specialty card (a dish or a drink)."""
    return isinstance(label, dict) and str(label.get("kind", "")) in CARD_WORTHY_KINDS


def is_unfit_for_card(label: dict[str, Any] | None) -> bool:
    """Whether a photo is KNOWN to be wrong on a menu card (truck, menu board, flyer…).

    An unlabelled photo is neither fit nor unfit — it stays a last-resort fallback.
    """
    return isinstance(label, dict) and str(label.get("kind", "")) in PHOTO_KINDS - CARD_WORTHY_KINDS


def labels_for_urls(photo_labels: Any, urls: list[str]) -> dict[str, dict[str, Any]]:
    """The stored labels restricted (and normalised) to the given URLs; labels of an older prompt version are skipped."""
    if not isinstance(photo_labels, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for url in urls:
        label = normalize_label(photo_labels.get(url))
        if label is not None and is_current_label(label):
            result[url] = label
    return result


def rank_card_photos(
    urls: list[str],
    labels: dict[str, dict[str, Any]],
    *,
    exclude: set[str] | None = None,
) -> list[str]:
    """Order photos for menu cards: dishes by appeal first, unlabelled ones next, unfit ones never.

    Args:
        urls: Candidate photo URLs, in their site order (the stable tie-breaker).
        labels: Labels keyed by URL (a missing entry = not analysed yet).
        exclude: URLs already used elsewhere, dropped from the result.

    Returns:
        The usable candidates, best first, without duplicates.
    """
    excluded = exclude or set()
    seen: set[str] = set()
    worthy: list[tuple[int, str]] = []
    unknown: list[str] = []
    for url in urls:
        if not isinstance(url, str) or not url.strip() or url in excluded or url in seen:
            continue
        seen.add(url)
        label = labels.get(url)
        if is_card_worthy(label):
            worthy.append((int(label.get("appeal", 0)) if label else 0, url))
        elif label is None:
            unknown.append(url)
    worthy.sort(key=lambda item: -item[0])
    return [url for _appeal, url in worthy] + unknown
