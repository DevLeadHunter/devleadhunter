"""Normalise a phone number to E.164 the way its country writes it, and tell French mobiles from landlines.

smsmode (like every A2P provider) requires E.164 (``+33612345678``). Our scraped
numbers come in every French shape (``06 12 34 56 78``, ``0612345678``,
``+33 6 12…``), and a text SMS can only reach a **mobile** (06/07) — a landline
(01–05) or VoIP (09) silently never receives it, so we must filter before paying
for a send. A national number is read in the country of the business that owns it
(``prospects.country``): a Québec « 514 555-0199 » is ``+15145550199`` and is never
mistaken for a French number.
"""

from __future__ import annotations

import re

from services.country_profiles import CountryProfiles

# Any non-digit separator a human or a scraper might use between groups.
_NON_DIGITS: re.Pattern[str] = re.compile(r"\D")
# Separators allowed in a typed international number, and the E.164 shape once they are gone.
_SEPARATORS: re.Pattern[str] = re.compile(r"[\s.()/-]")
# Mobiles the receptionist texts (France, Belgium, Luxembourg, Switzerland, Germany).
SERVED_MOBILE_PREFIXES: tuple[str, ...] = ("+33", "+32", "+352", "+41", "+49")
_E164: re.Pattern[str] = re.compile(r"^\+[1-9]\d{7,14}$")
# A North American subscriber number: area code and exchange both start with 2–9, ten digits in all.
_NANP_SUBSCRIBER: re.Pattern[str] = re.compile(r"^[2-9]\d{2}[2-9]\d{6}$")
# Countries whose national numbers carry no trunk « 0 » to strip (Luxembourg dials 621 … directly).
_NO_TRUNK_PREFIX_COUNTRIES: frozenset[str] = frozenset({"LU"})


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


def to_e164_nanp(raw: str | None) -> str | None:
    """Convert a North American number (Canada, United States) to E.164 (``+1NPANXXXXXX``).

    Accepts the ten-digit national form (``514 555-0199``, ``(514) 555-0199``), the eleven-digit
    form with its country code (``1 514 555 0199``, ``+1 514…``) and the European international
    prefix (``001 514…``). A number whose area code or exchange starts with 0 or 1 is not a
    subscriber number and returns ``None``.

    Args:
        raw: The phone number in any North American format.

    Returns:
        The number as ``+1XXXXXXXXXX``, or ``None`` when it is not a valid NANP number.
    """
    if not raw:
        return None
    digits = _NON_DIGITS.sub("", raw)
    if digits.startswith("001"):
        digits = digits[3:]
    elif len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if not _NANP_SUBSCRIBER.match(digits):
        return None
    return f"+1{digits}"


def to_e164(raw: str | None, *, country: str = "FR") -> str | None:
    """E.164 form of a number as a business of ``country`` writes it, mobile or landline.

    An international form (``+41 22 …``, ``0032 …``) is read as such whatever the country. A
    national form is read in the business's country: ``06 12 34 56 78`` is French only for a
    French business, ``514 555-0199`` is ``+1514…`` for a Canadian one, ``079 123 45 67`` is
    ``+4179…`` for a Swiss one. Nothing is validated beyond the shape (the SMS mobile rules live
    in :func:`to_e164_mobile`).

    Args:
        raw: The phone number as typed or scraped.
        country: ISO code of the business's country, deciding how a national number is read.

    Returns:
        The number as ``+…``, or ``None`` when it has no plausible shape.
    """
    compact = _SEPARATORS.sub("", (raw or "").replace("(0)", "").strip())
    if not compact:
        return None
    if compact.startswith("00"):
        compact = "+" + compact[2:]
    if compact.startswith("+33"):
        return to_e164_fr(compact)
    if compact.startswith("+1"):
        return to_e164_nanp(compact)
    if compact.startswith("+"):
        return compact if _E164.match(compact) else None
    profile = CountryProfiles.get(country)
    if profile.code == "FR":
        return to_e164_fr(compact)
    if profile.code == "CA":
        return to_e164_nanp(compact)
    national = compact[1:] if compact.startswith("0") and profile.code not in _NO_TRUNK_PREFIX_COUNTRIES else compact
    candidate = f"{profile.dial_code}{national}"
    return candidate if national.isdigit() and _E164.match(candidate) else None


def format_phone_for_display(raw: str | None, *, country: str = "FR") -> str:
    """The number as a reader of ``country`` expects it on a site or in a message.

    France groups ten digits by two (``06 12 34 56 78``); Québec writes the area code apart and
    hyphenates the line (``514 555-0199``). Another country, or a number of no known shape, keeps
    what was typed.

    Args:
        raw: The phone number as stored.
        country: ISO code of the business's country.

    Returns:
        The display form, empty for an empty input.
    """
    if not raw or not raw.strip():
        return ""
    e164 = to_e164(raw, country=country)
    if e164 is None:
        return raw.strip()
    if e164.startswith("+1"):
        national = e164[2:]
        return f"{national[:3]} {national[3:6]}-{national[6:]}"
    if e164.startswith("+33"):
        national = f"0{e164[3:]}"
        return " ".join(national[index : index + 2] for index in range(0, 10, 2))
    return raw.strip()


def to_e164_mobile(raw: str | None, *, country: str = "FR") -> str | None:
    """E.164 form of a number able to receive an SMS, French or not.

    A French number must be a mobile (06 / 07): in national form (``06 12 34 56 78``, leading 0
    required) only for a French business, or in international form (``+33 6…``, ``+33 (0)6…``).
    A Canadian business's ten-digit number (``514 555-0199``) reads as ``+1514…``: the plan does
    not tell a cellular from a landline, so the number is kept and the country rule of the SMS
    guard decides (no cold SMS to Canada). Any other country's number must be typed in
    international form (``+352 621 …``, ``0032 …``): a Luxembourg ``621 123 456`` or a Swiss
    ``079 …`` typed nationally would otherwise read as a stranger's French mobile. Foreign mobile
    ranges are not checked.

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
    if compact.startswith("+1"):
        return to_e164_nanp(compact)
    if compact.startswith("+"):
        return compact if _E164.match(compact) else None
    if country.upper() == "CA":
        return to_e164_nanp(compact)
    if country.upper() != "FR" or not compact.startswith("0"):
        return None
    return to_e164_fr(compact) if is_mobile_fr(compact) else None


# The mobile ranges of the countries the receptionist texts, after the country code.
_SERVED_MOBILE_RANGES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("+33", ("6", "7")),
    ("+32", ("4",)),
    ("+352", ("6",)),
    ("+41", ("74", "75", "76", "77", "78", "79")),
    ("+49", ("15", "16", "17")),
)


def to_served_mobile(raw: str | None, *, country: str = "FR") -> str | None:
    """E.164 form of a mobile the receptionist may text: France, Belgium, Luxembourg, Switzerland or Germany.

    A landline of those countries (``+32 2 …``, ``+41 22 …``) and any number of another country are refused:
    an alert would either never arrive or be billed as international.

    Args:
        raw: The phone number as typed.
        country: ISO code of the business's country, deciding how a national number is read.

    Returns:
        The number as ``+…``, or ``None`` when it is not a served mobile.
    """
    e164 = to_e164_mobile(raw, country=country)
    if e164 is None:
        return None
    for prefix, mobile_starts in _SERVED_MOBILE_RANGES:
        if e164.startswith(prefix):
            return e164 if e164[len(prefix) :].startswith(mobile_starts) else None
    return None
