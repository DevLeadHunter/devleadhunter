"""Unit tests for the OVH order tracking of a sale's go-live (status sync + wording)."""

import asyncio
from types import SimpleNamespace

from services.domain.ovh_provider import ovh_domain_provider
from services.notification_service import notification_service
from services.order_service import OVH_STATUS_LABELS, order_service


def _order(**overrides) -> SimpleNamespace:
    base = {
        "id": 42,
        "user_id": 1,
        "domain": "mayer-paysagiste-angers.fr",
        "business_name": "Mayer Paysagiste",
        "ovh_order_id": 258872913,
        "ovh_order_status": None,
        "fulfillment_attempts": 5,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _sync(monkeypatch, order: SimpleNamespace, ovh_status: str | None) -> list[dict]:
    """Run one status sync against a stubbed OVH + notifier; return the pushes sent."""
    pushes: list[dict] = []

    async def fake_status(order_id: int) -> str | None:
        assert order_id == order.ovh_order_id
        return ovh_status

    async def fake_notify(**kwargs) -> None:
        pushes.append(kwargs)

    monkeypatch.setattr(ovh_domain_provider, "order_status", fake_status)
    monkeypatch.setattr(notification_service, "notify_go_live_step", fake_notify)
    monkeypatch.setattr("services.order_service.activity_log_service", SimpleNamespace(record=lambda **_: None))
    db = SimpleNamespace(commit=lambda: None)
    asyncio.run(order_service._sync_ovh_order_status(db, order))
    return pushes


class TestSyncOvhOrderStatus:
    def test_pending_status_resets_the_retry_budget_and_notifies_once(self, monkeypatch) -> None:
        order = _order()
        pushes = _sync(monkeypatch, order, "checking")
        # Waiting on OVH is not a fulfilment failure: the recovery loop keeps retrying.
        assert order.fulfillment_attempts == 0
        assert order.ovh_order_status == "checking"
        assert len(pushes) == 1
        assert OVH_STATUS_LABELS["checking"] in pushes[0]["body"]

    def test_unchanged_status_does_not_re_notify(self, monkeypatch) -> None:
        order = _order(ovh_order_status="checking")
        assert _sync(monkeypatch, order, "checking") == []

    def test_delivered_transition_pushes_a_success(self, monkeypatch) -> None:
        order = _order(ovh_order_status="delivering", fulfillment_attempts=3)
        pushes = _sync(monkeypatch, order, "delivered")
        assert order.ovh_order_status == "delivered"
        # Delivered is not a pending status: the budget is left alone.
        assert order.fulfillment_attempts == 3
        assert pushes[0]["level"] == "success"

    def test_not_paid_pushes_a_warning(self, monkeypatch) -> None:
        pushes = _sync(monkeypatch, _order(), "notPaid")
        assert pushes[0]["level"] == "warning"

    def test_without_a_tracked_order_nothing_happens(self, monkeypatch) -> None:
        order = _order(ovh_order_id=None)
        assert _sync(monkeypatch, order, "checking") == []
        assert order.ovh_order_status is None

    def test_terminal_delivered_status_is_never_re_read(self, monkeypatch) -> None:
        order = _order(ovh_order_status="delivered")
        assert _sync(monkeypatch, order, "checking") == []
        assert order.ovh_order_status == "delivered"


class TestVerifyDeliveryWording:
    def test_names_the_ovh_step_while_the_registrar_processes(self, monkeypatch) -> None:
        from services.demo_site_verification_service import demo_site_verification_service

        async def fake_check(domain: str) -> bool:
            return False

        monkeypatch.setattr(demo_site_verification_service, "check_domain_live", fake_check)
        order = _order(ovh_order_status="checking")
        site = SimpleNamespace(storyblok_space_id=1, storyblok_invite_sent=False)
        delivered, message = asyncio.run(order_service._verify_delivery(order, site))
        assert delivered is False
        assert OVH_STATUS_LABELS["checking"] in message

    def test_falls_back_to_the_dns_wording_once_delivered(self, monkeypatch) -> None:
        from services.demo_site_verification_service import demo_site_verification_service

        async def fake_check(domain: str) -> bool:
            return False

        monkeypatch.setattr(demo_site_verification_service, "check_domain_live", fake_check)
        order = _order(ovh_order_status="delivered")
        site = SimpleNamespace(storyblok_space_id=1, storyblok_invite_sent=False)
        delivered, message = asyncio.run(order_service._verify_delivery(order, site))
        assert delivered is False
        assert "DNS/Vercel" in message
