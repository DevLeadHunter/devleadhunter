"""Reading the front page of an email's domain: a site whose certificate is broken is read in plain HTTP."""

import asyncio
from collections.abc import Callable
from typing import Any

import httpx
import pytest

import services.prospect_search.candidate_verifier as candidate_verifier_module
from services.prospect_search.candidate_verifier import CandidateVerifier

_REAL_ASYNC_CLIENT = httpx.AsyncClient


def _clients_answering(handler: Callable[[httpx.Request], httpx.Response]) -> Callable[..., httpx.AsyncClient]:
    """Build the HTTP clients the verifier opens on a canned transport."""

    def build(**kwargs: Any) -> httpx.AsyncClient:
        return _REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler), **kwargs)

    return build


def test_a_site_with_a_broken_certificate_is_read_in_plain_http(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.scheme == "https":
            raise httpx.ConnectError("certificate verify failed: Hostname mismatch", request=request)
        return httpx.Response(200, text="<title>Rochat & fils SA</title>")

    monkeypatch.setattr(candidate_verifier_module.httpx, "AsyncClient", _clients_answering(handler))

    front_page = asyncio.run(CandidateVerifier._front_page_of("rochat-fils.ch"))

    assert front_page is not None
    assert front_page[0].startswith("http://rochat-fils.ch")
    assert front_page[1] == "<title>Rochat & fils SA</title>"


def test_a_site_answering_an_error_in_https_is_not_asked_again_in_http(monkeypatch: pytest.MonkeyPatch) -> None:
    asked_schemes: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        asked_schemes.append(request.url.scheme)
        return httpx.Response(403, text="Checking your browser")

    monkeypatch.setattr(candidate_verifier_module.httpx, "AsyncClient", _clients_answering(handler))

    assert asyncio.run(CandidateVerifier._front_page_of("rochat-fils.ch")) is None
    assert asked_schemes == ["https"]
