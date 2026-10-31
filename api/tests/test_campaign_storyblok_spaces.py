"""The Storyblok spaces of a campaign, released together without taking one from a prospect who may still buy (31 Oct 2026).

The campaign page lists which spaces a release takes (a prospect who stayed silent or refused, once the demo has gone
out and its video is made) and which stay, each with its reason: a prospect who looked at the demo, answered, was
invited, or whose visits cannot be read keeps their space.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import services.campaign_storyblok_spaces_service as spaces_module
from api.v1.routes.campaigns import router as campaigns_router
from core.database import get_db
from enums.demo_site_status import DemoSiteStatus
from models.campaign import Campaign, CampaignStatus
from models.demo_site import DemoSite
from models.email_template import EmailTemplate
from models.prospect_db import ProspectDB
from services.auth_service import get_current_user
from services.campaign_storyblok_spaces_service import (
    STORYBLOK_SPACE_LIMIT,
    TRACKING_UNAVAILABLE_REASON,
    CampaignStoryblokSpacesService,
)
from services.storyblok_service import StoryblokService

_USER_ID = 7
_OTHER_USER_ID = 8
_NOW = datetime.now(UTC)


class _Results:
    """What the campaign's results answer: the state of each prospect, and whether the visits could be read."""

    def __init__(self) -> None:
        self.states: dict[str, str] = {}
        self.is_visit_tracking_available: bool = True
        self.is_missing: bool = False
        self.calls: int = 0
        self.account_spaces: int | None = 123
        self.names_by_prospect_id: dict[int, str] = {}


@pytest.fixture
def results() -> Iterator[_Results]:
    """The campaign results and the account's space count, answered by the test (``patch.object`` leaves no trace)."""
    answers = _Results()
    names_by_prospect_id = answers.names_by_prospect_id

    async def build(_db: Session, _user_id: int, _campaign_id: int) -> Any:
        answers.calls += 1
        if answers.is_missing:
            return None
        prospects = [
            SimpleNamespace(id=prospect_id, state=answers.states[name])
            for prospect_id, name in names_by_prospect_id.items()
            if name in answers.states
        ]
        return SimpleNamespace(prospects=prospects, is_visit_tracking_available=answers.is_visit_tracking_available)

    async def count_spaces() -> int | None:
        return answers.account_spaces

    with ExitStack() as patches:
        patches.enter_context(patch.object(spaces_module.campaign_results_service, "build", build))
        patches.enter_context(patch.object(spaces_module.storyblok_service, "count_spaces", count_spaces))
        yield answers


def _campaign(db: Session, user_id: int = _USER_ID) -> Campaign:
    template = EmailTemplate(user_id=user_id, name="Votre site", subject="Pour vous", body_html="<p>{lien_demo}</p>")
    db.add(template)
    db.flush()
    campaign = Campaign(
        user_id=user_id, name="Vague 4", status=CampaignStatus.COMPLETED, channel="email", template_id=template.id
    )
    db.add(campaign)
    db.commit()
    return campaign


def _prospect_with_site(
    db: Session, campaign: Campaign, answers: _Results, name: str, state: str, **site_overrides: object
) -> DemoSite:
    """A prospect of the campaign in ``state``, whose demo went out two days ago with its video made."""
    prospect = ProspectDB(name=name, category="garage", source="google", confidence=2, user_id=campaign.user_id)
    db.add(prospect)
    db.flush()
    campaign.prospects.append(prospect)
    answers.names_by_prospect_id[prospect.id] = name
    answers.states[name] = state
    fields: dict[str, Any] = {
        "user_id": campaign.user_id,
        "prospect_id": prospect.id,
        "slug": name.lower().replace(" ", "-"),
        "business_name": name,
        "template_id": "mechanic-pitlane",
        "status": DemoSiteStatus.ACTIVE.value,
        "demo_url": f"https://demo.example.com/{name.lower().replace(' ', '-')}",
        "storyblok_space_id": 295000000000000 + prospect.id,
        "storyblok_invite_sent": False,
        "content_json": {"businessName": name},
        "video_status": "ready",
        "video_generated_at": _NOW - timedelta(days=3),
        "demo_link_sent_at": _NOW - timedelta(days=2),
        "expires_at": _NOW + timedelta(days=19),
    }
    fields.update(site_overrides)
    site = DemoSite(**fields)
    db.add(site)
    db.commit()
    return site


def _summarize(db: Session, campaign: Campaign) -> Any:
    return asyncio.run(CampaignStoryblokSpacesService.summarize(db, campaign))


def test_only_the_prospects_who_stayed_silent_or_refused_have_their_space_released(
    db: Session, results: _Results
) -> None:
    campaign = _campaign(db)
    _prospect_with_site(db, campaign, results, "Garage Silencieux", "silent")
    _prospect_with_site(db, campaign, results, "Garage Refus", "refused")
    _prospect_with_site(db, campaign, results, "Garage Curieux", "visited")
    _prospect_with_site(db, campaign, results, "Garage Question", "replied")
    _prospect_with_site(db, campaign, results, "Garage Intéressé", "interested")
    _prospect_with_site(db, campaign, results, "Garage Acheteur", "sold")
    _prospect_with_site(db, campaign, results, "Garage Attente", "pending")

    summary = _summarize(db, campaign)

    assert [site.business_name for site in summary.releasable] == ["Garage Silencieux", "Garage Refus"]
    assert {site.business_name: site.reason for site in summary.kept} == {
        "Garage Curieux": "A regardé sa démo.",
        "Garage Question": "A répondu.",
        "Garage Intéressé": "S'est dit intéressé.",
        "Garage Acheteur": "A acheté.",
        "Garage Attente": "Pas encore contacté.",
    }


