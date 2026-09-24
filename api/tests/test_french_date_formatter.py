"""Tests for the locale-independent French date formatter."""

from datetime import datetime

from services.french_date_formatter import FrenchDateFormatter


def test_day_month_renders_french_month_name() -> None:
    """The short form is the day followed by the French month name."""
    assert FrenchDateFormatter.day_month(datetime(2026, 10, 12)) == "12 octobre"
    assert FrenchDateFormatter.day_month(datetime(2026, 8, 1)) == "1 août"


def test_long_date_renders_weekday_day_month_year() -> None:
    """The long form starts with the French weekday and ends with the year."""
    assert FrenchDateFormatter.long_date(datetime(2026, 9, 24)) == "jeudi 24 septembre 2026"
    assert FrenchDateFormatter.long_date(datetime(2026, 12, 27)) == "dimanche 27 décembre 2026"
