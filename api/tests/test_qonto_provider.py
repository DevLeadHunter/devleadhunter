"""Unit tests for the Qonto payment provider.

The provider makes real Business API calls, which can't be exercised against
Léo's account (it would create real invoices) and there's no connected sandbox
token in CI. So ``httpx`` is faked: each test drives canned responses and
asserts the *requests* the provider builds (body shape, IBAN, finalized status,
amount formatting) and how it *parses* the responses.
"""

import asyncio
from types import SimpleNamespace
from typing import ClassVar

import pytest

import services.payment_providers.qonto_provider as qonto_module
from core.config import settings
from services.payment_providers.base import BillingClient, InvoiceRequest
from services.payment_providers.qonto_provider import QontoEnvironmentError, QontoPaymentProvider


class _FakeResponse:
    """Minimal httpx.Response stand-in."""

    def __init__(self, payload: object = None, content: bytes = b"") -> None:
        self._payload = payload
        self.content = content
        self.status_code = 200

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class _FakeAsyncClient:
    """Fake httpx.AsyncClient routing on (method, path) and recording calls."""

    calls: ClassVar[list[dict]] = []
    routes: ClassVar[dict[tuple[str, str], object]] = {}

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def request(self, method: str, url: str, **kwargs: object) -> _FakeResponse:
        _FakeAsyncClient.calls.append({"method": method, "url": url, **kwargs})
        return self._resolve(method, url)

    async def get(self, url: str, **kwargs: object) -> _FakeResponse:
        _FakeAsyncClient.calls.append({"method": "GET", "url": url, **kwargs})
        if url.startswith("https://presigned"):
            return _FakeResponse(content=b"%PDF-1.4 fake")
        return self._resolve("GET", url)

    def _resolve(self, method: str, url: str) -> _FakeResponse:
        for (route_method, fragment), payload in _FakeAsyncClient.routes.items():
            if method == route_method and fragment in url:
                return _FakeResponse(payload=payload)
        raise AssertionError(f"No fake route for {method} {url}")


@pytest.fixture(autouse=True)
def _fake_httpx(monkeypatch: pytest.MonkeyPatch) -> None:
    """Route the provider's httpx through the fake client and skip real sleeps."""
    _FakeAsyncClient.calls = []
    _FakeAsyncClient.routes = {}
    monkeypatch.setattr(qonto_module.httpx, "AsyncClient", _FakeAsyncClient)

    async def _no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(qonto_module.asyncio, "sleep", _no_sleep)
    # The guard needs a sandbox runtime with a staging token.
    monkeypatch.setattr(settings, "qonto_environment", "sandbox")
    monkeypatch.setattr(settings, "qonto_staging_token", "stg_test")


def _provider(qonto_iban: str | None = "FR7616958000019712437314435") -> QontoPaymentProvider:
    account = SimpleNamespace(environment="sandbox", qonto_iban=qonto_iban)
    return QontoPaymentProvider(account, access_token="tok_test")


def _last_call(method: str, fragment: str) -> dict:
    for call in reversed(_FakeAsyncClient.calls):
        if call["method"] == method and fragment in call["url"]:
            return call
    raise AssertionError(f"No recorded {method} call matching {fragment}")


def test_guard_refuses_env_mismatch() -> None:
    """A production account on a sandbox runtime is refused."""
    account = SimpleNamespace(environment="production", qonto_iban="FR76")
    with pytest.raises(QontoEnvironmentError):
        QontoPaymentProvider(account, access_token="tok")


def test_authorized_headers_carry_staging_token() -> None:
    """Sandbox requests carry the staging-token header."""
    headers = _provider()._authorized_headers()
    assert headers["Authorization"] == "Bearer tok_test"
    assert headers["X-Qonto-Staging-Token"] == "stg_test"


def test_ensure_client_reuses_existing_by_email() -> None:
    """An existing client (matched by email) is reused, no client is created."""
    _FakeAsyncClient.routes = {
        ("GET", "/clients"): {"clients": [{"id": "cli_existing"}]},
        ("PATCH", "/clients/cli_existing"): {"client": {"id": "cli_existing"}},
    }
    client = BillingClient(name="Plomberie Durand", email="durand@example.fr")
    result = asyncio.run(_provider().ensure_client(client))
    assert result == "cli_existing"
    assert not any(call["method"] == "POST" for call in _FakeAsyncClient.calls)


