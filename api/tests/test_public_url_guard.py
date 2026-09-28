"""Fetching an address typed by someone reaches the public internet only: resolved, checked, pinned, per redirect."""

import asyncio
import ipaddress
from typing import Any

import httpx
import pytest

import services.ai_assistant.website_crawler as crawler_module
from services.ai_assistant.website_crawler import AiAssistantWebsiteCrawler
from services.brand_color_service import BrandColorService
from services.public_url_guard import (
    NonPublicAddressError,
    PublicOnlyAsyncTransport,
    PublicOnlyTransport,
    PublicUrlGuard,
)

# What a fake DNS answers: a public site, a site pointing at the machine itself, and a rebinding-style double answer.
_DNS: dict[str, list[str]] = {
    "toiture-martin.fr": ["93.184.216.34"],
    "www.toiture-martin.fr": ["2606:4700:4700::1111", "93.184.216.35"],
    "interne.toiture-martin.fr": ["10.0.0.12"],
    "double.toiture-martin.fr": ["93.184.216.36", "127.0.0.1"],
}


@pytest.fixture
def fake_dns(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Resolve through the table above, recording the hosts asked."""
    asked: list[str] = []
    real_resolve = PublicUrlGuard.resolve

    def resolve(host: str, port: int) -> list[str]:
        asked.append(host)
        if host in _DNS:
            return list(_DNS[host])
        return real_resolve(host, port)

    monkeypatch.setattr(PublicUrlGuard, "resolve", staticmethod(resolve))
    return asked


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.1.2.3",
        "172.16.5.4",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "0.0.0.0",
        "224.0.0.1",
        "240.0.0.1",
        "255.255.255.255",
        "198.18.0.1",
        "::1",
        "::",
        "fe80::1",
        "fc00::1",
        "fd00:ec2::254",
        "ff02::1",
        "::ffff:127.0.0.1",
        "::ffff:169.254.169.254",
        "64:ff9b::7f00:1",
        "2002:7f00:1::",
        "2001:db8::1",
    ],
)
def test_a_private_local_or_reserved_address_is_not_public(address: str) -> None:
    assert not PublicUrlGuard.is_public_address(ipaddress.ip_address(address))


@pytest.mark.parametrize(
    "address", ["93.184.216.34", "8.8.8.8", "2606:4700:4700::1111", "2a00:1450:4007:80c::200e", "::ffff:8.8.8.8"]
)
def test_an_internet_address_is_public(address: str) -> None:
    assert PublicUrlGuard.is_public_address(ipaddress.ip_address(address))


def _recording_transport(requests: list[httpx.Request], routes: dict[str, httpx.Response]) -> httpx.MockTransport:
    """A mock network that records what reaches it and answers by path."""

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return routes.get(request.url.path, httpx.Response(404))

    return httpx.MockTransport(handler)


@pytest.mark.usefixtures("fake_dns")
def test_a_public_host_is_fetched_at_its_checked_address_under_its_own_name() -> None:
    requests: list[httpx.Request] = []
    network = _recording_transport(requests, {"/tarifs": httpx.Response(200, text="Tarifs")})

    async def fetch() -> httpx.Response:
        async with httpx.AsyncClient(transport=PublicOnlyAsyncTransport(network)) as client:
            return await client.get("https://www.toiture-martin.fr/tarifs")

    response = asyncio.run(fetch())

    [sent] = requests
    assert response.text == "Tarifs" and str(response.url) == "https://www.toiture-martin.fr/tarifs"
    assert sent.url.host == "93.184.216.35"  # IPv4 first, the address that was checked
    assert sent.headers["host"] == "www.toiture-martin.fr"
    assert sent.extensions["sni_hostname"] == "www.toiture-martin.fr"


@pytest.mark.usefixtures("fake_dns")
@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8005/admin",
        "http://localhost:8005/admin",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]:8005/",
        "http://[fd00:ec2::254]/",
        "http://interne.toiture-martin.fr/",
        "http://double.toiture-martin.fr/",
    ],
)
def test_a_host_outside_the_public_internet_is_refused_before_any_connection(url: str) -> None:
    requests: list[httpx.Request] = []
    network = _recording_transport(requests, {})

    async def fetch() -> None:
        async with httpx.AsyncClient(transport=PublicOnlyAsyncTransport(network)) as client:
            await client.get(url)

    with pytest.raises(NonPublicAddressError):
        asyncio.run(fetch())
    assert requests == []


def test_a_host_written_as_a_bare_number_is_never_fetched() -> None:
    """Linux reads it as 127.0.0.1 (then refused), Windows cannot resolve it: either way nothing is fetched."""
    requests: list[httpx.Request] = []
    network = _recording_transport(requests, {})

    async def fetch() -> None:
        async with httpx.AsyncClient(transport=PublicOnlyAsyncTransport(network)) as client:
            await client.get("http://2130706433/")

    with pytest.raises(httpx.ConnectError):
        asyncio.run(fetch())
    assert requests == []


@pytest.mark.usefixtures("fake_dns")
@pytest.mark.parametrize(
    "location", ["http://127.0.0.1:8005/admin", "http://interne.toiture-martin.fr/", "http://[::ffff:10.0.0.1]/"]
)
def test_a_redirect_to_a_non_public_address_is_refused(location: str) -> None:
    requests: list[httpx.Request] = []
    network = _recording_transport(requests, {"/": httpx.Response(302, headers={"location": location})})

    async def fetch() -> None:
        async with httpx.AsyncClient(transport=PublicOnlyAsyncTransport(network), follow_redirects=True) as client:
            await client.get("https://toiture-martin.fr/")

    with pytest.raises(NonPublicAddressError):
        asyncio.run(fetch())
    assert [request.url.host for request in requests] == ["93.184.216.34"]


@pytest.mark.usefixtures("fake_dns")
def test_the_sync_transport_guards_the_same_way() -> None:
    requests: list[httpx.Request] = []
    network = _recording_transport(
        requests, {"/logo.png": httpx.Response(302, headers={"location": "http://10.0.0.1/"})}
    )

    with (
        httpx.Client(transport=PublicOnlyTransport(network), follow_redirects=True) as client,
        pytest.raises(NonPublicAddressError),
    ):
        client.get("https://toiture-martin.fr/logo.png")
    with httpx.Client(transport=PublicOnlyTransport(network)) as client, pytest.raises(NonPublicAddressError):
        client.get("http://169.254.169.254/")
    assert [request.url.host for request in requests] == ["93.184.216.34"]


def test_the_website_reader_never_reaches_an_internal_address(
    fake_dns: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A website field set to an internal address, or a page redirecting to one, reads nothing from it."""
    requests: list[httpx.Request] = []
    home = (
        "<html><head><title>Toiture Martin</title></head><body><main><p>Couvreur à Poitiers.</p>"
        '<a href="/tarifs">Tarifs</a></main></body></html>'
    )
    network = _recording_transport(
        requests,
        {
            "/": httpx.Response(200, text=home, headers={"content-type": "text/html"}),
            "/tarifs": httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data/"}),
        },
    )
    monkeypatch.setattr(crawler_module, "PublicOnlyAsyncTransport", lambda: PublicOnlyAsyncTransport(network))

    internal = asyncio.run(AiAssistantWebsiteCrawler().crawl("http://localhost:8005/"))
    public = asyncio.run(AiAssistantWebsiteCrawler().crawl("toiture-martin.fr"))

    assert internal is None
    assert public is not None and [page["url"] for page in public["pages"]] == ["https://toiture-martin.fr/"]
    assert {request.url.host for request in requests} == {"93.184.216.34"}


def test_a_logo_on_an_internal_address_gives_no_colour(monkeypatch: pytest.MonkeyPatch, fake_dns: list[str]) -> None:
    requests: list[httpx.Request] = []
    network = _recording_transport(requests, {})
    original = httpx.HTTPTransport

    def mocked_network(*args: Any, **kwargs: Any) -> httpx.BaseTransport:
        return network

    monkeypatch.setattr(httpx, "HTTPTransport", mocked_network)
    try:
        colour = BrandColorService().extract_brand_color("http://169.254.169.254/logo.png")
    finally:
        monkeypatch.setattr(httpx, "HTTPTransport", original)

    assert colour is None
    assert requests == []
