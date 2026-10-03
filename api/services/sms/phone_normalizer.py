"""Normalise a phone number to E.164, and tell mobiles from landlines.

smsmode (like every A2P provider) requires E.164 (``+33612345678``). Our scraped
numbers come in every French shape (``06 12 34 56 78``, ``0612345678``,
``+33 6 12…``), and a text SMS can only reach a **mobile** (06/07) — a landline
(01–05) or VoIP (09) silently never receives it, so we must filter before paying
for a send. A national number only reads once its country is known: a Swiss ``079``
typed without its country code is also a valid French ``07`` mobile.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar

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


@dataclass(frozen=True)
class CountryNumbering:
    """How a country writes its numbers: its dial code, the start of its mobile ranges, its national form."""

    iso_code: str
    dial_code: str
    mobile_prefixes: tuple[str, ...]
    national_form_starts_with_zero: bool = True

    def is_mobile(self, e164: str) -> bool:
        """Whether an E.164 number of this country sits in one of its mobile ranges.

        Args:
            e164: A number already known to start with this country's dial code.

        Returns:
            ``True`` when the subscriber part starts with a mobile prefix.
        """
        return e164[len(self.dial_code) :].startswith(self.mobile_prefixes)


class PhoneNumberPlans:
    """The numbering plans of the countries we text, and how a number reads in one of them."""

    PLANS: ClassVar[tuple[CountryNumbering, ...]] = (
        CountryNumbering(iso_code="FR", dial_code="+33", mobile_prefixes=("6", "7")),
        CountryNumbering(iso_code="BE", dial_code="+32", mobile_prefixes=("4",)),
        CountryNumbering(iso_code="LU", dial_code="+352", mobile_prefixes=("6",), national_form_starts_with_zero=False),
        CountryNumbering(iso_code="CH", dial_code="+41", mobile_prefixes=("74", "75", "76", "77", "78", "79")),
        CountryNumbering(iso_code="DE", dial_code="+49", mobile_prefixes=("15", "16", "17")),
    )

    @classmethod
    def of_country(cls, country: str | None) -> CountryNumbering | None:
        """The numbering plan of an ISO country code, ``None`` for a country we do not text.

        Args:
            country: ISO 3166-1 alpha-2 code, any case, ``None`` read as France.

        Returns:
            The matching plan, or ``None``.
        """
        cleaned = (country or "FR").strip().upper()
        return next((plan for plan in cls.PLANS if plan.iso_code == cleaned), None)

    @classmethod
    def of_e164(cls, e164: str | None) -> CountryNumbering | None:
        """The numbering plan an E.164 number belongs to, by its dial code.

        Args:
            e164: A number in ``+…`` form.

        Returns:
            The plan whose dial code starts the number, or ``None``.
        """
        if not e164:
            return None
        return next((plan for plan in cls.PLANS if e164.startswith(plan.dial_code)), None)

    @classmethod
    def country_of_e164(cls, e164: str | None) -> str | None:
        """The ISO code of the country an E.164 number belongs to, ``None`` for a country we do not text.

        Args:
            e164: A number in ``+…`` form.

        Returns:
            ``"FR"``, ``"CH"``… or ``None``.
        """
        plan = cls.of_e164(e164)
        return plan.iso_code if plan is not None else None

    @classmethod
    def mobile_of_country(cls, raw: str | None, *, country: str | None) -> str | None:
        """E.164 form of a prospect's number when it is a mobile OF HIS COUNTRY, the only one we prospect by SMS.

        A national number is read in the prospect's numbering plan: ``079 123 45 67`` is ``+41791234567``
        for a Swiss prospect and ``+33791234567`` for a French one. An international number is kept as
        typed, then refused when its dial code is another country's or its range is not a mobile one
        (``+41 22 …`` is a Geneva landline). A French prospect's number is read exactly as
        :func:`to_e164_fr` and :func:`is_mobile_fr` always read it.

        Args:
            raw: The phone number as stored on the prospect.
            country: The prospect's ISO country code, ``None`` read as France.

        Returns:
            The number as ``+…``, or ``None`` when it is not a mobile of that country.
        """
        plan = cls.of_country(country)
        if plan is None:
            return None
        if plan.iso_code == "FR":
            return to_e164_fr(raw) if is_mobile_fr(raw) else None
        compact = _SEPARATORS.sub("", (raw or "").replace("(0)", "").strip())
        if not compact:
            return None
        if compact.startswith("00"):
            compact = "+" + compact[2:]
        if not compact.startswith("+"):
            if not compact.isdigit():
                return None
            has_trunk_zero = plan.national_form_starts_with_zero and compact.startswith("0")
            compact = plan.dial_code + (compact[1:] if has_trunk_zero else compact)
        if not _E164.match(compact) or not compact.startswith(plan.dial_code):
            return None
        return compact if plan.is_mobile(compact) else None

    @staticmethod
    def international_to_e164(raw: str | None) -> str | None:
        """E.164 form of a number written internationally: ``+41 79 …``, ``0041 79 …`` or ``41791234567``.

        smsmode writes the numbers of its callbacks without the plus.

        Args:
            raw: The number, international form with or without its plus.

        Returns:
            The number as ``+…``, or ``None`` when it is not a plausible international number.
        """
        compact = _SEPARATORS.sub("", (raw or "").strip())
        if not compact:
            return None
        if compact.startswith("00"):
            compact = "+" + compact[2:]
        elif compact.isdigit():
            compact = "+" + compact
        return compact if _E164.match(compact) else None


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
    plan = PhoneNumberPlans.of_e164(e164)
    if e164 is None or plan is None:
        return None
    return e164 if plan.is_mobile(e164) else None