def test_ensure_client_patches_existing_with_reviewed_details() -> None:
    """A match is refreshed: Qonto refuses to invoice a client whose TIN is missing."""
    _FakeAsyncClient.routes = {
        ("GET", "/clients"): {"clients": [{"id": "cli_existing"}]},
        ("PATCH", "/clients/cli_existing"): {"client": {"id": "cli_existing"}},
    }
    client = BillingClient(
        name="Plomberie Durand",
        email="durand@example.fr",
        address="1 rue des Lilas",
        city="Lyon",
        zip_code="69001",
        tax_id="123456789",
    )
    asyncio.run(_provider().ensure_client(client))
    body = _last_call("PATCH", "/clients/cli_existing")["json"]
    assert body["tax_identification_number"] == "123456789"
    assert body["billing_address"]["city"] == "Lyon"


def test_ensure_client_creates_when_absent() -> None:
    """No match → a company client is created with a flat billing address."""
    _FakeAsyncClient.routes = {
        ("GET", "/clients"): {"clients": []},
        ("POST", "/clients"): {"client": {"id": "cli_new"}},
    }
    client = BillingClient(
        name="Plomberie Durand",
        email="durand@example.fr",
        address="1 rue des Lilas",
        city="Lyon",
        zip_code="69001",
        country_code="FR",
    )
    result = asyncio.run(_provider().ensure_client(client))
    assert result == "cli_new"
    body = _last_call("POST", "/clients")["json"]
    assert body["kind"] == "company"
    assert body["name"] == "Plomberie Durand"
    assert body["billing_address"] == {
        "street_address": "1 rue des Lilas",
        "city": "Lyon",
        "zip_code": "69001",
        "country_code": "FR",
    }


def test_create_invoice_builds_finalized_body_and_parses_result() -> None:
    """The invoice is finalized (unpaid), carries the account IBAN and the amount."""
    _FakeAsyncClient.routes = {
        ("POST", "/client_invoices"): {
            "client_invoice": {
                "id": "inv_1",
                "number": "F-2026-006",
                "status": "unpaid",
                "invoice_url": "https://pay.qonto.com/invoices/inv_1",
            }
        },
        ("POST", "/payment_links"): {"payment_link": {"id": "pl_1"}},
    }
    request = InvoiceRequest(client=BillingClient(name="X"), amount_cents=50000, currency="eur", label="Site web")
    issued = asyncio.run(_provider().create_invoice("cli_1", request))

    assert issued.invoice_id == "inv_1"
    assert issued.invoice_number == "F-2026-006"
    assert issued.payment_url == "https://pay.qonto.com/invoices/inv_1"
    assert issued.provider == "qonto"
    assert issued.payment_link_id == "pl_1"

    body = _last_call("POST", "/client_invoices")["json"]
    assert body["status"] == "unpaid"
    assert body["payment_methods"] == {"iban": "FR7616958000019712437314435"}
    assert body["currency"] == "EUR"
    item = body["items"][0]
    assert item["unit_price"] == {"value": "500.00", "currency": "EUR"}
    assert item["vat_exemption_reason"] == "S293B"

    # The card link uses the invoice variant: nested body, amount and debtor included.
    link = _last_call("POST", "/payment_links")["json"]["payment_link"]
    assert link["invoice_id"] == "inv_1"
    assert link["invoice_number"] == "F-2026-006"
    assert link["amount"] == {"value": "500.00", "currency": "EUR"}
    assert link["potential_payment_methods"] == ["bank_transfer", "credit_card", "apple_pay"]


@pytest.mark.parametrize(
    ("country", "code", "mention_repeated"),
    [("FR", "S293B", False), ("BE", "S283", True), ("LU", "S283", True), ("CH", "S259", True)],
)
def test_create_invoice_vat_mention_follows_the_client_country(country: str, code: str, mention_repeated: bool) -> None:
    """Franchise en base in France, reverse charge in the EU, export of services outside it — always in euros."""
    _FakeAsyncClient.routes = {
        ("POST", "/client_invoices"): {"client_invoice": {"id": "inv_1", "number": "F-2026-007"}},
        ("POST", "/payment_links"): {"payment_link": {"id": "pl_1"}},
    }
    client = BillingClient(name="Paysagement Tremblay", country_code=country)
    request = InvoiceRequest(client=client, amount_cents=50000, currency="eur", label="Site web")
    asyncio.run(_provider().create_invoice("cli_1", request))

    body = _last_call("POST", "/client_invoices")["json"]
    assert body["currency"] == "EUR"
    assert body["items"][0]["vat_rate"] == "0"
    assert body["items"][0]["vat_exemption_reason"] == code
    assert ("terms_and_conditions" in body) is mention_repeated


