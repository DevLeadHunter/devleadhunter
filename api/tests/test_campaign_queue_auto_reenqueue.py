"""A prospect skipped at launch (no demo/video) joins the queue on its own once it becomes ready.

The send queue is built once, at launch: a prospect skipped then for lacking a demo site or a
prospection video gets no queue row and nothing reconsiders it. ``enqueue_ready_prospect`` — called
when the video becomes ready — re-applies the launch guards for that one prospect and appends a J1
send in each active campaign it belongs to, without touching already-decided sends or other prospects.
"""

import importlib
import pkgutil
from datetime import datetime
from types import SimpleNamespace

from sqlalchemy.orm import configure_mappers

import models as _models_pkg

# Instantiating a real EmailQueue ORM row triggers mapper configuration, so every model must be
# imported first for cross-model relationships to resolve.
for _module in pkgutil.iter_modules(_models_pkg.__path__):
    importlib.import_module(f"models.{_module.name}")
configure_mappers()

import services.campaign_queue_service as cqs  # noqa: E402
from services.campaign_queue_service import CampaignQueueService  # noqa: E402


class _Result:
    """Stand-in for a SQLAlchemy result exposing the accessors the service calls."""

    def __init__(self, *, scalar=None, scalar_one_or_none=None, all_rows=None):
        self._scalar = scalar
        self._scalar_one_or_none = scalar_one_or_none
        self._all = all_rows or []

    def scalar(self):
        return self._scalar

    def scalar_one_or_none(self):
        return self._scalar_one_or_none

    def scalars(self):
        return SimpleNamespace(all=lambda: self._all)


class _FakeDB:
    """Session stand-in: ``execute`` returns queued results in order; records adds and commit."""

    def __init__(self, results=None, template=None):
        self._results = list(results or [])
        self._template = template
        self.added: list[object] = []
        self.committed = False

    def execute(self, *args, **kwargs):
        return self._results.pop(0) if self._results else _Result()

    def get(self, model, ident):
        return self._template

    def add(self, row):
        self.added.append(row)

    def commit(self):
        self.committed = True


def _prospect(pid: int, email: str = "a@b.fr", dnc: bool = False):
    return SimpleNamespace(id=pid, email=email, do_not_contact=dnc, name=f"Prospect {pid}")


