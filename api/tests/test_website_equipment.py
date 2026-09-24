"""Unit tests for the "déjà équipé" detection of a prospect's website.

The detector reads served HTML only, so each test feeds a small page and checks
what the Réceptionniste IA sourcing relies on: which chat vendor is installed,
whether the site has a contact form, and where its contact page is. The fetch
path runs against a fake ``httpx.AsyncClient``.
"""

import asyncio
from typing import ClassVar

import pytest

import services.website_equipment_service as equipment_module
from enums.chat_widget_provider import ChatWidgetProvider
from services.website_equipment_service import (
    WebsiteEquipment,
    WebsiteEquipmentDetector,
    WebsiteEquipmentService,
)


def test_tidio_snippet_is_detected() -> None:
    html = '<html><head><script src="//code.tidio.co/abc123.js" async></script></head></html>'

    equipment = WebsiteEquipmentDetector.detect(html)

    assert equipment.chat_providers == (ChatWidgetProvider.TIDIO,)
    assert equipment.has_chat


def test_inline_crisp_snippet_is_detected_by_its_global() -> None:
    html = '<script>window.$crisp=[];window.CRISP_WEBSITE_ID="f00";</script>'

    assert WebsiteEquipmentDetector.detect_chat_providers(html) == (ChatWidgetProvider.CRISP,)


def test_ionos_receptionist_chat_is_detected() -> None:
    html = (
        '<script src="https://ionos.ai-voice-receptionist.com/chat-scripts-MqGN74WP/web-chat.js" '
        'name="web-chat" data-client-secret="x"></script>'
    )

    assert WebsiteEquipmentDetector.detect_chat_providers(html) == (ChatWidgetProvider.IONOS,)


def test_hubspot_tracking_alone_is_not_a_chat() -> None:
    html = '<script id="hs-script-loader" src="//js.hs-scripts.com/123.js"></script>'

    assert WebsiteEquipmentDetector.detect_chat_providers(html) == ()


def test_several_vendors_are_all_reported_in_enum_order() -> None:
    html = '<script src="https://embed.tawk.to/1/default"></script><script src="https://code.tidio.co/x.js"></script>'

    assert WebsiteEquipmentDetector.detect_chat_providers(html) == (ChatWidgetProvider.TAWK, ChatWidgetProvider.TIDIO)


def test_page_without_widget_or_form_is_unequipped() -> None:
    equipment = WebsiteEquipmentDetector.detect("<html><body><h1>Toitures Morel</h1></body></html>")

    assert equipment == WebsiteEquipment()
    assert not equipment.has_chat


def test_form_with_a_message_area_is_a_contact_form() -> None:
    html = '<form action="/envoyer"><input name="nom"><input type="email" name="email"><textarea></textarea></form>'

    assert WebsiteEquipmentDetector.has_contact_form(html)


def test_form_with_name_email_and_phone_is_a_contact_form() -> None:
    html = '<form><input name="nom"><input type="email" name="email"><input type="tel" name="tel"></form>'

    assert WebsiteEquipmentDetector.has_contact_form(html)


@pytest.mark.parametrize(
    "html",
    [
        '<form class="newsletter-form"><input name="prenom"><input type="email" name="email"></form>',
        '<form><input type="email" name="email"><button>OK</button></form>',
        '<form role="search"><input name="query"><textarea></textarea></form>',
        '<form action="/"><input type="text" name="s"></form>',
        '<form id="login"><input type="email" name="email"><input type="password" name="pwd"></form>',
    ],
)
def test_newsletter_search_and_login_forms_are_not_contact_forms(html: str) -> None:
    assert not WebsiteEquipmentDetector.has_contact_form(html)


def test_form_plugin_assets_count_as_a_contact_form() -> None:
    html = (
        '<link rel="stylesheet" href="/wp-content/plugins/contact-form-7/includes/css/styles.css"><div class="wpcf7">'
    )

    assert WebsiteEquipmentDetector.has_contact_form(html)


def test_contact_link_is_resolved_against_the_page_url() -> None:
    html = '<nav><a href="/services">Services</a><a href="/nous-contacter/">Contact</a></nav>'

    url = WebsiteEquipmentDetector.find_contact_page_url(html, "https://www.toitures-morel.fr/")

    assert url == "https://www.toitures-morel.fr/nous-contacter/"


def test_contact_link_is_preferred_over_a_quote_link() -> None:
    html = '<a href="/demande-de-devis">Devis gratuit</a><a href="/contact">Nous écrire</a>'

    url = WebsiteEquipmentDetector.find_contact_page_url(html, "https://garage.be")

    assert url == "https://garage.be/contact"


