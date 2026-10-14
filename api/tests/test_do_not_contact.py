"""« Ne plus contacter » blocks every outreach channel and holds back pending sends.

The operator flag (set from the prospect drawer or a campaign row) must stop the prospect
everywhere: the email queue holds back their pending sends and keeps them visible as *held
back* (skip reason), and the SMS relance/cold selection drops them.
"""

from types import SimpleNamespace

from services.campaign_queue_service import CampaignQueueService
from services.sms_relance_service import sms_relance_service


class _QueueDB:
    """Session stand-in serving a fixed EmailQueue batch on ``.all()``."""

    def __init__(self, items: list[SimpleNamespace]) -> None:
        self._items = items
        self.commits = 0

    def query(self, *_entities: object) -> "_QueueDB":
        return self

    def filter(self, *_conditions: object) -> "_QueueDB":
        return self

    def all(self) -> list[SimpleNamespace]:
        return self._items

    def commit(self) -> None:
        self.commits += 1


def _pending(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {"id": 1, "prospect_id": 7, "status": "pending", "skip_reason": None}
    base.update(overrides)
    return SimpleNamespace(**base)


class TestSkipPendingForProspect:
    def test_holds_back_pending_items_with_the_reason(self) -> None:
        items = [_pending(id=1), _pending(id=2)]
        db = _QueueDB(items)

        held = CampaignQueueService(db).skip_pending_for_prospect(7, "pas chaud")

        assert held == 2
        assert all(item.status == "skipped" for item in items)
        assert all(item.skip_reason == "Ne plus contacter — pas chaud" for item in items)
        assert db.commits == 1

    def test_uses_a_bare_label_without_a_reason(self) -> None:
        items = [_pending()]

        CampaignQueueService(_QueueDB(items)).skip_pending_for_prospect(7, None)

        assert items[0].skip_reason == "Ne plus contacter"

    def test_nothing_to_hold_back_does_not_commit(self) -> None:
        db = _QueueDB([])

        held = CampaignQueueService(db).skip_pending_for_prospect(7)

        assert held == 0
        assert db.commits == 0


class TestSmsCandidateGate:
    def test_a_do_not_contact_prospect_is_never_an_sms_candidate(self) -> None:
        prospect = SimpleNamespace(phone="06 12 34 56 78", do_not_contact=True)

        candidate = sms_relance_service._build_candidate(_QueueDB([]), user_id=1, prospect=prospect, emailed_at=None)

        assert candidate is None
