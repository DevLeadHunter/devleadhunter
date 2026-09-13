"""Per-prospect gates of the automated SMS selection.

``sms_auto_excluded`` bars a prospect from EVERY automated SMS (relance J+30 and cold),
and a cold SMS — a FIRST touch — never goes to a prospect already contacted (manual
channels included): the operator owns that conversation.
"""

from types import SimpleNamespace

from services.sms_relance_service import sms_relance_service
from services.sms_service import sms_service


def _prospect(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 7,
        "phone": "06 12 34 56 78",
        "do_not_contact": False,
        "sms_auto_excluded": False,
        "contacted": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _allow_reachable(monkeypatch) -> None:
    """Make suppression and demo lookup succeed so only the prospect gates decide."""
    monkeypatch.setattr(sms_service, "is_suppressed", lambda db, user_id, e164: False)
    monkeypatch.setattr(
        sms_relance_service, "demo_for_prospect", lambda db, user_id, pid: SimpleNamespace(id=9, slug="s")
    )


def test_excluded_prospect_is_not_a_relance_candidate(monkeypatch):
    _allow_reachable(monkeypatch)

    candidate = sms_relance_service._build_candidate(
        None, user_id=1, prospect=_prospect(sms_auto_excluded=True), emailed_at=None, cold=False
    )

    assert candidate is None


def test_excluded_prospect_is_not_a_cold_candidate_either(monkeypatch):
    _allow_reachable(monkeypatch)

    candidate = sms_relance_service._build_candidate(
        None, user_id=1, prospect=_prospect(sms_auto_excluded=True), emailed_at=None, cold=True
    )

    assert candidate is None


def test_a_contacted_prospect_never_gets_a_cold_first_contact(monkeypatch):
    _allow_reachable(monkeypatch)

    candidate = sms_relance_service._build_candidate(
        None, user_id=1, prospect=_prospect(contacted=True), emailed_at=None, cold=True
    )

    assert candidate is None


def test_a_clean_prospect_stays_a_cold_candidate(monkeypatch):
    _allow_reachable(monkeypatch)

    candidate = sms_relance_service._build_candidate(None, user_id=1, prospect=_prospect(), emailed_at=None, cold=True)

    assert candidate is not None
    assert candidate.cold is True
