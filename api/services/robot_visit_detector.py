"""
Tells a robot's visit of a demo from a prospect's.

Mail and SMS link scanners open the links they carry in a real browser that runs the page, scrolls it and
even clicks it: their visit looks engaged. Their browser still gives them away. Either it declares itself
driven by automation, or its clock and its language both point away from the prospect: an American clock
in English on a Nancy electrician's demo, 9 hours from his own.

A prospect who reads in French, or on a clock less than three hours from his own (anywhere in Europe, the
Maghreb or the Near East for a French one), is never taken for a robot: in doubt, the visit is kept. So a
scanner on an American east-coast clock stays counted on a Martinique or Québec demo, whose clocks are that close.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

if TYPE_CHECKING:
    from services.posthog_service import DemoSession

_FAR_CLOCK_GAP = timedelta(hours=3)
_FRENCH_LANGUAGE_CODE = "fr"


@dataclass(frozen=True)
class VisitorBrowser:
    """
    What a visitor's browser tells of itself.

    Attributes:
        timezone_name: IANA zone of its clock (``America/Los_Angeles``), None when unknown.
        language: Its first language (``en-US``), None when unknown.
        is_automated: It declares itself driven by automation (``navigator.webdriver``).
    """

    timezone_name: str | None
    language: str | None
    is_automated: bool = False


class RobotVisitDetector:
    """Judges whether a demo visit comes from a robot, from what the visitor's browser tells of itself."""

    @staticmethod
    def is_robot_browser(browser: VisitorBrowser, prospect_timezone_name: str, at: datetime) -> bool:
        """
        Whether a browser is a robot's rather than the prospect's.

        Args:
            browser: What the visitor's browser tells of itself.
            prospect_timezone_name: IANA zone of the prospect's clock.
            at: Moment of the visit, naive UTC: clocks that change hour in summer are compared on that day.

        Returns:
            True for an automated browser, or for one whose clock is three hours or more from the prospect's
            while its language is not French; False whenever the clock or the language is unknown.
        """
        if browser.is_automated:
            return True
        return RobotVisitDetector._is_foreign_language(browser.language) and RobotVisitDetector._is_far_clock(
            browser.timezone_name, prospect_timezone_name, at
        )

    @staticmethod
    def is_human_session(session: DemoSession, prospect_timezone_name: str) -> bool:
        """
        Tell a person's visit from a robot's, on a session read back from PostHog.

        Two robots are told apart. A mail scanner's prefetch loads the page once, from a data centre: a
        desktop or unknown device, no city, and nothing but page views. A scanner that runs the page is
        betrayed by its browser's clock and language. A person scrolls, reads a section or stays long
        enough to send a time event, wherever they are.

        Args:
            session: The session to judge.
            prospect_timezone_name: IANA zone of the clock of the prospect whose demo it browsed.

        Returns:
            False only for a session that looks like a robot's.
        """
        looks_like_datacenter = session.city is None and session.device_type in (None, "Desktop")
        if looks_like_datacenter and session.interaction_count == 0:
            return False
        browser = VisitorBrowser(timezone_name=session.timezone_name, language=session.language)
        return not RobotVisitDetector.is_robot_browser(browser, prospect_timezone_name, session.started_at)

    @staticmethod
    def _is_foreign_language(language: str | None) -> bool:
        """Whether a browser language is known and is not French, whatever its region (``fr-CH``, ``fr_CA``)."""
        normalized_language = (language or "").strip().lower().replace("_", "-")
        if not normalized_language:
            return False
        language_code = normalized_language.split("-")[0]
        return language_code != _FRENCH_LANGUAGE_CODE

    @staticmethod
    def _is_far_clock(browser_timezone_name: str | None, prospect_timezone_name: str, at: datetime) -> bool:
        """Whether two clocks are 3 hours or more apart, by offset: Windows names some zones after a neighbour."""
        browser_zone = RobotVisitDetector._load_zone(browser_timezone_name)
        prospect_zone = RobotVisitDetector._load_zone(prospect_timezone_name)
        if browser_zone is None or prospect_zone is None:
            return False
        moment = at.replace(tzinfo=UTC) if at.tzinfo is None else at
        browser_offset = moment.astimezone(browser_zone).utcoffset()
        prospect_offset = moment.astimezone(prospect_zone).utcoffset()
        if browser_offset is None or prospect_offset is None:
            return False
        return abs(browser_offset - prospect_offset) >= _FAR_CLOCK_GAP

    @staticmethod
    def _load_zone(timezone_name: str | None) -> ZoneInfo | None:
        """The zone a name designates, None when the name is missing, unknown, or not a zone at all (« America »)."""
        if not timezone_name:
            return None
        try:
            return ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, ValueError, OSError):
            return None