def _campaign(**overrides):
    base = {
        "id": 1,
        "channel": "email",
        "user_id": 7,
        "include_video": True,
        "template_id": 100,
        "ab_template_id_b": None,
        "prospects": [],
        "max_emails_per_day": None,
        "send_delay_minutes": 20,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_enqueue_ready_prospect_calls_single_per_active_campaign(monkeypatch):
    campaigns = [_campaign(id=1), _campaign(id=2)]
    db = _FakeDB(results=[_Result(all_rows=campaigns)])
    seen: list[tuple[int, int]] = []

    # Only campaign 1 "adds" a row, so the total added count must be 1.
    monkeypatch.setattr(
        cqs.CampaignQueueService,
        "_enqueue_single_ready_prospect",
        lambda self, campaign, prospect_id: seen.append((campaign.id, prospect_id)) or campaign.id == 1,
    )

    added = CampaignQueueService(db).enqueue_ready_prospect(prospect_id=99, user_id=7)

    assert seen == [(1, 99), (2, 99)]
    assert added == 1


def test_single_ready_prospect_skips_sms_campaign():
    # SMS campaigns are demo-driven at launch/resume — a ready video must not enqueue one.
    created = CampaignQueueService(_FakeDB())._enqueue_single_ready_prospect(_campaign(channel="sms"), 5)
    assert created is False


def test_single_ready_prospect_skips_when_already_queued():
    # An initial row of any status means the prospect was already decided for this campaign.
    db = _FakeDB(results=[_Result(scalar_one_or_none=123)])
    created = CampaignQueueService(db)._enqueue_single_ready_prospect(_campaign(prospects=[_prospect(5)]), 5)
    assert created is False
    assert db.added == []


def test_single_ready_prospect_enqueues_when_guard_passes(monkeypatch):
    prospect = _prospect(5)
    campaign = _campaign(prospects=[prospect])
    # 1st execute() → existing-row check (None), 2nd → latest pending slot (None).
    db = _FakeDB(
        results=[_Result(scalar_one_or_none=None), _Result(scalar=None)],
        template=SimpleNamespace(subject="", body_html="{lien_demo}"),
    )
    monkeypatch.setattr(cqs.CampaignQueueService, "_send_guard_skip", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        cqs.CampaignQueueService, "_schedule_slots", lambda self, c, count, now, latest: [datetime(2026, 1, 5, 9, 0)]
    )
    monkeypatch.setattr(cqs.unsubscribe_service, "is_unsubscribed", lambda db, email: False)

    created = CampaignQueueService(db)._enqueue_single_ready_prospect(campaign, 5)

    assert created is True
    assert len(db.added) == 1
    row = db.added[0]
    assert row.prospect_id == 5
    assert row.template_id == 100
    assert row.queue_type == "initial"
    assert row.status == "pending"
    assert row.ab_variant is None
    assert db.committed


def test_single_ready_prospect_uses_b_variant_at_odd_index(monkeypatch):
    # A/B split follows the prospect's position: index 1 → variant B → the B template.
    prospects = [_prospect(10), _prospect(11)]
    campaign = _campaign(prospects=prospects, ab_template_id_b=200)
    db = _FakeDB(
        results=[_Result(scalar_one_or_none=None), _Result(scalar=None)],
        template=SimpleNamespace(subject="", body_html="{lien_video}"),
    )
    monkeypatch.setattr(cqs.CampaignQueueService, "_send_guard_skip", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        cqs.CampaignQueueService, "_schedule_slots", lambda self, c, count, now, latest: [datetime(2026, 1, 5, 9, 0)]
    )
    monkeypatch.setattr(cqs.unsubscribe_service, "is_unsubscribed", lambda db, email: False)

    created = CampaignQueueService(db)._enqueue_single_ready_prospect(campaign, 11)

    assert created is True
    row = db.added[0]
    assert row.ab_variant == "B"
    assert row.template_id == 200


def test_single_ready_prospect_skips_when_guard_still_fails(monkeypatch):
    campaign = _campaign(prospects=[_prospect(5)])
    db = _FakeDB(
        results=[_Result(scalar_one_or_none=None)],
        template=SimpleNamespace(subject="", body_html="{lien_video}"),
    )
    monkeypatch.setattr(cqs.CampaignQueueService, "_send_guard_skip", lambda *args, **kwargs: "video")
    monkeypatch.setattr(cqs.unsubscribe_service, "is_unsubscribed", lambda db, email: False)

    created = CampaignQueueService(db)._enqueue_single_ready_prospect(campaign, 5)

    assert created is False
    assert db.added == []


def test_send_guard_skip_matrix(monkeypatch):
    service = CampaignQueueService(_FakeDB())
    monkeypatch.setattr(cqs.CampaignQueueService, "_demo_link_for_prospect", lambda self, pid, uid, v: "")
    # Demo template, no active demo → "demo".
    assert service._send_guard_skip(1, 7, None, uses_demo=True, uses_video=False, include_video=True) == "demo"

    monkeypatch.setattr(cqs.CampaignQueueService, "_demo_link_for_prospect", lambda self, pid, uid, v: "url")
    monkeypatch.setattr(cqs.CampaignQueueService, "_video_for_prospect", lambda self, pid, uid, v: ("", ""))
    # Video-only template, no ready video → "video".
    assert service._send_guard_skip(1, 7, None, uses_demo=False, uses_video=True, include_video=True) == "video"
    # Combo template (demo + video) never blocks on the video — it degrades to the demo link.
    assert service._send_guard_skip(1, 7, None, uses_demo=True, uses_video=True, include_video=True) is None
    # Video-only template with the campaign video toggle off → "video".
    assert service._send_guard_skip(1, 7, None, uses_demo=False, uses_video=True, include_video=False) == "video"
    # Plain template (no demo, no video) is always allowed.
    assert service._send_guard_skip(1, 7, None, uses_demo=False, uses_video=False, include_video=True) is None
