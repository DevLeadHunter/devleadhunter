"""
Unit tests for the Resend send retries: a network cut is retried, an answer from Resend is not.
"""

from typing import Any

import aiohttp
import pytest

from services import resend_service as resend_module
from services.resend_service import ResendService, ResendUnreachableError

_PAYLOAD: dict[str, Any] = {"from": "Jean <jean@mail.example.com>", "to": ["pro@example.com"], "subject": "le site"}


class _FlakyResend:
    """Stand-in for the HTTP call: fails ``failures`` times with the given error, then answers."""

    def __init__(self, failures: int, error: BaseException) -> None:
        self.failures = failures
        self.error = error
        self.calls = 0

    async def post(self, payload: dict[str, Any], api_key: str, to_email: str) -> dict[str, str]:
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return {"message_id": f"msg_{self.calls}", "provider": "resend"}


def _install(monkeypatch: pytest.MonkeyPatch, flaky: _FlakyResend) -> list[int]:
    """Route the HTTP call to the stand-in and record the waits instead of sleeping."""
    waits: list[int] = []

    async def no_sleep(delay: int) -> None:
        waits.append(delay)

    monkeypatch.setattr(ResendService, "_post", flaky.post)
    monkeypatch.setattr(resend_module, "_sleep", no_sleep)
    return waits


@pytest.mark.asyncio
async def test_two_network_failures_then_an_answer_is_one_successful_send(monkeypatch: pytest.MonkeyPatch) -> None:
    flaky = _FlakyResend(failures=2, error=aiohttp.ClientOSError("Name or service not known"))
    waits = _install(monkeypatch, flaky)

    result = await ResendService()._post_with_retries(_PAYLOAD, "re_test", "pro@example.com")

    assert result == {"message_id": "msg_3", "provider": "resend"}
    assert flaky.calls == 3
    assert waits == [2, 5]


@pytest.mark.asyncio
async def test_a_network_cut_that_outlasts_every_wait_is_reported_as_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    flaky = _FlakyResend(failures=10, error=TimeoutError())
    waits = _install(monkeypatch, flaky)

    with pytest.raises(ResendUnreachableError):
        await ResendService()._post_with_retries(_PAYLOAD, "re_test", "pro@example.com")

    assert flaky.calls == 4
    assert waits == [2, 5, 10]


@pytest.mark.asyncio
async def test_an_answer_from_resend_is_never_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 422 is Resend refusing the email: retrying would only send the refusal again."""
    flaky = _FlakyResend(failures=1, error=RuntimeError("Resend API error 422: invalid recipient"))
    waits = _install(monkeypatch, flaky)

    with pytest.raises(RuntimeError, match="422"):
        await ResendService()._post_with_retries(_PAYLOAD, "re_test", "pro@example.com")

    assert flaky.calls == 1
    assert waits == []
