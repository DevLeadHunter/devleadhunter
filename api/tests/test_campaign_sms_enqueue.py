"""SMS-channel campaigns reuse the email queue engine.

``enqueue_campaign`` routes SMS campaigns to ``_enqueue_sms``, which creates template-less queue rows
for reachable mobiles **in prospect order** (the explicit ``position`` order → 1 métier/jour), skipping
landlines and prospects without an active demo.
"""

import importlib
import pkgutil
from datetime import datetime
from types import SimpleNamespace

from sqlalchemy.orm import configure_mappers

import models as _models_pkg

# This test instantiates a real EmailQueue ORM row, which triggers mapper configuration — so every
# model must be imported first for cross-model relationships (User → PaymentAccount, …) to resolve.
for _module in pkgutil.iter_modules(_models_pkg.__path__):
    importlib.import_module(f"models.{_module.name}")
configure_mappers()

import services.campaign_queue_service as cqs  # noqa: E402
from services.campaign_queue_service import CampaignQueueService, EnqueueResult  # noqa: E402


class _Result:
    def __init__(self, scalar=None, all_rows=None):
        self._scalar = scalar
        self._all = all_rows or []

    def scalar(self):
        return self._scalar

    def all(self):
        return self._all


class _FakeDB:
    def __init__(self):
        self.added: list[object] = []
        self.committed = False

    def execute(self, *args, **kwargs):
        return _Result(scalar=None, all_rows=[])

    def add(self, row):
        self.added.append(row)

    def commit(self):
        self.committed = True


def _prospect(pid: int, phone: str, dnc: bool = False):
    return SimpleNamespace(
        id=pid,
        phone=phone,
        name=f"Prospect {pid}",
        do_not_contact=dnc,
        contacted_by_module=None,
        contacted_by_module_at=None,
    )


def test_enqueue_sms_creates_templateless_rows_in_order(monkeypatch):
    db = _FakeDB()
    svc = CampaignQueueService(db)

    monkeypatch.setattr(cqs.CampaignQueueService, "_purge_skipped_initial_items", lambda self, cid: 0)
    monkeypatch.setattr(
        cqs.CampaignQueueService,
        "_schedule_slots",
        lambda self, campaign, count, now, latest: [datetime(2026, 1, 5, 9, 0)] * count,
    )
    # A demo exists for everyone except prospect 3.
    monkeypatch.setattr(
        cqs.CampaignQueueService,
        "_active_demo_for_prospect",
        lambda self, pid, uid: None if pid == 3 else SimpleNamespace(id=99, slug="s"),
    )
    from services.sms_service import sms_service

    monkeypatch.setattr(sms_service, "is_suppressed", lambda db, uid, e164: False)

    prospects = [
        _prospect(10, "06 12 34 56 78"),  # mobile + demo → enqueued (1st)
        _prospect(20, "03 22 33 44 55"),  # landline → skipped (not a mobile)
        _prospect(3, "06 98 76 54 32"),  # mobile but NO demo → skipped_no_demo
        _prospect(40, "07 11 22 33 44"),  # mobile + demo → enqueued (2nd)
    ]
    campaign = SimpleNamespace(id=1, user_id=7, channel="sms", sms_template_key=None, prospects=prospects)

    result = svc._enqueue_sms(campaign)

    assert result.enqueued == 2
    # Order preserved (position order), non-mobile + no-demo dropped.
    assert [row.prospect_id for row in db.added] == [10, 40]
    assert all(row.template_id is None for row in db.added)
    assert all(row.ab_variant is None and row.queue_type == "initial" for row in db.added)
    assert [entry["id"] for entry in result.skipped_no_demo] == [3]
    assert db.committed


def test_enqueue_sms_assistant_campaign_needs_an_assistant_not_a_demo(monkeypatch):
    db = _FakeDB()
    svc = CampaignQueueService(db)

    monkeypatch.setattr(cqs.CampaignQueueService, "_purge_skipped_initial_items", lambda self, cid: 0)
    monkeypatch.setattr(
        cqs.CampaignQueueService,
        "_schedule_slots",
        lambda self, campaign, count, now, latest: [datetime(2026, 1, 5, 9, 0)] * count,
    )
    # Nobody has a demo site; everyone but prospect 3 has an active assistant.
    monkeypatch.setattr(cqs.CampaignQueueService, "_active_demo_for_prospect", lambda self, pid, uid: None)
    monkeypatch.setattr(cqs.CampaignQueueService, "_has_active_assistant", lambda self, pid, uid: pid != 3)
    from services.sms_service import sms_service

    monkeypatch.setattr(sms_service, "is_suppressed", lambda db, uid, e164: False)

    prospects = [_prospect(10, "06 12 34 56 78"), _prospect(3, "06 98 76 54 32")]
    campaign = SimpleNamespace(id=1, user_id=7, channel="sms", sms_template_key="assistant-24-7", prospects=prospects)

    result = svc._enqueue_sms(campaign)

    assert [row.prospect_id for row in db.added] == [10]
    assert [entry["id"] for entry in result.skipped_no_assistant] == [3]
    assert result.skipped_no_demo == []
    assert prospects[0].contacted_by_module == cqs.MODULE_AI_ASSISTANT  # the lock is stamped for the right module


def test_enqueue_campaign_routes_sms_channel(monkeypatch):
    seen: dict[str, int] = {}

    def _fake_enqueue_sms(self, campaign):
        seen["campaign_id"] = campaign.id
        return EnqueueResult()

    monkeypatch.setattr(cqs.CampaignQueueService, "_enqueue_sms", _fake_enqueue_sms)

    svc = CampaignQueueService(_FakeDB())
    svc.enqueue_campaign(SimpleNamespace(id=42, channel="sms"))

    assert seen["campaign_id"] == 42
