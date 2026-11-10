"""A robot's visit of a demo pushes nothing and leaves the evening recap: its events only reach the activity feed.

The robot replays the hotmail link scanner that ran perrierelec's demo on 06/11, 24 s after the prospect himself:
an American clock in English, which opened the contact form and left it 236 ms later. Prospects keep notifying
as before, in France, in Martinique or in Switzerland, and a lead or typed words are never taken for a robot's.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.orm import Session

import services.notification_service as notification_module
from api.v1.routes.demo_events import ingest_demo_event
from models.demo_site import DemoSite
from models.prospect_db import ProspectDB
from models.push_subscription import PushSubscription
from schemas.notification import DemoEventIn
from services.notification_service import notification_service
from services.posthog_service import DemoSession
from services.robot_visit_detector import VisitorBrowser

USER_ID = 7
HOTMAIL_SCANNER = VisitorBrowser(timezone_name="America/Los_Angeles", language="en-US")
NOVEMBER_6 = datetime(2026, 11, 6)


@pytest.fixture
def pushes(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    pushed: list[dict[str, Any]] = []

    async def dispatch(**kwargs: Any) -> None:
        pushed.append(kwargs)

    monkeypatch.setattr(notification_service, "_dispatch", dispatch)
    return pushed


@pytest.fixture
def feed(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    monkeypatch.setattr(notification_module.activity_log_service, "record", lambda **kwargs: entries.append(kwargs))
    return entries


def _prospect(db: Session, name: str, *, country: str = "FR", address: str | None = None) -> ProspectDB:
    prospect = ProspectDB(
        name=name,
        category="Électricien",
        source="google",
        confidence=2,
        user_id=USER_ID,
        country=country,
        address=address,
    )
    db.add(prospect)
    db.commit()
    return prospect


def _demo_site(prospect: ProspectDB, slug: str) -> DemoSite:
    return DemoSite(
        user_id=USER_ID,
        prospect_id=prospect.id,
        slug=slug,
        business_name=prospect.name,
        status="active",
        expires_at=NOVEMBER_6 + timedelta(days=21),
    )


def _notify(db: Session, prospect: ProspectDB, event: str, browser: VisitorBrowser | None, **context: Any) -> None:
    asyncio.run(
        notification_service.notify_demo_event(
            db,
            user_id=USER_ID,
            prospect_id=prospect.id,
            event_name=event,
            fallback_name="perrierelec",
            browser=browser,
            **context,
        )
    )


def test_the_hotmail_scanner_pushes_nothing_but_leaves_a_trace(
    db: Session, pushes: list[dict[str, Any]], feed: list[dict[str, Any]]
) -> None:
    prospect = _prospect(db, "Perrier Élec")

    for event, context in (
        ("demo_opened", {}),
        ("demo_cta_banner_open", {}),
        ("demo_cta_banner_abandoned", {"seconds": 0}),
        ("demo_time_on_page", {"seconds": 23, "max_scroll": 0}),
        ("demo_returned", {}),
    ):
        _notify(db, prospect, event, HOTMAIL_SCANNER, channel="email", **context)

    assert pushes == []
    assert [entry["action"] for entry in feed] == ["robot_visit_ignored"] * 5
    assert feed[3]["title"] == "🤖 Robot ignoré · Perrier Élec · Visite : 23s · 0% lu · Email"
    assert feed[3]["detail"] == "demo_time_on_page · fuseau America/Los_Angeles · langue en-US"
    assert feed[0]["entity_id"] == prospect.id


@pytest.mark.parametrize(
    ("country", "address", "browser"),
    [
        pytest.param("FR", "Rue de la Commanderie, 54000 Nancy", VisitorBrowser("Europe/Paris", "fr"), id="nancy"),
        pytest.param(
            "FR",
            "Rue Victor Hugo, 97200 Fort-de-France",
            VisitorBrowser("America/Martinique", "fr-FR"),
            id="martinique",
        ),
        pytest.param("CH", "Route de Suisse 10, 1290 Versoix", VisitorBrowser("Europe/Zurich", "de-CH"), id="zurich"),
        pytest.param("FR", None, None, id="a-beacon-without-signals"),
    ],
)
def test_a_prospect_still_notifies(
    db: Session,
    pushes: list[dict[str, Any]],
    feed: list[dict[str, Any]],
    country: str,
    address: str | None,
    browser: VisitorBrowser | None,
) -> None:
    prospect = _prospect(db, "Perrier Élec", country=country, address=address)

    _notify(db, prospect, "demo_opened", browser)

    assert [push["body"] for push in pushes] == ["🌐 Site web · Vient d'ouvrir sa démo"]
    assert [entry["action"] for entry in feed] == ["demo_opened"]


def test_a_lead_or_typed_words_are_never_taken_for_a_robot(
    db: Session, pushes: list[dict[str, Any]], feed: list[dict[str, Any]]
) -> None:
    prospect = _prospect(db, "Perrier Élec")

    _notify(db, prospect, "demo_lead", HOTMAIL_SCANNER)
    _notify(db, prospect, "demo_cta_banner_abandoned", HOTMAIL_SCANNER, message="Combien pour le domaine ?")

    assert [push["title"] for push in pushes] == ["🙋 Perrier Élec", "🕓 Perrier Élec"]


def test_a_browser_driven_by_automation_pushes_nothing(
    db: Session, pushes: list[dict[str, Any]], feed: list[dict[str, Any]]
) -> None:
    prospect = _prospect(db, "Perrier Élec")

    _notify(db, prospect, "demo_opened", VisitorBrowser("Europe/Paris", "fr-FR", is_automated=True))

    assert pushes == []
    assert feed[0]["detail"] == "demo_opened · navigateur piloté par un automate"


def test_the_beacon_hands_its_browser_to_the_notification(
    db: Session, pushes: list[dict[str, Any]], feed: list[dict[str, Any]]
) -> None:
    prospect = _prospect(db, "Perrier Élec")
    db.add(_demo_site(prospect, "perrierelec"))
    db.commit()

    for timezone_name, language in (("America/Los_Angeles", "en-US"), ("Europe/Paris", "fr")):
        payload = DemoEventIn(
            demo_slug="perrierelec",
            event="demo_opened",
            channel="email",
            browser_timezone=timezone_name,
            browser_language=language,
        )
        asyncio.run(ingest_demo_event(payload, db))

    assert [push["body"] for push in pushes] == ["🌐 Site web · Vient d'ouvrir sa démo · Email"]


def test_the_evening_recap_leaves_the_robots_out(
    db: Session, monkeypatch: pytest.MonkeyPatch, pushes: list[dict[str, Any]]
) -> None:
    """06/11: Patrick Romang read his demo in Versoix, Perrier Élec in Nancy, then the scanner: 2 visits, 1 qualified."""
    perrier = _prospect(db, "Perrier Élec", address="Rue de la Commanderie, 54000 Nancy")
    romang = _prospect(db, "Électro Contrôle Patrick Romang", country="CH", address="Route de Suisse 10, 1290 Versoix")
    for prospect, slug in ((perrier, "perrierelec"), (romang, "electro-controle-patrick-romang")):
        db.add(_demo_site(prospect, slug))
    db.add(PushSubscription(user_id=USER_ID, endpoint="https://push.example/leo", p256dh="key", auth="auth"))
    db.commit()
    sessions = [
        DemoSession(
            "electro-controle-patrick-romang",
            "s1",
            NOVEMBER_6,
            "Mobile",
            "Versoix",
            4,
            None,
            None,
            "Europe/Zurich",
            "fr-CH",
            1,
            0,
        ),
        DemoSession("perrierelec", "s2", NOVEMBER_6, "Desktop", "Nancy", 25, 140.0, 20.0, "Europe/Paris", "fr", 1, 1),
        DemoSession(
            "perrierelec", "s3", NOVEMBER_6, "Desktop", None, 10, 25.0, 20.0, "America/Los_Angeles", "en-US", 1, 1
        ),
    ]

    async def read_sessions(slugs: list[str], since: datetime) -> list[DemoSession]:
        return [session for session in sessions if session.slug in slugs]

    monkeypatch.setattr(notification_module, "SessionLocal", lambda: db)
    monkeypatch.setattr(notification_module.posthog_service, "get_demo_sessions", read_sessions)

    asyncio.run(notification_service.send_daily_recap())

    assert len(pushes) == 1 and "2 visites (1 qualifiées)" in pushes[0]["body"]
