"""Legal send window for marketing SMS, evaluated in the prospect's country — a HARD guardrail.

Marketing SMS is allowed Mon–Fri 08:00–20:00 and Sat 10:00–19:00, and NEVER on Sunday
or a public holiday. These are the French legal hours, applied as the floor in every
country we prospect; the clock and the holidays are the prospect's own (a Swiss prospect
is texted on Zurich time and spared on August 1st, not on July 14th). Whatever an operator
configures, a send outside the window is refused and deferred to the next legal slot.
The operator's planning views (forecast, reschedule) read the French window.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from services.country_profiles import CountryProfiles

# Weekday (0 = Monday … 6 = Sunday) to (open, close) local time; a missing weekday is closed.
_OPENING_HOURS: dict[int, tuple[time, time]] = {
    0: (time(8, 0), time(20, 0)),
    1: (time(8, 0), time(20, 0)),
    2: (time(8, 0), time(20, 0)),
    3: (time(8, 0), time(20, 0)),
    4: (time(8, 0), time(20, 0)),
    5: (time(10, 0), time(19, 0)),
}

_MAXIMUM_CLOSED_DAYS: int = 14


class PublicHolidays:
    """National public holidays per country, the days no marketing SMS leaves.

    Only the days observed in the whole country are listed: Swiss cantonal holidays (January 2nd,
    Corpus Christi, All Saints, December 26th…) vary from canton to canton and are not modelled.
    """

    @staticmethod
    def easter_sunday(year: int) -> date:
        """Easter Sunday for *year* (Anonymous Gregorian algorithm).

        Args:
            year: The calendar year.

        Returns:
            The date of Easter Sunday.
        """
        a = year % 19
        b, c = divmod(year, 100)
        d, e = divmod(b, 4)
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i, k = divmod(c, 4)
        m = (32 + 2 * e + 2 * i - h - k) % 7
        n = (a + 11 * h + 22 * m) // 451
        month, day = divmod(h + m - 7 * n + 114, 31)
        return date(year, month, day + 1)

    @classmethod
    def france(cls, year: int) -> set[date]:
        """French national public holidays (métropole) for *year*.

        Args:
            year: The calendar year.

        Returns:
            The set of holiday dates.
        """
        easter = cls.easter_sunday(year)
        return {
            date(year, 1, 1),  # Jour de l'an
            easter + timedelta(days=1),  # Lundi de Pâques
            date(year, 5, 1),  # Fête du Travail
            date(year, 5, 8),  # Victoire 1945
            easter + timedelta(days=39),  # Ascension
            easter + timedelta(days=50),  # Lundi de Pentecôte
            date(year, 7, 14),  # Fête nationale
            date(year, 8, 15),  # Assomption
            date(year, 11, 1),  # Toussaint
            date(year, 11, 11),  # Armistice 1918
            date(year, 12, 25),  # Noël
        }

    @classmethod
    def switzerland(cls, year: int) -> set[date]:
        """Swiss public holidays observed in every canton for *year*.

        Args:
            year: The calendar year.

        Returns:
            The set of holiday dates.
        """
        easter = cls.easter_sunday(year)
        return {
            date(year, 1, 1),  # Nouvel An
            easter - timedelta(days=2),  # Vendredi saint
            easter + timedelta(days=1),  # Lundi de Pâques
            easter + timedelta(days=39),  # Ascension
            easter + timedelta(days=50),  # Lundi de Pentecôte
            date(year, 8, 1),  # Fête nationale
            date(year, 12, 25),  # Noël
        }

    @classmethod
    def for_country(cls, country: str | None, year: int) -> set[date]:
        """The public holidays of a country for *year*, the French ones for a country without its own list.

        Args:
            country: ISO 3166-1 alpha-2 code, any case.
            year: The calendar year.

        Returns:
            The set of holiday dates.
        """
        holidays_by_country: dict[str, Callable[[int], set[date]]] = {"FR": cls.france, "CH": cls.switzerland}
        return holidays_by_country.get((country or "FR").strip().upper(), cls.france)(year)


class SmsSendWindow:
    """The legal marketing-SMS window of one country: its clock, its holidays, the next open slot."""

    def __init__(self, country: str | None) -> None:
        """Bind the window to a country's timezone and holidays (France for an undeclared country).

        Args:
            country: ISO 3166-1 alpha-2 code of the prospect's country.
        """
        profile = (CountryProfiles.declared(country) if country else None) or CountryProfiles.get(country)
        self.country: str = profile.code
        self.timezone: ZoneInfo = ZoneInfo(profile.timezone)

    def now(self) -> datetime:
        """The current local time of the country, naive, for the window check.

        Returns:
            The current local time without tzinfo.
        """
        return datetime.now(self.timezone).replace(tzinfo=None)

    def to_utc_naive(self, local_moment: datetime) -> datetime:
        """Convert a naive local datetime of the country to naive UTC, the API's storage convention.

        Args:
            local_moment: A naive local datetime.

        Returns:
            The same instant as a naive UTC datetime.
        """
        return local_moment.replace(tzinfo=self.timezone).astimezone(UTC).replace(tzinfo=None)

    def to_local_naive(self, utc_moment: datetime) -> datetime:
        """Convert a naive UTC datetime to the country's naive local time, for window checks.

        Args:
            utc_moment: A naive UTC datetime.

        Returns:
            The same instant as a naive local datetime.
        """
        return utc_moment.replace(tzinfo=UTC).astimezone(self.timezone).replace(tzinfo=None)

    def is_public_holiday(self, day: date) -> bool:
        """Whether *day* is a public holiday of the country.

        Args:
            day: The calendar day.

        Returns:
            ``True`` on a national holiday.
        """
        return day in PublicHolidays.for_country(self.country, day.year)

    def is_open(self, local_moment: datetime) -> bool:
        """Whether a marketing SMS may legally be sent at *local_moment*.

        Args:
            local_moment: A naive datetime in the country's local time.

        Returns:
            ``True`` inside the window, ``False`` at night, on Sunday or on a holiday.
        """
        if self.is_public_holiday(local_moment.date()):
            return False
        opening_hours = _OPENING_HOURS.get(local_moment.weekday())
        if opening_hours is None:
            return False
        return opening_hours[0] <= local_moment.time() < opening_hours[1]

    def next_open_slot(self, local_moment: datetime) -> datetime:
        """The earliest legal send time at or after *local_moment*.

        Args:
            local_moment: A naive datetime in the country's local time.

        Returns:
            *local_moment* itself when already legal, else the next window's opening time.
        """
        candidate = local_moment
        for _ in range(_MAXIMUM_CLOSED_DAYS):
            opening_hours = (
                None if self.is_public_holiday(candidate.date()) else _OPENING_HOURS.get(candidate.weekday())
            )
            if opening_hours is not None:
                opens_at = candidate.replace(
                    hour=opening_hours[0].hour, minute=opening_hours[0].minute, second=0, microsecond=0
                )
                closes_at = candidate.replace(
                    hour=opening_hours[1].hour, minute=opening_hours[1].minute, second=0, microsecond=0
                )
                if candidate < opens_at:
                    return opens_at
                if candidate < closes_at:
                    return candidate
            candidate = (candidate + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return candidate


france_send_window: SmsSendWindow = SmsSendWindow("FR")
