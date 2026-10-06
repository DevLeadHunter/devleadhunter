"""The « Site Web » button of a Google card: its redirect is followed to the business's address."""

import asyncio
from typing import Any

import httpx
import pytest

import scrappers.google_website_button as google_website_button_module
from scrappers.google_website_button import GoogleWebsiteButton


def _destination(monkeypatch: pytest.MonkeyPatch, response: httpx.Response, link: str) -> str | None:
    real_client = httpx.AsyncClient

    def client_with_transport(**kwargs: Any) -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(lambda request: response), **kwargs)

    monkeypatch.setattr(google_website_button_module.httpx, "AsyncClient", client_with_transport)
    return asyncio.run(GoogleWebsiteButton().destination(link))


def test_the_google_redirect_gives_the_address_the_button_leads_to(monkeypatch: pytest.MonkeyPatch) -> None:
    response = httpx.Response(302, headers={"location": "https://yellow.local.ch/d/K9KKuhWx"})

    assert _destination(monkeypatch, response, "/goto?url=CAESVQHrOzAV") == "https://yellow.local.ch/d/K9KKuhWx"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="<html>Avant d'accéder à Google</html>"),
        httpx.Response(302, headers={"location": "https://www.google.com/sorry/index?continue=x"}),
        httpx.Response(302, headers={"location": "/maps"}),
    ],
)
def test_a_google_answer_without_a_way_out_gives_no_address(
    monkeypatch: pytest.MonkeyPatch, response: httpx.Response
) -> None:
    assert _destination(monkeypatch, response, "/goto?url=CAESVQHrOzAV") is None


def test_a_plain_address_on_the_button_is_its_destination() -> None:
    assert asyncio.run(GoogleWebsiteButton().destination("https://www.verdalys.ch/")) == "https://www.verdalys.ch/"
