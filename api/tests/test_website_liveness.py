"""Unit tests for the website liveness classification.

Real HTTP is out of the question in CI, so ``httpx.AsyncClient`` is faked: each
test drives a canned response (status code, body) or a transport error and
asserts the classification — the exact rules the scrapers rely on to keep
dead-site prospects instead of skipping them.
"""

import asyncio
from typing import ClassVar

import pytest

import services.website_liveness_service as liveness_module
from enums.website_status import WebsiteStatus
from services.website_liveness_service import WebsiteLivenessService


class _FakeResponse:
    """Minimal httpx.Response stand-in."""

    def __init__(self, status_code: int = 200, text: str = "<html>ok</html>") -> None:
        self.status_code = status_code
        self.text = text


class _FakeAsyncClient:
    """Fake httpx.AsyncClient returning a canned response or raising an error."""

    response: ClassVar[_FakeResponse | None] = None
    error: ClassVar[Exception | None] = None
    requested_urls: ClassVar[list[str]] = []

    def __init__(self, **_: object) -> None:
        return None

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def get(self, url: str) -> _FakeResponse:
        _FakeAsyncClient.requested_urls.append(url)
        if _FakeAsyncClient.error is not None:
            raise _FakeAsyncClient.error
        return _FakeAsyncClient.response or _FakeResponse()


@pytest.fixture(autouse=True)
def _fake_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route the service's httpx through the fake client with a fresh cache."""
    _FakeAsyncClient.response = None
    _FakeAsyncClient.error = None
    _FakeAsyncClient.requested_urls = []
    monkeypatch.setattr(liveness_module.httpx, "AsyncClient", _FakeAsyncClient)


def _check(service: WebsiteLivenessService, url: str | None) -> WebsiteStatus | None:
    return asyncio.run(service.check_website_status(url))


def test_no_url_returns_none() -> None:
    service = WebsiteLivenessService()
    assert _check(service, None) is None
    assert _check(service, "   ") is None
    assert _FakeAsyncClient.requested_urls == []


def test_responding_website_is_live() -> None:
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(status_code=200)
    assert _check(service, "https://www.artisan-durand.fr") is WebsiteStatus.LIVE


def test_not_found_website_is_dead() -> None:
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(status_code=404)
    assert _check(service, "https://garage-du-viaduc.fr") is WebsiteStatus.DEAD


def test_server_error_website_is_dead() -> None:
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(status_code=503)
    assert _check(service, "https://plomberie-morel.fr") is WebsiteStatus.DEAD


def test_a_coming_soon_page_answered_with_503_is_live() -> None:
    """A site in maintenance or « coming soon » answers 503 with its own page: a visitor sees it."""
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(
        status_code=503, text="<html><title>Atelier-E | Votre spécialiste électrique régional.</title></html>"
    )
    assert _check(service, "https://atelier-e.swiss/") is WebsiteStatus.LIVE


def test_a_server_s_own_503_page_is_dead() -> None:
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(status_code=503, text="<title>503 Service Unavailable</title>")
    assert _check(service, "https://plomberie-morel.fr") is WebsiteStatus.DEAD


def test_a_suspended_hosting_answered_with_503_is_dead() -> None:
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(
        status_code=503,
        text="<title>Website unavailable - OVHcloud</title><p>This site is currently suspended.</p>",
    )
    assert _check(service, "https://www.voltarys.ch/") is WebsiteStatus.DEAD


def test_bot_protection_status_is_not_dead() -> None:
    """403/429 usually mean a WAF on a working site — never call those dead."""
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(status_code=403)
    assert _check(service, "https://protected-site.fr") is WebsiteStatus.LIVE


def test_hosting_error_page_is_dead() -> None:
    """Solocal answers 200 with a 'SITE NOT FOUND' page for dead mini-sites."""
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(status_code=200, text="<h1>SITE NOT FOUND</h1>")
    assert _check(service, "https://ancien-site-artisan.fr") is WebsiteStatus.DEAD


def test_dns_failure_is_dead() -> None:
    service = WebsiteLivenessService()
    _FakeAsyncClient.error = liveness_module.httpx.ConnectError("[Errno 11001] getaddrinfo failed")
    assert _check(service, "https://domaine-disparu.fr") is WebsiteStatus.DEAD


def test_timeout_is_inconclusive_and_live() -> None:
    """A slow site must never be pitched as dead — same behaviour as before the check."""
    service = WebsiteLivenessService()
    _FakeAsyncClient.error = liveness_module.httpx.ReadTimeout("timed out")
    assert _check(service, "https://site-tres-lent.fr") is WebsiteStatus.LIVE


