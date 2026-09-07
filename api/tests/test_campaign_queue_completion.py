"""A campaign is « terminée » once its send queue has fully drained.

``complete_drained_campaigns`` flips every ACTIVE campaign whose queue holds no more
``pending`` or ``sending`` rows to COMPLETED — every J1 and follow-up reached a terminal
state — and records each one in the activity feed. It is the only path to the COMPLETED
status; without it a campaign whose sends all went out would stay ACTIVE forever.
"""

from types import SimpleNamespace

from pytest import MonkeyPatch

from models.campaign import CampaignStatus
from services import campaign_queue_service as queue_module
from services.campaign_queue_service import CampaignQueueService


class _Result:
    """Stand-in for a SQLAlchemy Result, answering whichever accessor the code under test uses."""

    def __init__(self, *, rows: list[object] | None = None, scalars: list[object] | None = None) -> None:
        self._rows = rows or []
        self._scalars = scalars or []

    def all(self) -> list[object]:
        return list(self._rows)

    def scalars(self) -> list[object]:
        return list(self._scalars)


class _FakeDB:
    """Session stand-in returning pre-programmed results in call order, recording commits."""

    def __init__(self, results: list[_Result]) -> None:
        self._results = list(results)
        self.commits = 0

    def execute(self, *args: object, **kwargs: object) -> _Result:
        return self._results.pop(0)

    def commit(self) -> None:
        self.commits += 1


def _active_campaign(campaign_id: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=campaign_id, name=f"Campagne {campaign_id}", user_id=1, status=CampaignStatus.ACTIVE.value
    )


def test_completes_active_campaigns_whose_queue_has_drained(monkeypatch: MonkeyPatch) -> None:
    logged: list[int] = []
    monkeypatch.setattr(
        queue_module.activity_log_service, "record", lambda **kwargs: logged.append(kwargs["entity_id"])
    )
    first, second = _active_campaign(6), _active_campaign(7)
    db = _FakeDB([_Result(rows=[(6,), (7,)]), _Result(scalars=[first, second])])
    service = CampaignQueueService(db)

    completed = service.complete_drained_campaigns()

    assert completed == [6, 7]
    assert first.status == CampaignStatus.COMPLETED.value
    assert second.status == CampaignStatus.COMPLETED.value
    assert db.commits == 1
    assert logged == [6, 7]


def test_no_completion_when_nothing_has_drained(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(queue_module.activity_log_service, "record", lambda **kwargs: None)
    db = _FakeDB([_Result(rows=[])])
    service = CampaignQueueService(db)

    completed = service.complete_drained_campaigns()

    assert completed == []
    assert db.commits == 0