def test_the_conditions_of_the_demo_itself_keep_a_silent_prospects_space(db: Session, results: _Results) -> None:
    campaign = _campaign(db)
    _prospect_with_site(db, campaign, results, "Garage Invite", "silent", storyblok_invite_sent=True)
    _prospect_with_site(db, campaign, results, "Garage Dedans", "silent", storyblok_collaborator_status="joined")
    _prospect_with_site(db, campaign, results, "Garage Sans Video", "silent", video_status=None)
    _prospect_with_site(db, campaign, results, "Garage Pas Envoye", "silent", demo_link_sent_at=None)

    summary = _summarize(db, campaign)

    assert summary.releasable == []
    assert {site.business_name: site.reason for site in summary.kept} == {
        "Garage Invite": "Le client a été invité dans l'espace : on le garde.",
        "Garage Dedans": "Le client a rejoint l'espace : on le garde.",
        "Garage Sans Video": "La vidéo n'est pas encore générée : l'espace sert à la filmer.",
        "Garage Pas Envoye": "Le lien de la démo n'a pas encore été envoyé : on garde l'espace.",
    }


def test_nothing_is_released_when_the_visits_cannot_be_read(db: Session, results: _Results) -> None:
    results.is_visit_tracking_available = False
    campaign = _campaign(db)
    _prospect_with_site(db, campaign, results, "Garage Silencieux", "silent")

    summary = _summarize(db, campaign)

    assert summary.releasable == []
    assert [site.reason for site in summary.kept] == [TRACKING_UNAVAILABLE_REASON]


def test_nothing_is_released_when_the_campaign_has_no_results(db: Session, results: _Results) -> None:
    results.is_missing = True
    campaign = _campaign(db)
    _prospect_with_site(db, campaign, results, "Garage Silencieux", "silent")

    summary = _summarize(db, campaign)

    assert summary.releasable == []
    assert [site.reason for site in summary.kept] == [TRACKING_UNAVAILABLE_REASON]


def test_a_campaign_without_any_space_is_not_asked_for_its_results(db: Session, results: _Results) -> None:
    campaign = _campaign(db)
    _prospect_with_site(db, campaign, results, "Garage Sans Espace", "silent", storyblok_space_id=None)
    _prospect_with_site(db, campaign, results, "Garage Vendu", "sold", status=DemoSiteStatus.DELIVERED.value)

    summary = _summarize(db, campaign)

    assert summary.releasable == []
    assert summary.kept == []
    assert results.calls == 0


def test_the_account_count_and_the_cap_come_with_the_lists(db: Session, results: _Results) -> None:
    campaign = _campaign(db)

    summary = _summarize(db, campaign)

    assert summary.account_space_count == 123
    assert summary.account_space_limit == STORYBLOK_SPACE_LIMIT == 250


def test_the_account_count_is_left_out_when_storyblok_does_not_answer(db: Session, results: _Results) -> None:
    results.account_spaces = None

    summary = _summarize(db, _campaign(db))

    assert summary.account_space_count is None


def _client(db: Session) -> TestClient:
    application = FastAPI()
    application.include_router(campaigns_router)
    application.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=_USER_ID, email="o@x.com")
    application.dependency_overrides[get_db] = lambda: db
    return TestClient(application)


def test_the_route_answers_for_the_owners_campaign_and_not_for_another_users(db: Session, results: _Results) -> None:
    mine = _campaign(db)
    _prospect_with_site(db, mine, results, "Garage Silencieux", "silent")
    other_users = _campaign(db, user_id=_OTHER_USER_ID)

    answer = _client(db).get(f"{campaigns_router.prefix}/{mine.id}/storyblok-spaces")
    refused = _client(db).get(f"{campaigns_router.prefix}/{other_users.id}/storyblok-spaces")

    assert answer.status_code == 200
    assert [site["business_name"] for site in answer.json()["releasable"]] == ["Garage Silencieux"]
    assert answer.json()["kept"] == []
    assert answer.json()["account_space_limit"] == 250
    assert refused.status_code == 404


class _AccountAnswer:
    def __init__(self, spaces: int) -> None:
        self._spaces = spaces

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {"spaces": [{"id": index} for index in range(self._spaces)]}


class _AccountClient:
    async def __aenter__(self) -> _AccountClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None


def test_the_account_is_counted_once_every_five_minutes_and_a_failure_is_no_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = StoryblokService()
    asked: list[str] = []

    async def read_spaces(_client: object, _method: str, url: str, **_kwargs: object) -> _AccountAnswer:
        asked.append(url)
        if len(asked) == 3:
            raise RuntimeError("Storyblok is down")
        return _AccountAnswer(123)

    monkeypatch.setattr(StoryblokService, "is_configured", property(lambda self: True))
    monkeypatch.setattr("services.storyblok_service.httpx.AsyncClient", lambda **_kwargs: _AccountClient())
    monkeypatch.setattr(service, "_storyblok_request", read_spaces)

    assert asyncio.run(service.count_spaces()) == 123
    assert asyncio.run(service.count_spaces()) == 123
    assert len(asked) == 1
    assert asked[0].endswith("/spaces/")

    service._space_count_cache = None
    assert asyncio.run(service.count_spaces()) == 123
    service._space_count_cache = None
    assert asyncio.run(service.count_spaces()) is None


def test_an_unconfigured_storyblok_has_no_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(StoryblokService, "is_configured", property(lambda self: False))

    assert asyncio.run(StoryblokService().count_spaces()) is None
