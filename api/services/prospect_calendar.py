"""The calendar a prospect lives by: the clock he reads and the public holidays he takes off.

Every send slot of a prospect is placed on it: the send policy's hours and weekdays are read on his clock, and his
public holidays are days off like a weekend. A Martinique prospect, French in every other respect, thus receives his
emails on Fort-de-France's clock, never on a French holiday nor on May 22nd; a Swiss one is spared August 1st and
emailed on November 11th.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from services.country_profiles import CountryProfiles
from services.french_overseas import FrenchOverseas
from services.public_holidays import PublicHolidays

if TYPE_CHECKING:
    from models.prospect_db import ProspectDB


@dataclass(frozen=True)
class ProspectCalendar:
    """The clock and the public holidays of the place a prospect works.

    Attributes:
        timezone_name: The IANA zone of his clock (« America/Martinique »).
        country: ISO 3166-1 alpha-2 code of his country (« CH »), whose public holidays he takes off.
        region: His French overseas department (« MQ »), whose holidays replace the mainland ones; ``None`` elsewhere.
    """

    timezone_name: str
    country: str
    region: str | None = None

    @classmethod
    def of_prospect(cls, prospect: ProspectDB | None) -> ProspectCalendar:
        """
        The calendar of a prospect: his French overseas department's, else his country's.

        An unknown or closed country reads as France, like everywhere else in the product.

        Args:
            prospect: The prospect, a stub carrying ``country``, ``address``, ``phones`` and ``phone``, or ``None``.

        Returns:
            His clock and the place his public holidays are read from.
        """
        department = FrenchOverseas.of_prospect(prospect)
        profile = CountryProfiles.get(getattr(prospect, "country", None))
        if department is None:
            return cls(timezone_name=profile.timezone, country=profile.code)
        return cls(timezone_name=department.timezone, country=profile.code, region=department.code)

    def is_public_holiday(self, day: date) -> bool:
        """
        Whether *day* is a public holiday where the prospect works.

        Args:
            day: A calendar day on the prospect's clock.

        Returns:
            ``True`` on a holiday of his overseas department, else of his country.
        """
        if self.region is not None:
            return day in PublicHolidays.french_overseas_department(self.region, day.year)
        return day in PublicHolidays.for_country(self.country, day.year)
