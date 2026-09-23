"""Tests for the cross-module contact lock."""

from datetime import datetime, timedelta
from types import SimpleNamespace

from services.contact_lock_service import (
    LOCK_DAYS,
    MODULE_AI_ASSISTANT,
    MODULE_WEBSITES,
    contact_lock_service,
)

_NOW = datetime(2026, 9, 23, 12, 0, 0)


def _prospect(module: str | None, at: datetime | None) -> SimpleNamespace:
    """A minimal prospect stub carrying only the lock columns the service reads."""
    return SimpleNamespace(contacted_by_module=module, contacted_by_module_at=at)


def test_unstamped_prospect_is_never_locked() -> None:
    prospect = _prospect(None, None)
    assert contact_lock_service.is_locked_for_module(prospect, MODULE_WEBSITES, _NOW) is False


def test_same_module_is_not_locked_by_its_own_stamp() -> None:
    """A module's own follow-ups must keep flowing."""
    prospect = _prospect(MODULE_AI_ASSISTANT, _NOW - timedelta(days=1))
    assert contact_lock_service.is_locked_for_module(prospect, MODULE_AI_ASSISTANT, _NOW) is False


def test_other_module_is_locked_inside_the_window() -> None:
    prospect = _prospect(MODULE_WEBSITES, _NOW - timedelta(days=LOCK_DAYS - 1))
    assert contact_lock_service.is_locked_for_module(prospect, MODULE_AI_ASSISTANT, _NOW) is True


def test_other_module_is_free_once_the_window_passes() -> None:
    prospect = _prospect(MODULE_WEBSITES, _NOW - timedelta(days=LOCK_DAYS + 1))
    assert contact_lock_service.is_locked_for_module(prospect, MODULE_AI_ASSISTANT, _NOW) is False


def test_record_contact_stamps_module_and_time() -> None:
    prospect = _prospect(None, None)
    contact_lock_service.record_contact(prospect, MODULE_AI_ASSISTANT, _NOW)
    assert prospect.contacted_by_module == MODULE_AI_ASSISTANT
    assert prospect.contacted_by_module_at == _NOW


def test_locked_until_is_the_future_lift_time_or_none() -> None:
    active = _prospect(MODULE_WEBSITES, _NOW - timedelta(days=1))
    assert contact_lock_service.locked_until(active, _NOW) == _NOW - timedelta(days=1) + timedelta(days=LOCK_DAYS)

    expired = _prospect(MODULE_WEBSITES, _NOW - timedelta(days=LOCK_DAYS + 1))
    assert contact_lock_service.locked_until(expired, _NOW) is None

    assert contact_lock_service.locked_until(_prospect(None, None), _NOW) is None


def test_module_label_is_human_readable() -> None:
    assert contact_lock_service.module_label(MODULE_WEBSITES) == "Sites web"
    assert contact_lock_service.module_label(MODULE_AI_ASSISTANT) == "Assistant IA"
    assert contact_lock_service.module_label(None) == ""
