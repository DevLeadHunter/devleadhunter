"""Multi-phone helpers for a prospect.

A prospect can hold several numbers (Maps, Facebook, a reply from another mobile…). ``phones[0]``
is the primary — the one shown in the table and used to send SMS — and ``prospect.phone`` is
always kept in sync with it. Mirrors :mod:`services.prospect_emails`, with an E.164 dedupe key so
« 06 42 19 38 12 » and « +33642193812 » count as one number.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from services.sms.phone_normalizer import to_e164_fr

if TYPE_CHECKING:
    from models.prospect_db import ProspectDB


def _clean(value: object) -> str | None:
    """Return a trimmed phone string, or None when blank/not a string."""
    return value.strip() if isinstance(value, str) and value.strip() else None


def _dedupe_key(phone: str) -> str:
    """Build the identity key of a number — its E.164 form when parseable, else its bare digits."""
    return to_e164_fr(phone) or "".join(char for char in phone if char.isdigit() or char == "+")


def dedupe_phones(phones: list[object]) -> list[str]:
    """Dedupe phone numbers by E.164 identity, keeping first-seen order and dropping blanks."""
    seen: set[str] = set()
    result: list[str] = []
    for candidate in phones:
        cleaned = _clean(candidate)
        if cleaned is None:
            continue
        key = _dedupe_key(cleaned)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def set_prospect_phones(prospect: ProspectDB, phones: list[object]) -> list[str]:
    """Replace the prospect's whole phone list with ``phones`` (deduped, order kept).

    This is the human-edit path: the caller sends the full ordered list, so it covers reorder,
    add and remove in one shot. ``phones[0]`` becomes the primary and ``phone`` is synced to it.

    Args:
        prospect: The prospect to update in place.
        phones: The new ordered list; the first entry becomes the primary.

    Returns:
        The cleaned, deduped list actually stored.
    """
    cleaned = dedupe_phones(phones)
    prospect.phones = cleaned
    prospect.phone = cleaned[0] if cleaned else None
    return cleaned


def sync_prospect_phones(
    prospect: ProspectDB,
    *,
    add: list[object] | None = None,
    primary: str | None = None,
) -> None:
    """Rebuild the prospect's phone list (deduped) and keep ``phone`` synced to ``phones[0]``.

    Args:
        prospect: The prospect to update in place.
        add: Newly discovered numbers to fold in (after the current ones — never promoted to primary).
        primary: A number to force to the front (e.g. the human's chosen primary).
    """
    current: list[object] = list(prospect.phones or [])
    if not current and prospect.phone:
        current = [prospect.phone]
    combined: list[object] = ([primary] if primary else []) + current + list(add or [])
    phones = dedupe_phones(combined)
    prospect.phones = phones
    prospect.phone = phones[0] if phones else None
