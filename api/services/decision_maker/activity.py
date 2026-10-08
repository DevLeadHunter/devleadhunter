"""Coherence between a prospect's trade and the registry's declared activity.

The geographic check clears a registry match sitting in the prospect's own
département — but that is exactly where a same-town HOMONYM slips through:
« Mayer Paysagiste » (a landscaper) resolved to « JOSUE MAYER », a company
registered in Angers for INDUSTRIAL CLEANING (NAF 81.22Z). Name + town agreed,
so the match scored 95 %, yet the activity has nothing to do with landscaping —
almost certainly the wrong person.

This module answers « does this NAF code fit that trade? » so the resolver can
demote such a match to « à confirmer » instead of trusting it automatically.

Deliberately conservative: an unmapped trade or a missing NAF code yields
``None`` (« can't tell » → never demote), so the guard only ever fires on a
POSITIVE mismatch and never blocks a trade we simply don't model.
"""

from __future__ import annotations

from services.decision_maker.normalize import fold

# Trade word (folded, as emitted by TradeNormalizer) → the dot-less, upper-case
# NAF prefixes coherent with it. Matched with ``startswith`` against the
# normalised code, so "8130" covers "81.30Z". Kept intentionally broad — an
# artisan often declares a neighbouring activity (a landscaper filed under
# forestry or earthworks). The goal is to catch the gross mismatch (cleaning vs
# landscaping), never to police the exact sub-class.
_NAF_BY_TRADE: dict[str, frozenset[str]] = {
    "garagiste": frozenset({"4520", "4532", "4540", "4519", "4511", "4531"}),
    "carrossier": frozenset({"4520", "4532"}),
    "plombier": frozenset({"4322", "4329"}),
    "chauffagiste": frozenset({"4322", "4329"}),
    "electricien": frozenset({"4321", "4329", "4399", "4321A"}),
    "barbier": frozenset({"9602"}),
    "coiffeur": frozenset({"9602"}),
    "dentiste": frozenset({"8623", "8622"}),
    "paysagiste": frozenset({"8130", "0161", "0240", "4312", "0130"}),
    "fleuriste": frozenset({"4776", "0130", "4619"}),
    "menuisier": frozenset({"4332", "1623", "3109", "3101"}),
    "serrurier": frozenset({"4332", "2572", "4399", "2562"}),
    "couvreur": frozenset({"4391", "4399"}),
    "macon": frozenset({"4399", "4120", "4211", "4291", "4312"}),
    "peintre": frozenset({"4334"}),
    "carreleur": frozenset({"4333"}),
    "boulanger": frozenset({"1071", "4724"}),
    "patissier": frozenset({"1071", "4724"}),
    "boucher": frozenset({"1013", "1011", "4722", "4632"}),
    "traiteur": frozenset({"5621", "5629", "1085", "1089"}),
    "restaurant": frozenset({"5610", "5630", "5621"}),
}

_OFFICIAL_ACTIVITY_CODES: tuple[str, ...] = (
    "01.30Z",
    "01.61Z",
    "02.40Z",
    "10.11Z",
    "10.13A",
    "10.13B",
    "10.71A",
    "10.71B",
    "10.71C",
    "10.71D",
    "10.85Z",
    "10.89Z",
    "16.23Z",
    "25.62A",
    "25.62B",
    "25.72Z",
    "31.01Z",
    "31.09A",
    "31.09B",
    "41.20A",
    "41.20B",
    "42.11Z",
    "42.91Z",
    "43.12A",
    "43.12B",
    "43.21A",
    "43.21B",
    "43.22A",
    "43.22B",
    "43.29A",
    "43.29B",
    "43.32A",
    "43.32B",
    "43.32C",
    "43.33Z",
    "43.34Z",
    "43.91A",
    "43.91B",
    "43.99A",
    "43.99B",
    "43.99C",
    "43.99D",
    "43.99E",
    "45.11Z",
    "45.19Z",
    "45.20A",
    "45.20B",
    "45.31Z",
    "45.32Z",
    "45.40Z",
    "46.19A",
    "46.19B",
    "46.32A",
    "46.32B",
    "46.32C",
    "47.22Z",
    "47.24Z",
    "47.76Z",
    "56.10A",
    "56.10B",
    "56.10C",
    "56.21Z",
    "56.29A",
    "56.29B",
    "56.30Z",
    "81.30Z",
    "86.22A",
    "86.22B",
    "86.22C",
    "86.23Z",
    "96.02A",
    "96.02B",
)


def _normalise_naf(naf_code: str | None) -> str | None:
    """Strip separators and case from a NAF code (« 81.30Z » → « 8130Z »)."""
    if not naf_code:
        return None
    cleaned = "".join(char for char in naf_code if char.isalnum()).upper()
    return cleaned or None


def activity_consistency(trade: str | None, naf_code: str | None) -> bool | None:
    """Tell whether ``naf_code`` fits ``trade``.

    Args:
        trade: The prospect's normalised trade word (« paysagiste »,
            « garagiste »… as emitted by :class:`TradeNormalizer`).
        naf_code: The SIRENE main-activity code of the registry match
            (« 81.30Z »), or None when the source carries no activity.

    Returns:
        ``True`` when the code sits in a family coherent with the trade,
        ``False`` on a positive mismatch, and ``None`` when it cannot be judged
        (unmapped trade or missing code) — callers MUST treat None as neutral
        and never demote on it.
    """
    prefixes = _NAF_BY_TRADE.get(fold(trade or ""))
    normalised = _normalise_naf(naf_code)
    if not prefixes or not normalised:
        return None
    return any(normalised.startswith(prefix) for prefix in prefixes)


def has_known_activity(trade: str | None) -> bool:
    """
    Whether the activity codes coherent with a trade are known, so a registry company's code can be checked.

    Args:
        trade: The prospect's normalised trade word.

    Returns:
        True when :func:`activity_consistency` can judge a code for that trade.
    """
    return fold(trade or "") in _NAF_BY_TRADE


def activity_codes_of(trade: str | None) -> list[str]:
    """
    The official activity codes coherent with a trade, to filter a registry search on them.

    Args:
        trade: The prospect's normalised trade word.

    Returns:
        The codes as the registry writes them (« 43.21A »); empty for a trade without known codes.
    """
    prefixes = _NAF_BY_TRADE.get(fold(trade or ""), frozenset())
    return [code for code in _OFFICIAL_ACTIVITY_CODES if any(code.replace(".", "").startswith(p) for p in prefixes)]


_MAIN_NAF_BY_TRADE: dict[str, str] = {
    "garagiste": "4520",
    "carrossier": "4520",
    "plombier": "4322",
    "chauffagiste": "4322",
    "electricien": "4321",
    "paysagiste": "8130",
    "menuisier": "4332",
    "couvreur": "4391",
    "peintre": "4334",
    "carreleur": "4333",
}


def is_main_activity(trade: str | None, naf_code: str | None) -> bool:
    """
    Whether a code is the activity the trade declares first (« 43.21A » for an electrician, not « 43.99C »).

    Args:
        trade: The prospect's normalised trade word.
        naf_code: A registry company's main activity code.

    Returns:
        True when the code is the trade's main activity.
    """
    main_prefix = _MAIN_NAF_BY_TRADE.get(fold(trade or ""))
    normalised = _normalise_naf(naf_code)
    return bool(main_prefix and normalised and normalised.startswith(main_prefix))
