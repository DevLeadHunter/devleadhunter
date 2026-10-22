"""
The Postmaster page reads Google's v2 API: the registered domain that covers the sending domain, Gmail's
compliance status and the daily rates, and asks for a new consent when the stored access predates v2.
"""

from types import SimpleNamespace
from typing import Any

import httplib2
import pytest
from googleapiclient.errors import HttpError

import services.postmaster_service as postmaster_module
from services.postmaster_service import PostmasterService

_COMPLIANCE: dict[str, Any] = {
    "name": "domains/mail.dibodev.fr/complianceStatus",
    "complianceData": {
        "domainId": "dibodev.fr",
        "deliverabilityStatusVerdict": {"state": {"status": "NEEDS_WORK"}, "reason": "MESSAGE_VOLUME_LOW"},
        "rowData": [
            {"requirement": "SPF", "status": {"status": "COMPLIANT"}},
            {"requirement": "ONE_CLICK_UNSUBSCRIBE", "status": {"status": "COMPLIANT"}},
        ],
    },
}
_FIRST_PAGE: dict[str, Any] = {
    "domainStats": [
        {"date": {"year": 2026, "month": 10, "day": 21}, "metric": "spam_ratio", "value": {"doubleValue": 0.0}},
        {"date": {"year": 2026, "month": 10, "day": 21}, "metric": "spf_ratio", "value": {"doubleValue": 100.0}},
    ],
    "nextPageToken": "page-2",
}
_SECOND_PAGE: dict[str, Any] = {
    "domainStats": [
        {"date": {"year": 2026, "month": 10, "day": 20}, "metric": "spam_ratio", "value": {"doubleValue": 0.002}},
    ],
}


def _http_error(status: int, message: str) -> HttpError:
    content = f'{{"error": {{"code": {status}, "message": "{message}"}}}}'.encode()
    return HttpError(httplib2.Response({"status": str(status)}), content)


class _Request:
    """A Google API request that answers or fails once executed."""

    def __init__(self, answer: dict[str, Any] | HttpError) -> None:
        self.answer = answer

    def execute(self) -> dict[str, Any]:
        if isinstance(self.answer, HttpError):
            raise self.answer
        return self.answer


class _DomainStats:
    def __init__(self, client: "_FakeClient") -> None:
        self.client = client

    def query(self, parent: str, body: dict[str, Any]) -> _Request:
        self.client.stats_calls.append((parent, body.get("pageToken")))
        if parent != "domains/dibodev.fr":
            return _Request(_http_error(404, "Requested entity was not found."))
        return _Request(_SECOND_PAGE if body.get("pageToken") == "page-2" else _FIRST_PAGE)


class _Domains:
    def __init__(self, client: "_FakeClient") -> None:
        self.client = client

    def getComplianceStatus(self, name: str) -> _Request:
        self.client.compliance_calls.append(name)
        return _Request(self.client.compliance_answer)

    def domainStats(self) -> _DomainStats:
        return _DomainStats(self.client)


class _FakeClient:
    """The slice of the v2 client the service uses: compliance on the subdomain, stats on the root only."""

    def __init__(self, compliance_answer: dict[str, Any] | HttpError) -> None:
        self.compliance_answer = compliance_answer
        self.compliance_calls: list[str] = []
        self.stats_calls: list[tuple[str, str | None]] = []

    def domains(self) -> _Domains:
        return _Domains(self)


def _connected_user() -> SimpleNamespace:
    return SimpleNamespace(id=1, postmaster_oauth_refresh_token="encrypted", postmaster_google_email="leo@example.com")


def _use_client(monkeypatch: pytest.MonkeyPatch, client: _FakeClient) -> None:
    monkeypatch.setattr(PostmasterService, "_ensure_credentials", lambda _self, _db, _user: object())
    monkeypatch.setattr(postmaster_module, "build", lambda *_args, **_kwargs: client)


def test_a_sending_subdomain_is_read_through_its_registered_domain() -> None:
    assert PostmasterService.candidate_domains("mail.dibodev.fr") == ["mail.dibodev.fr", "dibodev.fr"]
    assert PostmasterService.candidate_domains("dibodev.fr") == ["dibodev.fr"]


def test_the_compliance_and_the_daily_rates_come_back_for_the_covering_domain(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient(_COMPLIANCE)
    _use_client(monkeypatch, client)

    result = PostmasterService().domain_stats(object(), _connected_user(), "mail.dibodev.fr", days=30)

    assert result["queried_domain"] == "dibodev.fr"
    assert result["domain_not_found"] is False
    assert result["compliance"] == {
        "domain": "dibodev.fr",
        "deliverability_status": "NEEDS_WORK",
        "deliverability_reason": "MESSAGE_VOLUME_LOW",
        "requirements": [
            {"requirement": "SPF", "status": "COMPLIANT"},
            {"requirement": "ONE_CLICK_UNSUBSCRIBE", "status": "COMPLIANT"},
        ],
    }
    assert [row["date"] for row in result["days"]] == ["2026-10-20", "2026-10-21"]
    assert result["latest"]["spf_ratio"] == 1.0
    assert result["latest"]["spam_ratio"] == 0.0
    assert result["days"][0]["spam_ratio"] == 0.002
    assert client.stats_calls == [
        ("domains/mail.dibodev.fr", None),
        ("domains/dibodev.fr", None),
        ("domains/dibodev.fr", "page-2"),
    ]


def _refuse_every_domain(*_args: object) -> list[dict[str, Any]]:
    raise _http_error(403, "The caller does not have permission")


def test_a_domain_registered_nowhere_is_reported_as_such(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient(_http_error(404, "Requested entity was not found."))
    _use_client(monkeypatch, client)
    monkeypatch.setattr(PostmasterService, "_query_daily_stats", _refuse_every_domain)

    result = PostmasterService().domain_stats(object(), _connected_user(), "mail.example.com", days=30)

    assert result["domain_not_found"] is True
    assert result["compliance"] is None
    assert result["days"] == []


def test_an_access_granted_before_v2_asks_to_reconnect(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _FakeClient(_http_error(403, "Request had insufficient authentication scopes."))
    _use_client(monkeypatch, client)

    result = PostmasterService().domain_stats(object(), _connected_user(), "mail.dibodev.fr", days=30)

    assert result["needs_reconnect"] is True
    assert "Reconnecter Google" in result["error"]
    assert client.compliance_calls == ["domains/mail.dibodev.fr/complianceStatus"]
