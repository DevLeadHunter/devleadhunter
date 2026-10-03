"""A worker restart can leave a queue item stuck in ``sending`` (process died mid-dispatch).

``reclaim_orphaned_sending`` settles each such row from the truth of whether the email actually left:
an ``EmailLog`` at or after the item's slot means it was sent (mark ``sent`` + arm follow-ups), no log
means it never went out (requeue ``pending``). The email-log check is what prevents a re-send.
"""

from types import SimpleNamespace

from services.campaign_queue_service import CampaignQueueService


class _Result:
    """Stand-in for a SQLAlchemy Result, answering whichever accessor the code under test uses."""

    def __init__(self, *, scalars: list[object] | None = None, one: object = None, scalar: object = None) -> None:
        self._scalars = scalars or []
        self._one = one
        self._scalar = scalar

    def scalars(self) -> list[object]:
        return list(self._scalars)

    def scalar_one_or_none(self) -> object:
        return self._one

    def scalar(self) -> object:
        return self._scalar


class _FakeDB:
    """Session stand-in that returns pre-programmed results in call order and records commits."""

    def __init__(self, results: list[_Result]) -> None:
        self._results = list(results)
        self.commits = 0
        self.prospect = SimpleNamespace(contacted=False)

    def execute(self, *args: object, **kwargs: object) -> _Result:
        return self._results.pop(0)

    def get(self, model: object, primary_key: object) -> object:
        return self.prospect

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        pass


def _orphan() -> SimpleNamespace:
    return SimpleNamespace(
        id=52,
        status="sending",
        campaign_id=6,
        prospect_id=14,
        ab_variant=None,
        scheduled_at="2026-08-24T08:26:01",
        queue_type="initial",
        email_log_id=None,
        campaign=SimpleNamespace(channel="email"),
    )


def test_reclaim_marks_item_sent_and_arms_follow_ups_when_the_email_went_out() -> None:
    item = _orphan()
    log = SimpleNamespace(id=24)
    db = _FakeDB([_Result(scalars=[item]), _Result(one=log), _Result(scalar=0)])
    service = CampaignQueueService(db)
    scheduled: list[object] = []
    service._schedule_follow_ups = lambda queued: scheduled.append(queued)  # type: ignore[method-assign]

    reconciled = service.reclaim_orphaned_sending()

    assert reconciled == 1
    assert item.status == "sent"
    assert item.email_log_id == 24
    assert db.prospect.contacted is True
    assert scheduled == [item]


def test_reclaim_requeues_item_as_pending_when_no_email_went_out() -> None:
    item = _orphan()
    db = _FakeDB([_Result(scalars=[item]), _Result(one=None)])
    service = CampaignQueueService(db)
    scheduled: list[object] = []
    service._schedule_follow_ups = lambda queued: scheduled.append(queued)  # type: ignore[method-assign]

    reconciled = service.reclaim_orphaned_sending()

    assert reconciled == 1
    assert item.status == "pending"
    assert scheduled == []
