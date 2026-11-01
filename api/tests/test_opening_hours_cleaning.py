"""
Tests for opening-hours cleaning: near a public holiday Google annotates the day ("samedi
(Assomption)") and adds an "hours may differ" disclaimer (sometimes as its own row), and two daily
ranges can be captured glued together. The cleaner strips the annotation and disclaimer, separates
the ranges, keeps only real weekday rows and puts them from Monday to Sunday.
"""

import pytest

from services.storyblok_service import storyblok_service
from services.templates import registry
from services.templates.site_content import _clean_opening_hours


def test_strips_holiday_annotation_disclaimer_and_splits_glued_ranges() -> None:
    rows = [
        {"day": "vendredi", "hours": "07:45–12:0014:00–18:00"},
        {"day": "samedi(Assomption)", "hours": "Fermé Les horaires peuvent être différents"},
        {"day": "dimanche", "hours": "Fermé"},
    ]
    assert _clean_opening_hours(rows) == [
        {"day": "vendredi", "hours": "07:45–12:00, 14:00–18:00"},
        {"day": "samedi", "hours": "Fermé"},
        {"day": "dimanche", "hours": "Fermé"},
    ]


def test_drops_rows_whose_day_is_not_a_real_weekday() -> None:
    rows = [
        {"day": "lundi", "hours": "08:00–19:00"},
        {"day": "Les horaires peuvent être différents", "hours": ""},
        {"day": "", "hours": "09:00–17:00"},
    ]
    assert [r["day"] for r in _clean_opening_hours(rows)] == ["lundi"]


def test_clean_hours_flow_through_the_generated_site() -> None:
    site = registry.build_site_content(
        template_id="barber",
        business_name="X",
        phone="0",
        email="x@y.fr",
        city="Tours",
        area="Tours",
        subtitle="",
        palette={"primary": "#000", "secondary": "#111", "accent": "#222"},
        enrichment={
            "opening_hours": [{"day": "samedi(Assomption)", "hours": "Fermé Les horaires peuvent être différents"}]
        },
    )
    assert site["openingHours"] == [{"day": "samedi", "hours": "Fermé"}]


def test_the_week_starts_on_monday_whatever_day_the_listing_was_read_on() -> None:
    rows = [
        {"day": "samedi", "hours": "Fermé"},
        {"day": "dimanche", "hours": "Fermé"},
        {"day": "Lundi", "hours": "08:00–12:00, 14:00–18:00"},
        {"day": "mardi", "hours": "08:00–12:00, 14:00–18:00"},
        {"day": "mercredi", "hours": "08:00–12:00, 14:00–18:00"},
        {"day": "jeudi", "hours": "08:00–12:00, 14:00–18:00"},
        {"day": "vendredi (Toussaint)", "hours": "Fermé"},
    ]

    assert [row["day"] for row in _clean_opening_hours(rows)] == [
        "Lundi",
        "mardi",
        "mercredi",
        "jeudi",
        "vendredi",
        "samedi",
        "dimanche",
    ]


def test_english_day_names_follow_the_same_week_order() -> None:
    rows = [
        {"day": "Sunday", "hours": "Closed"},
        {"day": "Saturday", "hours": "9 AM–12 PM"},
        {"day": "Monday", "hours": "8 AM–6 PM"},
    ]

    assert [row["day"] for row in _clean_opening_hours(rows)] == ["Monday", "Saturday", "Sunday"]


@pytest.mark.parametrize("template_id", sorted(registry.TEMPLATES_BY_ID))
def test_every_template_shows_the_hours_from_monday(template_id: str) -> None:
    site = storyblok_service.build_content_json(
        business_name="Garage Exemple",
        phone=None,
        email=None,
        city="Thuré",
        description=None,
        template_id=template_id,
        enrichment={
            "opening_hours": [
                {"day": "dimanche", "hours": "Fermé"},
                {"day": "samedi", "hours": "Fermé"},
                {"day": "lundi", "hours": "08:00–18:00"},
            ]
        },
    )

    assert [row["day"] for row in site["openingHours"]] == ["lundi", "samedi", "dimanche"]
