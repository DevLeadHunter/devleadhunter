"""French overseas departments — what differs for a French prospect who lives there.

Martinique, Guadeloupe, French Guiana, Réunion and Mayotte are France for the law, the euro, the SIREN
and the legal pages of a site: their prospects keep ``country = "FR"`` and every French rule. What
differs from mainland France is read here, in one place: the clock (Martinique lives five hours behind
Paris in winter), the dial code of the numbers (a Martinique mobile « 0696 12 34 56 » is
``+596 696 12 34 56``, never ``+33 6 96 12 34 56``), the names an address ends with and, for a department
open to the prospect search, its communes. A prospect's department is read from his address (its postal
code, else the department named at its end), else from his numbers.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from models.prospect_db import ProspectDB

_FRENCH_POSTAL_CODE_RE: re.Pattern[str] = re.compile(r"(?<!\d)(\d{5})(?!\d)")
_NON_ALPHANUMERIC_RE: re.Pattern[str] = re.compile(r"[^a-z0-9]+")
_NATIONAL_NUMBER_DIGITS: int = 9
_NUMBER_PREFIX_DIGITS: int = 3


def _comparison_text(text: str) -> str:
    """Lower-case words without accents, ligatures nor punctuation: « Schœlcher » and « SCHOELCHER » read the same."""
    decomposed = unicodedata.normalize("NFD", text.lower().replace("œ", "oe").replace("æ", "ae"))
    without_accents = "".join(character for character in decomposed if unicodedata.category(character) != "Mn")
    return _NON_ALPHANUMERIC_RE.sub(" ", without_accents).strip()


@dataclass(frozen=True)
class OverseasDepartment:
    """One French overseas department and the facts a prospect living there carries.

    Attributes:
        code: ISO 3166-1 alpha-2 code of the territory (« MQ »), the ``region`` of a search there.
        label: Its French name (« Martinique »).
        postal_prefix: The first three digits of its postal codes (« 972 »).
        timezone: The IANA zone its prospects read the clock in.
        dial_code: The international prefix of its numbers (« +596 »).
        landline_prefixes: The first three digits of its landlines, trunk zero dropped (« 596 »).
        mobile_prefixes: The first three digits of its mobiles, trunk zero dropped (« 696 », « 697 »).
        address_names: The names an address writes at its end (« Martinique »; « La Réunion », « Réunion »).
        communes: Its communes, biggest first, the towns a search walks there; empty when the search is not open there.
    """

    code: str
    label: str
    postal_prefix: str
    timezone: str
    dial_code: str
    landline_prefixes: tuple[str, ...]
    mobile_prefixes: tuple[str, ...]
    address_names: tuple[str, ...]
    communes: tuple[str, ...] = ()

    @property
    def number_prefixes(self) -> tuple[str, ...]:
        """The first three digits of every number of the department, landlines and mobiles."""
        return (*self.landline_prefixes, *self.mobile_prefixes)

    @property
    def is_searchable(self) -> bool:
        """Whether a prospect search can walk the department's communes."""
        return bool(self.communes)

    def owns_national_number(self, national_digits: str) -> bool:
        """Whether nine digits written after the trunk zero (« 696123456 ») are a number of the department."""
        return len(national_digits) == _NATIONAL_NUMBER_DIGITS and national_digits.startswith(self.number_prefixes)

    def owns_e164(self, e164: str) -> bool:
        """Whether a ``+…`` number is one of the department's: Réunion and Mayotte share ``+262``, not their prefixes."""
        return e164.startswith(self.dial_code) and self.owns_national_number(e164[len(self.dial_code) :])

    def is_mobile_e164(self, e164: str) -> bool:
        """Whether a ``+…`` number is a mobile of the department."""
        return self.owns_e164(e164) and e164[len(self.dial_code) :].startswith(self.mobile_prefixes)

    def commune_in(self, text: str | None) -> str | None:
        """
        The commune of the department a text names, the one written last when it names several.

        An address writes its town after its street (« Route de Sainte-Marie, 97220 La Trinité »), and
        Google may glue the town to the street (« Route De Jeanne D'Arc LE LAMENTIN, 97232 »).

        Args:
            text: An address or a line of a listing.

        Returns:
            The commune as the department spells it, or ``None`` when the text names none.
        """
        padded_text = f" {_comparison_text(text or '')} "
        named: list[tuple[int, str]] = []
        for commune in self.communes:
            position = padded_text.rfind(f" {_comparison_text(commune)} ")
            if position >= 0:
                named.append((position + len(_comparison_text(commune)), commune))
        return max(named)[1] if named else None


