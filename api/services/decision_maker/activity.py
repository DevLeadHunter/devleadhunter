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
