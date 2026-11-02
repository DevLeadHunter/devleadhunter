"""Public holidays: the days a prospect takes off, when no prospecting message reaches him.

A prospect is spared the holidays of the place he works: a Swiss prospect August 1st and not July 14th, a prospect
of a French overseas department, French in every other respect, the French holidays plus the days his department
adds to them. The legal SMS window and the email send policy read the same lists.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta


class PublicHolidays:
    """Public holidays per country and per French overseas department, the days no prospecting message leaves.

    Only the days observed in the whole country or department are listed: Swiss cantonal holidays (January 2nd,
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
    def french_overseas_department(cls, department_code: str, year: int) -> set[date]:
        """French public holidays plus the days a French overseas department adds to them, for *year*.

        Each department commemorates the abolition of slavery on its own day (decree n° 83-1003 of the 23rd of
        November 1983); Guadeloupe and Martinique also stop on July 21st, Victor Schœlcher's day. The days taken off
        by custom only (carnival, Good Friday) are no public holidays and are left out.

        Args:
            department_code: ISO 3166-1 alpha-2 code of the department (« MQ »), any case.
            year: The calendar year.

        Returns:
            The set of holiday dates, the French ones alone for any other code.
        """
        victor_schoelcher_day = date(year, 7, 21)
        own_holidays_by_department: dict[str, set[date]] = {
            "GP": {date(year, 5, 27), victor_schoelcher_day},
            "MQ": {date(year, 5, 22), victor_schoelcher_day},
            "GF": {date(year, 6, 10)},
            "RE": {date(year, 12, 20)},
            "YT": {date(year, 4, 27)},
        }
        return cls.france(year) | own_holidays_by_department.get(department_code.strip().upper(), set())

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
