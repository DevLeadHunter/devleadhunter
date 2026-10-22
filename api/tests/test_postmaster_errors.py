"""
The Postmaster page tells the real failure: a retired API version is named as such and never retried, a real
quota stays a quota, and a word that merely contains « rate » is no longer read as one.
"""

import httplib2
import pytest
from googleapiclient.errors import HttpError

import services.postmaster_service as postmaster_module
from services.postmaster_service import PostmasterService

_RETIRED_MESSAGE = "This version of the Postmaster Tools API is no longer supported. Get the current API."


def _http_error(status: int, message: str) -> HttpError:
    content = f'{{"error": {{"code": {status}, "message": "{message}"}}}}'.encode()
    return HttpError(httplib2.Response({"status": str(status)}), content)


class _FailingRequest:
    """A Google API request that always fails with the same error."""

    def __init__(self, error: HttpError) -> None:
        self.error = error
        self.calls = 0

    def execute(self) -> dict[str, object]:
        self.calls += 1
        raise self.error


def test_a_retired_api_version_is_named_and_not_called_a_quota() -> None:
    message = PostmasterService._friendly_error(_http_error(429, _RETIRED_MESSAGE))

    assert "retiré" in message
    assert not message.startswith("Quota")


def test_a_real_quota_is_still_a_quota() -> None:
    message = PostmasterService._friendly_error(_http_error(429, "Quota exceeded for quota metric Queries"))

    assert message.startswith("Quota")


def test_a_word_that_contains_rate_is_not_a_quota() -> None:
    message = PostmasterService._friendly_error(RuntimeError("Please migrate your integration"))

    assert not message.startswith("Quota")


def test_a_retired_api_version_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    waits: list[float] = []
    monkeypatch.setattr(postmaster_module.time, "sleep", waits.append)
    request = _FailingRequest(_http_error(429, _RETIRED_MESSAGE))

    with pytest.raises(HttpError):
        PostmasterService._execute(request)

    assert request.calls == 1
    assert waits == []


def test_a_real_rate_limit_is_retried_after_each_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    waits: list[float] = []
    monkeypatch.setattr(postmaster_module.time, "sleep", waits.append)
    request = _FailingRequest(_http_error(429, "Too many requests"))

    with pytest.raises(HttpError):
        PostmasterService._execute(request)

    assert request.calls == 4
    assert waits == [2.0, 5.0, 10.0]
