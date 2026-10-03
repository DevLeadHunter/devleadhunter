"""Multi-phone helpers for a prospect.

A prospect can hold several numbers (Maps, Facebook, a reply from another mobile…). ``phones[0]``
is the primary — the one shown in the table — and ``prospect.phone`` is always kept in sync with
it. The primary may be a business landline, so SMS does NOT target it blindly: it targets the first
*mobile* found across the whole list (see :func:`first_mobile_e164`), read in the prospect's own
country's numbering, and only in a country open to SMS prospecting. Mirrors
:mod:`services.prospect_emails`, with an E.164 dedupe key so « 06 42 19 38 12 » and « +33642193812 »
count as one number.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from services.sms.phone_normalizer import PhoneNumberPlans, to_e164_fr
from services.sms_prospecting_rules import SmsProspectingRules

if TYPE_CHECKING:
    from models.prospect_db import ProspectDB


def _clean(value: object) -> str | None:
    """Return a trimmed phone string, or None when blank/not a string."""
    return value.strip() if isinstance(value, str) and value.strip() else None


def _dedupe_key(phone: str, country: str | None) -> str:
    """Build the identity key of a number — its E.164 form when parseable, else its bare digits."""
    return (
        PhoneNumberPlans.mobile_of_country(phone, country=country)
        or to_e164_fr(phone)
        or "".join(char for char in phone if char.isdigit() or char == "+")
    )


def dedupe_phones(phones: list[object], *, country: str | None = None) -> list[str]:
    """Dedupe phone numbers by E.164 identity, keeping first-seen order and dropping blanks.

    Args:
        phones: The raw numbers, blanks and non-strings included.
        country: The owner's ISO country code, deciding how a national number is read (France when unset).

    Returns:
        The cleaned, deduped numbers in first-seen order.
    """
    seen: set[str] = set()
    result: list[str] = []
    for candidate in phones:
        cleaned = _clean(candidate)
        if cleaned is None:
            continue
        key = _dedupe_key(cleaned, country)
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
    cleaned = dedupe_phones(phones, country=SmsProspectingRules.country_of(prospect))
    prospect.phones = cleaned
    prospect.phone = cleaned[0] if cleaned else None
    return cleaned


def _promote_first_mobile(phones: list[str], country: str) -> list[str]:
    """Move the first mobile of the prospect's country to the front, as the primary, keeping the rest in order.

    Args:
        phones: The deduped, ordered numbers.
        country: The prospect's ISO country code.

    Returns:
        The list with its first mobile at index 0, unchanged when none is a mobile or SMS is closed in that country.
    """
    if not SmsProspectingRules.is_country_open(country):
        return phones
    for index, phone in enumerate(phones):
        if PhoneNumberPlans.mobile_of_country(phone, country=country) is not None:
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
    country = SmsProspectingRules.country_of(prospect)
    current: list[object] = list(prospect.phones or [])
    if not current and prospect.phone:
        current = [prospect.phone]
    combined: list[object] = ([primary] if primary else []) + current + list(add or [])
    phones = dedupe_phones(combined, country=country)
    if primary is None:
        phones = _promote_first_mobile(phones, country)
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
    """Return the E.164 of the first mobile we may text the prospect at, across ALL his numbers, else ``None``.

    A text SMS only reaches a mobile, so every SMS path (relance, cold, campaign) targets the first
    mobile in the list — the display primary is often a business landline we deliberately keep. The
    mobile must belong to the prospect's country (a Swiss ``079`` becomes ``+4179…``, never ``+337…``),
    and that country must be open to SMS prospecting: a Belgian prospect has no mobile to text.

    Args:
        prospect: The prospect to read.

    Returns:
        The first mobile as ``+336…`` / ``+4179…``, or ``None`` when none may be texted.
    """
    country = SmsProspectingRules.country_of(prospect)
    if not SmsProspectingRules.is_country_open(country):
        return None
    for phone in iter_phones(prospect):
        e164 = PhoneNumberPlans.mobile_of_country(phone, country=country)
        if e164 is not None:
            return e164
    return None