def test_live_directory_mini_site_is_placeholder() -> None:
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(status_code=200)
    assert _check(service, "https://debiolepatrick.site-solocal.com") is WebsiteStatus.PLACEHOLDER
    assert _check(service, "https://monsalon.wixsite.com/coiffure") is WebsiteStatus.PLACEHOLDER
    assert _check(service, "https://www.pagesjaunes.fr/pros/12345678") is WebsiteStatus.PLACEHOLDER


def test_dead_directory_mini_site_is_dead() -> None:
    """business.site pages all 404 since Google closed them — DEAD wins over PLACEHOLDER."""
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(status_code=404)
    assert _check(service, "https://garage-du-viaduc.business.site") is WebsiteStatus.DEAD


def test_placeholder_host_requires_suffix_match() -> None:
    """A domain merely containing a placeholder name is a normal website."""
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(status_code=200)
    assert _check(service, "https://mybusiness.site.example.fr") is WebsiteStatus.LIVE


def test_scheme_less_url_is_normalized() -> None:
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(status_code=200)
    assert _check(service, "artisan-sans-schema.fr") is WebsiteStatus.LIVE
    assert _FakeAsyncClient.requested_urls == ["https://artisan-sans-schema.fr"]


def test_verdict_is_cached_per_url() -> None:
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(status_code=404)
    assert _check(service, "https://meme-site.fr") is WebsiteStatus.DEAD
    requests_of_first_check = len(_FakeAsyncClient.requested_urls)
    assert _check(service, "https://meme-site.fr") is WebsiteStatus.DEAD
    assert len(_FakeAsyncClient.requested_urls) == requests_of_first_check


def test_a_site_is_only_dead_once_its_other_address_forms_failed_too() -> None:
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(status_code=404)
    assert _check(service, "http://ancienne-adresse.ch/") is WebsiteStatus.DEAD
    assert _FakeAsyncClient.requested_urls == [
        "http://ancienne-adresse.ch/",
        "https://ancienne-adresse.ch/",
        "https://www.ancienne-adresse.ch/",
        "http://www.ancienne-adresse.ch/",
    ]


def test_a_listing_keeping_the_http_address_of_an_https_site_is_live(monkeypatch: pytest.MonkeyPatch) -> None:
    """Seen on a real candidate: http://… answered 500, https://… answered 200."""

    async def answer_by_scheme(self: _FakeAsyncClient, url: str) -> _FakeResponse:
        return _FakeResponse(status_code=200 if url.startswith("https://") else 500)

    monkeypatch.setattr(_FakeAsyncClient, "get", answer_by_scheme)
    assert _check(WebsiteLivenessService(), "http://fv-entretien.ch/") is WebsiteStatus.LIVE


def test_live_foreign_directory_listing_is_placeholder() -> None:
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(status_code=200)
    assert _check(service, "https://www.local.ch/fr/d/lausanne/1004/sanitaire/abc") is WebsiteStatus.PLACEHOLDER
    assert _check(service, "https://sanitaire-rochat.localsearch.ch") is WebsiteStatus.PLACEHOLDER
    assert _check(service, "https://www.pagesjaunes.ca/bus/Quebec/Laval/Plomberie-Tremblay/1234567.html") is (
        WebsiteStatus.PLACEHOLDER
    )


def test_german_domain_for_sale_page_is_dead() -> None:
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(status_code=200, text="<h1>Diese Domain steht zum Verkauf!</h1>")
    assert _check(service, "https://sanitaer-meier.ch") is WebsiteStatus.DEAD
    _FakeAsyncClient.response = _FakeResponse(status_code=200, text="<title>Domain zu verkaufen</title>")
    assert _check(service, "https://garage-huber.ch") is WebsiteStatus.DEAD


def test_a_live_german_site_selling_something_stays_live() -> None:
    """« Occasionen zu verkaufen » on a garage site is not a parked domain."""
    service = WebsiteLivenessService()
    _FakeAsyncClient.response = _FakeResponse(status_code=200, text="<h2>Occasionen zu verkaufen</h2>")
    assert _check(service, "https://garage-keller.ch") is WebsiteStatus.LIVE


def test_a_host_s_welcome_page_for_a_domain_without_a_site_is_dead() -> None:
    _FakeAsyncClient.response = _FakeResponse(
        200, "<html><head><title>Bienvenue sur garage-exemple.ch</title></head><body></body></html>"
    )

    assert _check(WebsiteLivenessService(), "https://garage-exemple.ch/") is WebsiteStatus.DEAD


def test_a_site_welcoming_its_visitors_by_name_stays_live() -> None:
    _FakeAsyncClient.response = _FakeResponse(
        200, "<html><head><title>Bienvenue sur le site du Garage Exemple</title></head></html>"
    )

    assert _check(WebsiteLivenessService(), "https://garage-exemple.ch/") is WebsiteStatus.LIVE
