"""Multi-phone helpers for a prospect.

A prospect can hold several numbers (Maps, Facebook, a reply from another mobile…). ``phones[0]``
is the primary — the one shown in the table — and ``prospect.phone`` is always kept in sync with
it. The primary may be a business landline, so SMS does NOT target it blindly: it targets the first
*mobile* (06/07) found across the whole list (see :func:`first_mobile_e164`). Mirrors
:mod:`services.prospect_emails`, with an E.164 dedupe key so « 06 42 19 38 12 » and « +33642193812 »
count as one number.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from services.sms.phone_normalizer import is_mobile_fr, to_e164_fr

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


def _promote_first_mobile(phones: list[str]) -> list[str]:
    """Move the first mobile (06/07) to the front so it becomes the primary, keeping the rest in order.

    Args:
        phones: The deduped, ordered numbers.

    Returns:
        The list with its first mobile at index 0, or the list unchanged when none is a mobile.
    """
    for index, phone in enumerate(phones):
        if is_mobile_fr(phone):
            return phones if index == 0 else [phone, *phones[:index], *phones[index + 1 :]]
    return phones


def sync_prospect_phones(
    prospect: ProspectDB,
    *,
    add: list[object] | None = None,
    primary: str | None = None,
) -> None:
    """Rebuild the prospect's phone list (deduped) and keep ``phone`` synced to ``phones[0]``.

    On the discovery path (no forced ``primary``), a mobile takes the primary slot: SMS is the
    only channel a mobile unlocks, so a freshly found mobile outranks a business landline. A
    forced ``primary`` is always honoured (the human's explicit choice in the drawer wins).

    Args:
        prospect: The prospect to update in place.
        add: Newly discovered numbers to fold in (after the current ones).
        primary: A number to force to the front (e.g. the human's chosen primary).
    """
    current: list[object] = list(prospect.phones or [])
    if not current and prospect.phone:
        current = [prospect.phone]
    combined: list[object] = ([primary] if primary else []) + current + list(add or [])
    phones = dedupe_phones(combined)
    if primary is None:
        phones = _promote_first_mobile(phones)
    prospect.phones = phones
    prospect.phone = phones[0] if phones else None


def iter_phones(prospect: ProspectDB) -> list[str]:
    """Return the prospect's known numbers, primary first, falling back to the single ``phone``.

    Args:
        prospect: The prospect to read (``phones`` may be absent on legacy rows).

    Returns:
        The stored ``phones`` (blanks dropped), or ``[phone]`` when only the legacy field is set.
    """
    raw = getattr(prospect, "phones", None) or []
    phones = [phone for phone in raw if isinstance(phone, str) and phone.strip()]
    if not phones and prospect.phone:
        phones = [prospect.phone]
    return phones


def first_mobile_e164(prospect: ProspectDB) -> str | None:
    """Return the E.164 of the prospect's first mobile (06/07) across ALL its numbers, else ``None``.

    A text SMS only reaches a mobile, so every SMS path (relance, cold, campaign) targets the first
    mobile in the list — the display primary is often a business landline we deliberately keep.

    Args:
        prospect: The prospect to read.

    Returns:
        The first mobile as ``+336…``/``+337…``, or ``None`` when no number is a French mobile.
    """
    for phone in iter_phones(prospect):
        if is_mobile_fr(phone):
            return to_e164_fr(phone)
    return None
