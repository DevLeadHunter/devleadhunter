"""Normalise a French phone number to E.164, and tell mobiles from landlines.

smsmode (like every A2P provider) requires E.164 (``+33612345678``). Our scraped
numbers come in every French shape (``06 12 34 56 78``, ``0612345678``,
``+33 6 12…``), and a text SMS can only reach a **mobile** (06/07) — a landline
(01–05) or VoIP (09) silently never receives it, so we must filter before paying
for a send.
"""

from __future__ import annotations

import re

# Any non-digit separator a human or a scraper might use between groups.
_NON_DIGITS: re.Pattern[str] = re.compile(r"\D")
# Separators allowed in a typed international number, and the E.164 shape once they are gone.
_SEPARATORS: re.Pattern[str] = re.compile(r"[\s.()/-]")
# Mobiles the receptionist texts (France, Belgium, Luxembourg, Switzerland, Germany).
SERVED_MOBILE_PREFIXES: tuple[str, ...] = ("+33", "+32", "+352", "+41", "+49")
_E164: re.Pattern[str] = re.compile(r"^\+[1-9]\d{7,14}$")


def to_e164_fr(raw: str | None) -> str | None:
    """Convert a French phone number to E.164 (``+33…``), or ``None`` if invalid.

    Accepts the national form (``0X…``), the already-international form
    (``+33X…`` / ``0033X…``) and any spacing/punctuation. A number that is not a
    plausible 9-digit French subscriber number returns ``None``.

    Args:
        raw: The phone number in any French format.

    Returns:
        The number as ``+33XXXXXXXXX``, or ``None`` when it is not a valid FR number.
    """
    if not raw:
        return None
    digits = _NON_DIGITS.sub("", raw)
    if digits.startswith("0033"):
        digits = digits[4:]
    elif digits.startswith("33") and len(digits) == 11:
        digits = digits[2:]
    elif digits.startswith("0"):
        digits = digits[1:]
    # A French subscriber number is 9 digits, first digit 1–9.
    if len(digits) != 9 or digits[0] == "0":
        return None
    return f"+33{digits}"


def is_mobile_fr(raw: str | None) -> bool:
    """Whether a French number is a mobile (06/07) — the only kind an SMS reaches.

    Args:
        raw: The phone number in any French format.

    Returns:
        ``True`` when the normalised number is a French mobile (``+336…`` / ``+337…``).
    """
    e164 = to_e164_fr(raw)
    return bool(e164 and e164[3] in {"6", "7"})


def to_e164_mobile(raw: str | None, *, country: str = "FR") -> str | None:
    """E.164 form of a number able to receive an SMS, French or not.

    A French number must be a mobile (06 / 07): in national form (``06 12 34 56 78``, leading 0
    required) only for a French business, or in international form (``+33 6…``, ``+33 (0)6…``).
    Any other country's number must be typed in international form (``+352 621 …``, ``0032 …``):
    a Luxembourg ``621 123 456`` or a Swiss ``079 …`` typed nationally would otherwise read as a
    stranger's French mobile. Foreign mobile ranges are not checked.

    Args:
        raw: The phone number as typed.
        country: ISO code of the business's country, deciding how a national number is read.

    Returns:
        The number as ``+…``, or ``None`` when it cannot receive an SMS.
    """
    compact = _SEPARATORS.sub("", (raw or "").replace("(0)", "").strip())
    if not compact:
        return None
    if compact.startswith("00"):
        compact = "+" + compact[2:]
    if compact.startswith("+33"):
        return to_e164_fr(compact) if is_mobile_fr(compact) else None
    if compact.startswith("+"):
        return compact if _E164.match(compact) else None
    if country.upper() != "FR" or not compact.startswith("0"):
        return None
    return to_e164_fr(compact) if is_mobile_fr(compact) else None
