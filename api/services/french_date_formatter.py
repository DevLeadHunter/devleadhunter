"""Dates written in French words, whatever the server locale."""

from datetime import date, datetime


class FrenchDateFormatter:
    """Static French date formatting; names are hardcoded because the server locale is not French."""

    MONTHS: tuple[str, ...] = (
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    )
    WEEKDAYS: tuple[str, ...] = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")

    @staticmethod
    def day_month(moment: datetime) -> str:
        """The day and month of ``moment``, as "12 octobre"."""
        return f"{moment.day} {FrenchDateFormatter.MONTHS[moment.month - 1]}"

    @staticmethod
    def month_year(moment: date) -> str:
        """The month and year of ``moment``, as "septembre 2026"."""
        return f"{FrenchDateFormatter.MONTHS[moment.month - 1]} {moment.year}"

    @staticmethod
    def long_date(moment: datetime) -> str:
        """The weekday, day, month and year of ``moment``, as "jeudi 24 septembre 2026"."""
        return f"{FrenchDateFormatter.WEEKDAYS[moment.weekday()]} {FrenchDateFormatter.day_month(moment)} {moment.year}"
