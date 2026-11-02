"""The public holidays a prospect takes off: his country's, or his French overseas department's.

The SMS window and the email send policy read the same lists. An overseas department adds its own days to the French
ones (the abolition of slavery, and Victor Schœlcher's day in Guadeloupe and Martinique); a prospect's calendar reads
his department from his address, else his country.
"""

from datetime import date
from types import SimpleNamespace

from services.french_overseas import FrenchOverseas
from services.prospect_calendar import ProspectCalendar
from services.public_holidays import PublicHolidays


def _prospect(*, country: str, address: str | None) -> SimpleNamespace:
    """A prospect as the queue reads it."""
    return SimpleNamespace(country=country, address=address, phones=[], phone=None)


class TestPublicHolidays:
    def test_easter_based_days_2026(self) -> None:
        assert PublicHolidays.easter_sunday(2026) == date(2026, 4, 5)
        assert date(2026, 4, 6) in PublicHolidays.france(2026)  # Lundi de Pâques
        assert date(2026, 5, 14) in PublicHolidays.france(2026)  # Ascension
        assert date(2026, 4, 3) in PublicHolidays.switzerland(2026)  # Vendredi saint
        assert date(2026, 5, 25) in PublicHolidays.switzerland(2026)  # Lundi de Pentecôte

    def test_the_country_dispatch_defaults_to_france(self) -> None:
        assert PublicHolidays.for_country("CH", 2026) == PublicHolidays.switzerland(2026)
        assert PublicHolidays.for_country("BE", 2026) == PublicHolidays.france(2026)
        assert PublicHolidays.for_country(None, 2026) == PublicHolidays.france(2026)

    def test_martinique_takes_the_french_holidays_off_and_its_own_two_days(self) -> None:
        martinique = PublicHolidays.french_overseas_department("mq", 2026)

        assert martinique - PublicHolidays.france(2026) == {date(2026, 5, 22), date(2026, 7, 21)}
        assert date(2026, 11, 11) in martinique

    def test_every_overseas_department_commemorates_the_abolition_of_slavery_on_its_own_day(self) -> None:
        own_holidays = {
            department.code: PublicHolidays.french_overseas_department(department.code, 2026)
            - PublicHolidays.france(2026)
            for department in FrenchOverseas.DEPARTMENTS
        }

        assert own_holidays == {
            "GP": {date(2026, 5, 27), date(2026, 7, 21)},
            "MQ": {date(2026, 5, 22), date(2026, 7, 21)},
            "GF": {date(2026, 6, 10)},
            "RE": {date(2026, 12, 20)},
            "YT": {date(2026, 4, 27)},
        }

    def test_a_code_of_no_overseas_department_reads_the_french_holidays(self) -> None:
        assert PublicHolidays.french_overseas_department("CH", 2026) == PublicHolidays.france(2026)


class TestProspectCalendar:
    def test_a_martinique_prospect_reads_fort_de_france_clock_and_the_martinique_holidays(self) -> None:
        calendar = ProspectCalendar.of_prospect(
            _prospect(country="FR", address="Zi la Lézarde, Le Lamentin 97232, Martinique")
        )

        assert calendar == ProspectCalendar(timezone_name="America/Martinique", country="FR", region="MQ")
        assert calendar.is_public_holiday(date(2026, 11, 11))
        assert calendar.is_public_holiday(date(2026, 5, 22))

    def test_a_mainland_prospect_takes_november_11th_off_but_not_may_22nd(self) -> None:
        calendar = ProspectCalendar.of_prospect(_prospect(country="FR", address="12 Rue Nationale, 41000 Blois"))

        assert calendar == ProspectCalendar(timezone_name="Europe/Paris", country="FR")
        assert calendar.is_public_holiday(date(2026, 11, 11))
        assert not calendar.is_public_holiday(date(2026, 5, 22))

    def test_a_swiss_prospect_works_on_november_11th_and_takes_august_1st_off(self) -> None:
        calendar = ProspectCalendar.of_prospect(_prospect(country="CH", address="Rue du Rhône 12, 1204 Genève"))

        assert calendar == ProspectCalendar(timezone_name="Europe/Zurich", country="CH")
        assert not calendar.is_public_holiday(date(2026, 11, 11))
        assert calendar.is_public_holiday(date(2025, 8, 1))

    def test_a_prospect_placed_nowhere_reads_the_french_calendar(self) -> None:
        french = ProspectCalendar(timezone_name="Europe/Paris", country="FR")

        assert ProspectCalendar.of_prospect(None) == french
        assert ProspectCalendar.of_prospect(_prospect(country="ZZ", address=None)) == french
