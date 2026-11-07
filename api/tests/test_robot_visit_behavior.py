"""A robot's session on a demo heats no lead: the hot leads, the prospect list's temperatures and the prospect
drawer read only the sessions people made, and the drawer shows a robot's session as one line.

The robot replays the hotmail link scanner that ran perrierelec's demo on 06/11, 24 s after the prospect himself:
an American clock in English, which clicked through the page and opened the contact form.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import pytest
from sqlalchemy.orm import Session

import services.behavior_service as behavior_module
from models.demo_site import DemoSite
from models.prospect_db import ProspectDB
from services.behavior_service import behavior_service
from services.posthog_service import DemoSession

USER_ID = 7
OPENED_AT = datetime(2026, 11, 6, 14, 24, 8)
SCANNED_AT = datetime(2026, 11, 6, 14, 24, 33)


def _prospect_with_demo(db: Session, name: str, slug: str) -> ProspectDB:
    prospect = ProspectDB(
        name=name, category="Électricien", source="google", confidence=2, user_id=USER_ID, country="FR"
    )
    db.add(prospect)
    db.flush()
    db.add(
        DemoSite(
            user_id=USER_ID,
            prospect_id=prospect.id,
            slug=slug,
            business_name=name,
            status="active",
            expires_at=OPENED_AT + timedelta(days=21),
        )
    )
    db.commit()
    return prospect


def _prospect_session(slug: str) -> DemoSession:
    return DemoSession(
        slug=slug,
        session_id=f"{slug}-prospect",
        started_at=OPENED_AT,
        device_type="Desktop",
        city="Nancy",
        interaction_count=25,
        time_on_page_seconds=39.0,
        engaged_seconds=20.0,
        timezone_name="Europe/Paris",
        language="fr",
        pageview_count=1,
        engaged_count=1,
        cta_click_count=8,
        last_event_at=OPENED_AT + timedelta(seconds=102),
    )


def _scanner_session(slug: str) -> DemoSession:
    return DemoSession(
        slug=slug,
        session_id=f"{slug}-scanner",
        started_at=SCANNED_AT,
        device_type="Desktop",
        city=None,
        interaction_count=10,
        time_on_page_seconds=25.0,
        engaged_seconds=20.0,
        timezone_name="America/Los_Angeles",
        language="en-US",
        pageview_count=1,
        engaged_count=1,
        cta_click_count=1,
        phone_click_count=1,
        last_event_at=SCANNED_AT + timedelta(minutes=5),
    )


def _event(name: str, timestamp: str, session_id: str) -> dict[str, Any]:
    return {"event": name, "timestamp": timestamp, "properties": {"$session_id": session_id}}


@pytest.fixture
def posthog_sessions(monkeypatch: pytest.MonkeyPatch) -> list[DemoSession]:
    sessions: list[DemoSession] = []

    async def read_sessions(slugs: list[str], since: datetime | None = None) -> list[DemoSession]:
        return [session for session in sessions if session.slug in slugs]

    monkeypatch.setattr(behavior_module.posthog_service, "get_demo_sessions", read_sessions)
    return sessions


@pytest.fixture
def perrierelec_events(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    events = [
        _event("demo_cta_banner_abandoned", "2026-11-06T14:25:01Z", "perrierelec-scanner"),
        _event("demo_cta_banner_open", "2026-11-06T14:25:00Z", "perrierelec-scanner"),
        _event("demo_phone_click", "2026-11-06T14:24:50Z", "perrierelec-scanner"),
        _event("$pageview", "2026-11-06T14:24:33Z", "perrierelec-scanner"),
        _event("demo_cta_click", "2026-11-06T14:24:30Z", "perrierelec-prospect"),
        _event("$pageview", "2026-11-06T14:24:08Z", "perrierelec-prospect"),
    ]

    async def read_events(slug: str, *, limit: int = 300) -> list[dict[str, Any]]:
        return list(events) if slug == "perrierelec" else []

    monkeypatch.setattr(behavior_module.posthog_service, "get_events_for_slug", read_events)
    return events


def test_the_hot_leads_and_the_temperatures_read_only_the_prospects_visits(
    db: Session, posthog_sessions: list[DemoSession]
) -> None:
    perrier = _prospect_with_demo(db, "Perrier Élec", "perrierelec")
    scanned_only = _prospect_with_demo(db, "Électro Contrôle", "electro-controle")
    posthog_sessions.extend(
        [_prospect_session("perrierelec"), _scanner_session("perrierelec"), _scanner_session("electro-controle")]
    )

    hot_leads = asyncio.run(behavior_service.get_hot_leads(db, USER_ID))
    temperatures = asyncio.run(behavior_service.get_temperatures(db, USER_ID, [perrier.id, scanned_only.id]))

    assert [lead["prospect_id"] for lead in hot_leads] == [perrier.id]
    signals = hot_leads[0]["signals"]
    assert (signals["visits"], signals["pageviews"], signals["cta_clicks"], signals["phone_clicks"]) == (1, 1, 8, 0)
    assert hot_leads[0]["last_seen"] == "2026-11-06T14:25:50"
    assert temperatures[scanned_only.id]["temperature"] == "unknown"
    assert temperatures[perrier.id]["temperature"] != "unknown"


def test_the_drawer_shows_the_scanner_as_one_line_and_scores_the_prospect_alone(
    db: Session, posthog_sessions: list[DemoSession], perrierelec_events: list[dict[str, Any]]
) -> None:
    perrier = _prospect_with_demo(db, "Perrier Élec", "perrierelec")
    posthog_sessions.extend([_prospect_session("perrierelec"), _scanner_session("perrierelec")])

    behavior = asyncio.run(behavior_service.get_behavior(db, USER_ID, perrier.id))

    assert [entry["label"] for entry in behavior["timeline"]] == [
        "Visite d'un robot, ignorée",
        "Clic sur un bouton d'action",
        "Visite de la démo",
    ]
    assert (behavior["signals"]["visits"], behavior["signals"]["phone_clicks"]) == (1, 0)
    assert behavior["has_data"]


def test_an_unreadable_posthog_keeps_every_event_in_the_drawer(
    db: Session, perrierelec_events: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """In doubt, the visit is kept: without the sessions to judge, no event is taken for a robot's."""
    perrier = _prospect_with_demo(db, "Perrier Élec", "perrierelec")

    async def unreadable_sessions(slugs: list[str], since: datetime | None = None) -> None:
        return None

    monkeypatch.setattr(behavior_module.posthog_service, "get_demo_sessions", unreadable_sessions)

    behavior = asyncio.run(behavior_service.get_behavior(db, USER_ID, perrier.id))

    assert len(behavior["timeline"]) == len(perrierelec_events)
    assert behavior["signals"]["phone_clicks"] == 1