def test_quote_link_is_used_when_there_is_no_contact_link() -> None:
    html = '<a href="https://toitures-morel.fr/devis">Devis</a>'

    url = WebsiteEquipmentDetector.find_contact_page_url(html, "https://www.toitures-morel.fr")

    assert url == "https://toitures-morel.fr/devis"


@pytest.mark.parametrize(
    "html",
    [
        '<a href="https://www.facebook.com/contact">Contact</a>',
        '<a href="mailto:contact@garage.be">contact@garage.be</a>',
        '<a href="#contact">Contact</a>',
        '<a href="/">Accueil</a>',
    ],
)
def test_foreign_mail_and_same_page_links_are_ignored(html: str) -> None:
    assert WebsiteEquipmentDetector.find_contact_page_url(html, "https://garage.be/") is None


def test_merging_pages_unions_providers_and_forms() -> None:
    home = WebsiteEquipment(chat_providers=(ChatWidgetProvider.TIDIO,))
    contact = WebsiteEquipment(
        chat_providers=(ChatWidgetProvider.TIDIO, ChatWidgetProvider.CRISP), has_contact_form=True
    )

    merged = home.merged_with(contact)

    assert merged.chat_providers == (ChatWidgetProvider.TIDIO, ChatWidgetProvider.CRISP)
    assert merged.has_contact_form


class _FakeResponse:
    """Minimal httpx.Response stand-in."""

    def __init__(self, url: str, text: str, status_code: int = 200, content_type: str = "text/html") -> None:
        self.url = url
        self.text = text
        self.status_code = status_code
        self.headers = {"content-type": content_type}

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300


class _FakeAsyncClient:
    """Fake httpx.AsyncClient serving canned pages by URL."""

    pages: ClassVar[dict[str, _FakeResponse]] = {}
    requested_urls: ClassVar[list[str]] = []

    def __init__(self, **_: object) -> None:
        return None

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def get(self, url: str) -> _FakeResponse:
        _FakeAsyncClient.requested_urls.append(url)
        return _FakeAsyncClient.pages.get(url) or _FakeResponse(url, "not found", status_code=404)


@pytest.fixture(autouse=True)
def _fake_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route the service's httpx through the fake client."""
    _FakeAsyncClient.pages = {}
    _FakeAsyncClient.requested_urls = []
    monkeypatch.setattr(equipment_module.httpx, "AsyncClient", _FakeAsyncClient)


def _serve(url: str, html: str, **kwargs: object) -> None:
    _FakeAsyncClient.pages[url] = _FakeResponse(url, html, **kwargs)  # type: ignore[arg-type]


def test_inspect_reads_the_contact_page_when_the_home_page_has_no_form() -> None:
    _serve("https://toitures-morel.fr", '<script src="//code.tidio.co/x.js"></script><a href="/contact">Contact</a>')
    _serve("https://toitures-morel.fr/contact", "<form><input><input type='email'><textarea></textarea></form>")

    equipment = asyncio.run(WebsiteEquipmentService().inspect("toitures-morel.fr"))

    assert equipment == WebsiteEquipment(chat_providers=(ChatWidgetProvider.TIDIO,), has_contact_form=True)
    assert _FakeAsyncClient.requested_urls == ["https://toitures-morel.fr", "https://toitures-morel.fr/contact"]


def test_inspect_stops_at_the_home_page_when_it_has_a_form() -> None:
    _serve("https://garage.be", '<form><textarea></textarea></form><a href="/contact">Contact</a>')

    equipment = asyncio.run(WebsiteEquipmentService().inspect("https://garage.be"))

    assert equipment is not None and equipment.has_contact_form
    assert _FakeAsyncClient.requested_urls == ["https://garage.be"]


def test_unreadable_home_page_is_unknown_not_unequipped() -> None:
    _serve("https://garage.be", "<html></html>", status_code=503)

    assert asyncio.run(WebsiteEquipmentService().inspect("https://garage.be")) is None
    assert asyncio.run(WebsiteEquipmentService().inspect(None)) is None
    assert asyncio.run(WebsiteEquipmentService().inspect("   ")) is None


def test_non_html_home_page_is_unknown() -> None:
    _serve("https://garage.be/plan.pdf", "%PDF-1.7", content_type="application/pdf")

    assert asyncio.run(WebsiteEquipmentService().inspect("https://garage.be/plan.pdf")) is None


def test_inspect_many_maps_each_distinct_site() -> None:
    _serve("https://a.fr", '<script src="https://embed.tawk.to/1"></script>')

    results = asyncio.run(WebsiteEquipmentService().inspect_many(["https://a.fr", "https://b.fr", "https://a.fr"]))

    assert results == {
        "https://a.fr": WebsiteEquipment(chat_providers=(ChatWidgetProvider.TAWK,)),
        "https://b.fr": None,
    }
