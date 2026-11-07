"""A demo visit is a robot's when its browser is automated, or when its clock and its language both point away
from the prospect; a prospect is never taken for one, wherever he reads his demo.

The robot cases are sessions replayed from PostHog: link scanners that ran a mailed or texted demo link from an
American data centre (the perrierelec one of 06/11 opened the contact form and left 236 ms later).
"""

from datetime import datetime

import pytest

from services.posthog_service import DemoSession
from services.robot_visit_detector import RobotVisitDetector, VisitorBrowser

PARIS = "Europe/Paris"
ZURICH = "Europe/Zurich"
MARTINIQUE = "America/Martinique"
NOVEMBER_6 = datetime(2026, 11, 6, 14, 24, 33)
JULY_1 = datetime(2026, 7, 1, 9, 0)


def _session(
    timezone_name: str | None, language: str | None, *, city: str | None = None, interactions: int = 10
) -> DemoSession:
    return DemoSession(
        slug="perrierelec",
        session_id="session",
        started_at=NOVEMBER_6,
        device_type="Desktop",
        city=city,
        interaction_count=interactions,
        time_on_page_seconds=25.0,
        engaged_seconds=20.0,
        timezone_name=timezone_name,
        language=language,
        pageview_count=1,
        engaged_count=1,
    )


@pytest.mark.parametrize(
    ("timezone_name", "language", "prospect_timezone_name", "at"),
    [
        pytest.param("America/Los_Angeles", "en-US", PARIS, NOVEMBER_6, id="perrierelec-hotmail-scanner"),
        pytest.param("America/New_York", "en-US", ZURICH, datetime(2026, 11, 5, 10, 42, 53), id="flo-jardinier"),
        pytest.param("America/Los_Angeles", "en-US", PARIS, datetime(2026, 10, 4, 21, 35), id="amsterdam-scanner"),
        pytest.param("America/Denver", "en-US", PARIS, datetime(2026, 10, 7, 11, 26), id="sms-link-scanner"),
        pytest.param("America/Chicago", "en-US", PARIS, datetime(2026, 10, 19, 9, 34), id="charleston-scanner"),
        pytest.param("America/Los_Angeles", "en-US", MARTINIQUE, NOVEMBER_6, id="west-coast-on-martinique"),
    ],
)
def test_the_link_scanners_replayed_from_posthog_are_robots(
    timezone_name: str, language: str, prospect_timezone_name: str, at: datetime
) -> None:
    browser = VisitorBrowser(timezone_name=timezone_name, language=language)

    assert RobotVisitDetector.is_robot_browser(browser, prospect_timezone_name, at)


@pytest.mark.parametrize(
    ("timezone_name", "language", "prospect_timezone_name"),
    [
        pytest.param(PARIS, "fr", PARIS, id="perrierelec-prospect-in-nancy"),
        pytest.param(MARTINIQUE, "fr-FR", MARTINIQUE, id="martinique-prospect"),
        pytest.param(ZURICH, "fr-CH", ZURICH, id="swiss-prospect"),
        pytest.param(ZURICH, "pt-PT", ZURICH, id="swiss-prospect-reading-in-portuguese"),
        pytest.param(ZURICH, "de-CH", ZURICH, id="swiss-german-prospect"),
        pytest.param("Europe/Berlin", "fr-FR", PARIS, id="windows-naming-a-tours-pc-after-berlin"),
        pytest.param("America/La_Paz", "en-US", MARTINIQUE, id="windows-naming-a-martinique-pc-after-la-paz"),
        pytest.param("Europe/Skopje", "fr-CH", ZURICH, id="swiss-prospect-on-holiday-in-macedonia"),
        pytest.param("America/New_York", "fr-FR", PARIS, id="french-prospect-in-new-york"),
        pytest.param("Europe/London", "en-GB", PARIS, id="english-browser-one-hour-away"),
        pytest.param(PARIS, "en-US", PARIS, id="english-browser-on-the-prospects-clock"),
    ],
)
def test_a_prospect_is_never_a_robot(timezone_name: str, language: str, prospect_timezone_name: str) -> None:
    browser = VisitorBrowser(timezone_name=timezone_name, language=language)

    assert not RobotVisitDetector.is_robot_browser(browser, prospect_timezone_name, NOVEMBER_6)
    assert not RobotVisitDetector.is_robot_browser(browser, prospect_timezone_name, JULY_1)


def test_a_browser_driven_by_automation_is_a_robot_even_on_the_prospects_clock() -> None:
    browser = VisitorBrowser(timezone_name=PARIS, language="fr-FR", is_automated=True)

    assert RobotVisitDetector.is_robot_browser(browser, PARIS, NOVEMBER_6)


@pytest.mark.parametrize(
    ("timezone_name", "language"),
    [
        pytest.param(None, "en-US", id="no-clock"),
        pytest.param("America/Los_Angeles", None, id="no-language"),
        pytest.param("America/Los_Angeles", "", id="empty-language"),
        pytest.param("America", "en-US", id="a-directory-not-a-zone"),
        pytest.param("Mars/Olympus_Mons", "en-US", id="unknown-zone"),
        pytest.param("../../etc/passwd", "en-US", id="a-path-not-a-zone"),
    ],
)
def test_an_unknown_signal_keeps_the_visit(timezone_name: str | None, language: str | None) -> None:
    browser = VisitorBrowser(timezone_name=timezone_name, language=language)

    assert not RobotVisitDetector.is_robot_browser(browser, PARIS, NOVEMBER_6)


def test_clocks_are_compared_on_the_day_of_the_visit() -> None:
    """Denver is three hours from Martinique in winter but two in summer, when it moves its clock and Martinique does not."""
    browser = VisitorBrowser(timezone_name="America/Denver", language="en-US")

    assert RobotVisitDetector.is_robot_browser(browser, MARTINIQUE, NOVEMBER_6)
    assert not RobotVisitDetector.is_robot_browser(browser, MARTINIQUE, JULY_1)


def test_a_scanner_prefetch_is_not_a_visit() -> None:
    scanner = DemoSession("garage", "s1", NOVEMBER_6, "Desktop", None, 0, None, None)
    reader_without_city = DemoSession("garage", "s2", NOVEMBER_6, "Mobile", None, 0, None, None)

    assert not RobotVisitDetector.is_human_session(scanner, PARIS)
    assert RobotVisitDetector.is_human_session(reader_without_city, PARIS)


def test_a_session_that_ran_the_page_is_judged_on_its_browser() -> None:
    """The perrierelec scanner scrolled and clicked: only its clock and its language tell it apart."""
    scanner = _session("America/Los_Angeles", "en-US")
    prospect = _session(PARIS, "fr", city="Nancy")

    assert not RobotVisitDetector.is_human_session(scanner, PARIS)
    assert RobotVisitDetector.is_human_session(prospect, PARIS)
    assert RobotVisitDetector.is_human_session(_session(None, None), PARIS)