def test_vat_exemption_mentions_read_as_leo_writes_them() -> None:
    """The mention a foreign client reads names the regime in plain words."""
    exemption_for = QontoPaymentProvider.vat_exemption_for
    assert exemption_for("FR").mention == "TVA non applicable, art. 293 B du CGI"
    assert exemption_for("CH").mention.startswith("TVA non applicable, exportation hors UE")
    assert exemption_for("BE").mention.startswith("Autoliquidation, art. 196 directive TVA")
    assert exemption_for(None) == exemption_for("FR")


def test_create_invoice_requires_iban() -> None:
    """Without an IBAN the invoice can't be issued (Qonto requires it)."""
    request = InvoiceRequest(client=BillingClient(name="X"), amount_cents=50000, currency="eur", label="Site web")
    with pytest.raises(ValueError):
        asyncio.run(_provider(qonto_iban=None).create_invoice("cli_1", request))


def test_create_invoice_survives_card_link_failure() -> None:
    """The card payment link is best-effort — its failure never fails the sale."""
    _FakeAsyncClient.routes = {
        ("POST", "/client_invoices"): {
            "client_invoice": {
                "id": "inv_1",
                "number": "F-2026-006",
                "invoice_url": "https://pay.qonto.com/invoices/inv_1",
            }
        },
        # No /payment_links route → the call raises, must be swallowed.
    }
    request = InvoiceRequest(client=BillingClient(name="X"), amount_cents=50000, currency="eur", label="Site web")
    issued = asyncio.run(_provider().create_invoice("cli_1", request))
    assert issued.invoice_id == "inv_1"


def test_get_invoice_pdf_polls_then_downloads() -> None:
    """The PDF is fetched once its async attachment appears."""
    _FakeAsyncClient.routes = {
        ("GET", "/client_invoices/inv_1"): {"client_invoice": {"id": "inv_1", "attachment_id": "att_1"}},
        ("GET", "/attachments/att_1"): {"attachment": {"url": "https://presigned.example/inv_1.pdf"}},
    }
    pdf = asyncio.run(_provider().get_invoice_pdf("inv_1"))
    assert pdf == b"%PDF-1.4 fake"


def test_check_paid_maps_status() -> None:
    """A ``paid`` invoice status maps to is_paid=True."""
    _FakeAsyncClient.routes = {("GET", "/client_invoices/inv_1"): {"client_invoice": {"status": "paid"}}}
    state = asyncio.run(_provider().check_paid("inv_1"))
    assert state.is_paid is True
    assert state.raw_status == "paid"


def test_check_paid_reads_link_when_invoice_unpaid() -> None:
    """An unpaid invoice whose card/Apple Pay link is settling counts as paid."""
    _FakeAsyncClient.routes = {
        ("GET", "/client_invoices/inv_1"): {"client_invoice": {"status": "unpaid"}},
        ("GET", "/payment_links/pl_1"): {"payment_link": {"status": "processing"}},
    }
    state = asyncio.run(_provider().check_paid("inv_1", "pl_1"))
    assert state.is_paid is True
    assert state.raw_status == "link:processing"


def test_check_paid_stays_unpaid_when_link_is_open() -> None:
    """An unpaid invoice whose link nobody has paid stays unpaid."""
    _FakeAsyncClient.routes = {
        ("GET", "/client_invoices/inv_1"): {"client_invoice": {"status": "unpaid"}},
        ("GET", "/payment_links/pl_1"): {"payment_link": {"status": "open"}},
    }
    state = asyncio.run(_provider().check_paid("inv_1", "pl_1"))
    assert state.is_paid is False
    assert state.raw_status == "unpaid"


def test_check_paid_ignores_link_when_invoice_already_paid() -> None:
    """A paid invoice is authoritative — the link is never fetched (no route for it)."""
    _FakeAsyncClient.routes = {("GET", "/client_invoices/inv_1"): {"client_invoice": {"status": "paid"}}}
    state = asyncio.run(_provider().check_paid("inv_1", "pl_1"))
    assert state.is_paid is True
    assert state.raw_status == "paid"