class FrenchOverseas:
    """The French overseas departments and how a prospect, an address or a number is placed in one."""

    DEPARTMENTS: ClassVar[tuple[OverseasDepartment, ...]] = (
        OverseasDepartment(
            code="GP",
            label="Guadeloupe",
            postal_prefix="971",
            timezone="America/Guadeloupe",
            dial_code="+590",
            landline_prefixes=("590",),
            mobile_prefixes=("690", "691"),
            address_names=("Guadeloupe",),
        ),
        OverseasDepartment(
            code="MQ",
            label="Martinique",
            postal_prefix="972",
            timezone="America/Martinique",
            dial_code="+596",
            landline_prefixes=("596",),
            mobile_prefixes=("696", "697"),
            address_names=("Martinique",),
            communes=(
                "Fort-de-France",
                "Le Lamentin",
                "Le Robert",
                "Schœlcher",
                "Ducos",
                "Saint-Joseph",
                "Sainte-Marie",
                "Le François",
                "Rivière-Salée",
                "La Trinité",
                "Rivière-Pilote",
                "Saint-Esprit",
                "Sainte-Luce",
                "Le Gros-Morne",
                "Le Vauclin",
                "Le Marin",
                "Les Trois-Îlets",
                "Le Lorrain",
                "Le Diamant",
                "Le Morne-Rouge",
                "Case-Pilote",
                "Sainte-Anne",
                "Saint-Pierre",
                "Le Carbet",
                "Les Anses-d'Arlet",
                "Le Marigot",
                "Basse-Pointe",
                "Le Morne-Vert",
                "L'Ajoupa-Bouillon",
                "Bellefontaine",
                "Le Prêcheur",
                "Macouba",
                "Fonds-Saint-Denis",
                "Grand'Rivière",
            ),
        ),
        OverseasDepartment(
            code="GF",
            label="Guyane",
            postal_prefix="973",
            timezone="America/Cayenne",
            dial_code="+594",
            landline_prefixes=("594",),
            mobile_prefixes=("694",),
            address_names=("Guyane", "Guyane française", "French Guiana"),
        ),
        OverseasDepartment(
            code="RE",
            label="La Réunion",
            postal_prefix="974",
            timezone="Indian/Reunion",
            dial_code="+262",
            landline_prefixes=("262", "263"),
            mobile_prefixes=("692", "693"),
            address_names=("La Réunion", "Réunion"),
        ),
        OverseasDepartment(
            code="YT",
            label="Mayotte",
            postal_prefix="976",
            timezone="Indian/Mayotte",
            dial_code="+262",
            landline_prefixes=("269",),
            mobile_prefixes=("639",),
            address_names=("Mayotte",),
        ),
    )

    @classmethod
    def by_code(cls, code: str | None) -> OverseasDepartment | None:
        """The department of an ISO code (« MQ », any case), ``None`` for any other code."""
        cleaned = (code or "").strip().upper()
        return next((department for department in cls.DEPARTMENTS if department.code == cleaned), None)

    @classmethod
    def searchable(cls) -> list[OverseasDepartment]:
        """The departments a prospect search can walk, in declaration order."""
        return [department for department in cls.DEPARTMENTS if department.is_searchable]

    @classmethod
    def address_names(cls) -> tuple[str, ...]:
        """Every name an address of an overseas department ends with."""
        return tuple(name for department in cls.DEPARTMENTS for name in department.address_names)

    @staticmethod
    def postal_code_in(address: str | None) -> str | None:
        """The French postal code an address holds: its last group of five digits, a street number coming first."""
        codes = _FRENCH_POSTAL_CODE_RE.findall(address or "")
        return codes[-1] if codes else None

    @classmethod
    def of_postal_code(cls, postal_code: str | None) -> OverseasDepartment | None:
        """The department of a French postal code (« 97232 » is Martinique), ``None`` for a mainland one."""
        code = (postal_code or "").strip()
        return next((department for department in cls.DEPARTMENTS if code.startswith(department.postal_prefix)), None)

    @classmethod
    def of_address(cls, address: str | None) -> OverseasDepartment | None:
        """
        The department an address is in: by its postal code, else by the department named at its end.

        Args:
            address: An address as a listing writes it (« 35 Imp. Jacinthe, Le Lamentin, Martinique »).

        Returns:
            The department, or ``None`` for a mainland address and for an address that tells neither.
        """
        postal_code = cls.postal_code_in(address)
        if postal_code is not None:
            return cls.of_postal_code(postal_code)
        segments = [segment for segment in (address or "").split(",") if segment.strip()]
        last_segment = _comparison_text(segments[-1]) if segments else ""
        return next(
            (
                department
                for department in cls.DEPARTMENTS
                if any(_comparison_text(name) == last_segment for name in department.address_names)
            ),
            None,
        )

    @classmethod
    def of_national_number(cls, national_digits: str) -> OverseasDepartment | None:
        """The department of a French number's nine digits after the trunk zero (« 696123456 » is Martinique)."""
        return next(
            (department for department in cls.DEPARTMENTS if department.owns_national_number(national_digits)), None
        )

    @classmethod
    def of_e164(cls, e164: str | None) -> OverseasDepartment | None:
        """The department of a ``+…`` number (« +596696123456 » is Martinique), ``None`` for any other number."""
        return next((department for department in cls.DEPARTMENTS if department.owns_e164(e164 or "")), None)

    @classmethod
    def e164_of_international_digits(cls, digits: str) -> str | None:
        """
        The ``+…`` form of a number written with an overseas dial code, its plus or zeros dropped (« 596696123456 »).

        Args:
            digits: The number's digits only, the international prefix (``+`` or ``00``) already removed.

        Returns:
            ``+596696123456``, or ``None`` when the digits are not an overseas number.
        """
        for department in cls.DEPARTMENTS:
            dial_digits = department.dial_code.removeprefix("+")
            if digits.startswith(dial_digits) and department.owns_national_number(digits[len(dial_digits) :]):
                return f"+{digits}"
        return None

    @classmethod
    def of_prospect(cls, prospect: ProspectDB | None) -> OverseasDepartment | None:
        """
        The department a French prospect lives in: by his address, else by the first of his numbers that tells.

        A mainland postal code settles it without the numbers: a mainland business may keep an overseas mobile.

        Args:
            prospect: The prospect, or a stub carrying ``country``, ``address``, ``phones`` and ``phone``.

        Returns:
            The department, or ``None`` for a mainland or foreign prospect and for one nothing places.
        """
        if prospect is None or (getattr(prospect, "country", None) or "FR").strip().upper() != "FR":
            return None
        address = getattr(prospect, "address", None)
        department = cls.of_address(address)
        if department is not None or cls.postal_code_in(address) is not None:
            return department
        # Imported here: the phone normalizer reads this registry to give an overseas number its dial code.
        from services.sms.phone_normalizer import to_e164

        numbers = [*(getattr(prospect, "phones", None) or []), getattr(prospect, "phone", None)]
        for number in numbers:
            if isinstance(number, str) and number.strip():
                department = cls.of_e164(to_e164(number, country="FR"))
                if department is not None:
                    return department
        return None
