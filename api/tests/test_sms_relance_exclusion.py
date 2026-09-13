"""The per-prospect J+30 relance opt-out drops it from the relance selection only.

``sms_relance_excluded`` bars a prospect from the SMS relance (worker + forecast), while
a cold SMS — a different automation — stays allowed for the same prospect.
"""

from types import SimpleNamespace

from services.sms_relance_service import sms_relance_service
from services.sms_service import sms_service


def _prospect(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 7,
        "phone": "06 12 34 56 78",
        "do_not_contact": False,
        "sms_relance_excluded": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _allow_reachable(monkeypatch) -> None:
    """Make suppression and demo lookup succeed so only the opt-out gate decides."""
    monkeypatch.setattr(sms_service, "is_suppressed", lambda db, user_id, e164: False)
    monkeypatch.setattr(
        sms_relance_service, "demo_for_prospect", lambda db, user_id, pid: SimpleNamespace(id=9, slug="s")
    )


def test_excluded_prospect_is_not_a_relance_candidate(monkeypatch):
    _allow_reachable(monkeypatch)

    candidate = sms_relance_service._build_candidate(
        None, user_id=1, prospect=_prospect(sms_relance_excluded=True), emailed_at=None, cold=False
    )

    assert candidate is None


def test_exclusion_does_not_block_a_cold_sms(monkeypatch):
    _allow_reachable(monkeypatch)

    candidate = sms_relance_service._build_candidate(
        None, user_id=1, prospect=_prospect(sms_relance_excluded=True), emailed_at=None, cold=True
    )

    assert candidate is not None
    assert candidate.cold is True
