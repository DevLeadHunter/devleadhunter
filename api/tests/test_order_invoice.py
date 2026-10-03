"""Unit tests for order invoice generation and the sale email.

The provider is faked (its live calls are covered by ``test_qonto_provider``);
here we assert the order plumbing: columns filled from the issued invoice, an
existing invoice reused (never re-issued — a finalized invoice burns a number),
and the email copy (no "Stripe", black button, generic payment URL).
"""

import asyncio
from decimal import Decimal
from types import SimpleNamespace

import pytest

from enums.order_status import OrderStatus
from enums.payment_provider import PaymentProvider
from models.order import Order
from services.order_service import OrderService, _format_business_name_for_display, _split_postal_address
from services.payment_providers.base import IssuedInvoice


class _FakeLockQuery:
    """No-op stand-in for the ``SELECT ... FOR UPDATE`` row lock chain."""

    def filter(self, *_conditions: object) -> "_FakeLockQuery":
        return self

    def with_for_update(self) -> "_FakeLockQuery":
        return self

    def first(self) -> None:
        return None


class _FakeDB:
    """No-op session: the service only calls query/commit/refresh on it."""

    def query(self, *_entities: object) -> _FakeLockQuery:
        return _FakeLockQuery()

    def commit(self) -> None:
        return None

    def refresh(self, _obj: object) -> None:
        return None


class _FakeProvider:
    """Records the invoice request and returns a canned issued invoice."""

    provider = PaymentProvider.QONTO

    def __init__(self) -> None:
        self.ensure_client_called_with: object = None
        self.create_invoice_called_with: object = None

    async def ensure_client(self, billing: object) -> str:
        self.ensure_client_called_with = billing
        return "cli_1"

    async def create_invoice(self, client_id: str, request: object) -> IssuedInvoice:
        self.create_invoice_called_with = request
        return IssuedInvoice(
            provider="qonto",
            invoice_id="inv_1",
            invoice_number="F-2026-006",
            payment_url="https://pay.qonto.com/invoices/inv_1",
        )


def _order(**overrides: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "id": 7,
        "user_id": 1,
        "product_type": "website",
        "business_name": "Plomberie Durand",
        "customer_name": None,
        "customer_email": "durand@example.fr",
        "amount_cents": 50000,
        "currency": "eur",
        "status": OrderStatus.DRAFT.value,
        "invoice_id": None,
        "invoice_number": None,
        "payment_link_id": None,
        "payment_provider": None,
        "payment_url": None,
        "stripe_payment_url": None,
        "prospect_id": None,
        "billing_address": "12 rue de la Paix",
        "billing_city": "Paris",
        "billing_zip_code": "75002",
        "billing_country_code": "FR",
        "billing_tax_id": None,
        "billing_vat_number": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_ensure_invoice_fills_columns_from_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """A connected provider issues the invoice and its artifacts land on the order."""
    service = OrderService()
    provider = _FakeProvider()

    async def _fake_resolve(_db: object, _user: object) -> _FakeProvider:
        return provider

    monkeypatch.setattr(service, "_resolve_provider", _fake_resolve)
    order = _order()
    result = asyncio.run(service.ensure_invoice(_FakeDB(), SimpleNamespace(id=1), order))

    assert result.payment_provider == "qonto"
    assert result.invoice_id == "inv_1"
    assert result.invoice_number == "F-2026-006"
    assert result.payment_url == "https://pay.qonto.com/invoices/inv_1"
    assert result.status == OrderStatus.PAYMENT_PENDING.value
    # The line item carries the business name and the order amount.
    assert provider.create_invoice_called_with.amount_cents == 50000
    assert "Plomberie Durand" in provider.create_invoice_called_with.label


def test_ensure_invoice_bills_the_reviewed_address(monkeypatch: pytest.MonkeyPatch) -> None:
    """The address stored on the order reaches the provider (Qonto rejects invoices without one)."""
    service = OrderService()
    provider = _FakeProvider()

    async def _fake_resolve(_db: object, _user: object) -> _FakeProvider:
        return provider

    monkeypatch.setattr(service, "_resolve_provider", _fake_resolve)
    asyncio.run(service.ensure_invoice(_FakeDB(), SimpleNamespace(id=1), _order()))

    counterpart = provider.ensure_client_called_with
    assert counterpart.address == "12 rue de la Paix"
    assert counterpart.zip_code == "75002"
    assert counterpart.city == "Paris"
    assert counterpart.country_code == "FR"


class _SettingsDB(_FakeDB):
    """Fake session returning canned credit settings for the commission maths."""

    def __init__(self, settings: object) -> None:
        self._settings = settings

    def query(self, _model: object) -> "_SettingsDB":
        return self

    def filter(self, *_args: object) -> "_SettingsDB":
        return self

    def first(self) -> object:
        return self._settings


def _commission(percent: str, fixed_cents: int, amount_cents: int) -> int | None:
    settings = SimpleNamespace(
        platform_commission_percent=Decimal(percent), platform_commission_fixed_cents=fixed_cents
    )
    return OrderService().platform_commission_cents(_SettingsDB(settings), amount_cents)


def test_platform_commission_adds_the_percentage_and_the_fixed_part() -> None:
    """10 % + 1 € on a 10 € sale is 2 € — the fixed part is what makes it worth invoicing."""
    assert _commission("10", 100, 1000) == 200
    assert _commission("10", 100, 50000) == 5100


def test_platform_commission_is_none_when_nothing_is_configured() -> None:
    """Both terms at zero means no application fee at all."""
    assert _commission("0", 0, 50000) is None


def test_platform_commission_never_exceeds_the_sale() -> None:
    """Stripe rejects an application fee larger than the amount charged."""
    assert _commission("0", 500, 300) == 300


def test_stripe_invoice_carries_the_platform_commission(monkeypatch: pytest.MonkeyPatch) -> None:
    """A configured rate becomes the Stripe application fee, in cents."""
    service = OrderService()
    provider = _FakeProvider()
    provider.provider = PaymentProvider.STRIPE

    async def _fake_resolve(_db: object, _user: object) -> _FakeProvider:
        return provider

    monkeypatch.setattr(service, "_resolve_provider", _fake_resolve)
    monkeypatch.setattr(service, "platform_commission_cents", lambda _db, amount: amount // 10)
    asyncio.run(service.ensure_invoice(_FakeDB(), SimpleNamespace(id=1), _order()))

    assert provider.create_invoice_called_with.application_fee_amount == 5000


def test_qonto_invoice_never_carries_a_commission(monkeypatch: pytest.MonkeyPatch) -> None:
    """Léo invoices his own clients through Qonto — the platform takes nothing."""
    service = OrderService()
    provider = _FakeProvider()
    provider.provider = PaymentProvider.QONTO

    async def _fake_resolve(_db: object, _user: object) -> _FakeProvider:
        return provider

    monkeypatch.setattr(service, "_resolve_provider", _fake_resolve)
    monkeypatch.setattr(service, "platform_commission_cents", lambda _db, _amount: 5000)
    asyncio.run(service.ensure_invoice(_FakeDB(), SimpleNamespace(id=1), _order()))

    assert provider.create_invoice_called_with.application_fee_amount is None


def test_finalize_sale_refuses_incomplete_billing(monkeypatch: pytest.MonkeyPatch) -> None:
    """An incomplete address stops the sale before an invoice number is burned."""
    service = OrderService()

    async def _must_not_run(_db: object, _user: object) -> None:
        raise AssertionError("the provider must not be called with incomplete billing")

    monkeypatch.setattr(service, "_resolve_provider", _must_not_run)
    monkeypatch.setattr(service, "connected_provider", lambda _db, _user: "qonto")
    billing = {"name": "Plomberie Durand", "email": "durand@example.fr", "address": "", "zip_code": "", "city": ""}

    with pytest.raises(ValueError, match="Facturation incomplète"):
        asyncio.run(service.finalize_sale(_FakeDB(), SimpleNamespace(id=1), _order(), billing, 50000))


def test_split_postal_address_extracts_zip_and_city() -> None:
    """A one-line scraped address is split into the parts the providers expect."""
    assert _split_postal_address("12 rue de la Paix, 75002 Paris", None) == ("12 rue de la Paix", "75002", "Paris")
    # A street number is not mistaken for a zip code, and the prospect's city wins.
    assert _split_postal_address("8 avenue des Ternes", "Paris") == ("8 avenue des Ternes", None, "Paris")


def test_split_postal_address_reads_the_prospect_country_shape() -> None:
    """Swiss and Belgian codes have four digits; the country written after the city is never taken for it."""
    assert _split_postal_address("Rue du Rhône 12, 1204 Genève", None, "CH") == ("Rue du Rhône 12", "1204", "Genève")
    assert _split_postal_address("Rue de la Loi 16, 1000 Bruxelles", None, "BE") == (
        "Rue de la Loi 16",
        "1000",
        "Bruxelles",
    )
    assert _split_postal_address("Rue du Rhône 12, 1204 Genève, Suisse", None, "CH") == (
        "Rue du Rhône 12",
        "1204",
        "Genève",
    )
    assert _split_postal_address("12 rue de la Paix, 75002 Paris, France", None) == (
        "12 rue de la Paix",
        "75002",
        "Paris",
    )
    # A four-digit code is not a French one: the address stays whole rather than inventing a zip.
    assert _split_postal_address("Rue du Rhône 12, 1204 Genève", "Genève", "FR") == (
        "Rue du Rhône 12, 1204 Genève",
        None,
        "Genève",
    )


def test_billing_details_pre_set_the_prospect_country() -> None:
    """A Swiss prospect opens the drawer on Switzerland, with its address split the Swiss way."""

    class _ProspectDB(_FakeDB):
        def query(self, *_entities: object) -> SimpleNamespace:
            prospect = SimpleNamespace(address="Rue du Rhône 12, 1204 Genève", city=None, country="CH")
            return SimpleNamespace(filter=lambda *_c: SimpleNamespace(first=lambda: prospect))

    order = _order(
        prospect_id=3, billing_address=None, billing_city=None, billing_zip_code=None, billing_country_code=None
    )
    details = OrderService().billing_details_for_order(_ProspectDB(), order)
    assert details["country_code"] == "CH"
    assert (details["address"], details["zip_code"], details["city"]) == ("Rue du Rhône 12", "1204", "Genève")


def test_missing_billing_fields_wants_no_tax_id_outside_france(monkeypatch: pytest.MonkeyPatch) -> None:
    """Qonto documents the TIN as optional: a Swiss client is invoiced without one, a French one is not."""
    service = OrderService()
    monkeypatch.setattr(service, "connected_provider", lambda _db, _user: "qonto")
    billing = {
        "name": "Paysagiste Favre",
        "email": "info@favre.ch",
        "address": "Rue du Rhône 12",
        "zip_code": "1204",
        "city": "Genève",
        "country_code": "CH",
    }
    assert service.missing_billing_fields(_FakeDB(), SimpleNamespace(id=1), billing) == []
    assert service.missing_billing_fields(_FakeDB(), SimpleNamespace(id=1), {**billing, "country_code": "FR"}) == [
        "le SIREN / SIRET"
    ]


def test_missing_billing_fields_lists_every_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every provider-required field missing is reported at once, not one by one."""
    service = OrderService()
    monkeypatch.setattr(service, "connected_provider", lambda _db, _user: "stripe")
    billing = {"name": "Durand", "email": "durand@example.fr"}
    assert service.missing_billing_fields(_FakeDB(), SimpleNamespace(id=1), billing) == [
        "l'adresse",
        "le code postal",
        "la ville",
    ]


def test_missing_billing_fields_requires_tax_id_on_qonto(monkeypatch: pytest.MonkeyPatch) -> None:
    """Qonto rejects an invoice whose client has no TIN, so the SIREN is required."""
    service = OrderService()
    monkeypatch.setattr(service, "connected_provider", lambda _db, _user: "qonto")
    billing = {
        "name": "Durand",
        "email": "durand@example.fr",
        "address": "12 rue de la Paix",
        "zip_code": "75002",
        "city": "Paris",
    }
    assert service.missing_billing_fields(_FakeDB(), SimpleNamespace(id=1), billing) == ["le SIREN / SIRET"]


def test_missing_billing_fields_skips_address_without_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """A fully manual sale (cash, transfer) is not blocked on a postal address."""
    service = OrderService()
    monkeypatch.setattr(service, "connected_provider", lambda _db, _user: None)
    billing = {"name": "Durand", "email": "durand@example.fr"}
    assert service.missing_billing_fields(_FakeDB(), SimpleNamespace(id=1), billing) == []


def test_ensure_invoice_reuses_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    """An order that already has an invoice is never re-issued."""
    service = OrderService()

    async def _must_not_run(_db: object, _user: object) -> None:
        raise AssertionError("provider must not be resolved when an invoice already exists")

    monkeypatch.setattr(service, "_resolve_provider", _must_not_run)
    order = _order(invoice_id="inv_existing", invoice_number="F-2026-005")
    result = asyncio.run(service.ensure_invoice(_FakeDB(), SimpleNamespace(id=1), order))
    assert result.invoice_id == "inv_existing"


def test_build_payment_email_has_no_stripe_black_button_and_generic_url() -> None:
    """The sale email drops the Stripe mention, uses a black button and the generic URL."""
    order = _order(invoice_id="inv_1", payment_url="https://pay.qonto.com/invoices/inv_1")
    rendered = OrderService().build_payment_email(order, sender_name="Léo")

    body = rendered["body_html"]
    assert "Stripe" not in body
    assert "#111111" in body
    assert "https://pay.qonto.com/invoices/inv_1" in body
    assert "pièce jointe" in body  # an invoice exists → the attachment is announced
    # No centred block: a one-to-one email, not a campaign.
    assert "text-align:center" not in body
    # Card and 3D Secure are only true once the payment-links provider is connected.
    assert "3D Secure" not in body


def test_build_payment_email_names_the_invoice_and_repeats_the_url() -> None:
    """The button names the invoice, and the raw link survives a stripped button."""
    order = _order(invoice_id="inv_1", invoice_number="F-2026-006", payment_url="https://pay.qonto.com/invoices/inv_1")
    body = OrderService().build_payment_email(order, sender_name="Léo")["body_html"]

    assert "Régler la facture F-2026-006" in body
    assert "Si le bouton ne s'ouvre pas" in body
    assert body.count("https://pay.qonto.com/invoices/inv_1") >= 2


def test_build_payment_email_falls_back_to_a_neutral_action_without_an_invoice() -> None:
    """With no invoice number to name, the button stays generic rather than lying."""
    order = _order(payment_url="https://buy.stripe.com/x")
    body = OrderService().build_payment_email(order, sender_name="Léo")["body_html"]
    assert "Procéder au paiement" in body


def test_build_payment_email_omits_attachment_note_without_invoice() -> None:
    """Without an issued invoice, the email doesn't promise an attachment."""
    order = _order(payment_url="https://buy.stripe.com/x")
    body = OrderService().build_payment_email(order, sender_name="Léo")["body_html"]
    assert "pièce jointe" not in body


def test_build_payment_email_softens_a_shouted_business_name() -> None:
    """A full-caps registry name is re-cased and the product label reads mid-sentence."""
    order = _order(business_name="PLOMBERIE DURAND", invoice_id="inv_1")
    rendered = OrderService().build_payment_email(order, sender_name="Léo")

    assert "Votre site web est prêt" in rendered["subject"]
    assert "le <strong>site web</strong> de <strong>Plomberie Durand</strong>" in rendered["body_html"]
    assert "PLOMBERIE DURAND" not in rendered["body_html"]


def test_format_business_name_for_display_recases_only_shouted_names() -> None:
    """Full-caps names get title case with lowercase linking words; clean names are kept."""
    assert _format_business_name_for_display("GARAGE DE LA GARE") == "Garage de la Gare"
    assert _format_business_name_for_display("L'Atelier du Bois") == "L'Atelier du Bois"


def test_check_and_mark_paid_marks_when_provider_reports_paid(monkeypatch: pytest.MonkeyPatch) -> None:
    """A provider-confirmed payment transitions the order to paid."""
    service = OrderService()
    order = _order(invoice_id="inv_1", payment_provider="qonto", paid_at=None)

    async def _fake_resolve(_db: object, _user: object) -> SimpleNamespace:
        async def _check_paid(_invoice_id: str, _payment_link_id: str | None = None) -> SimpleNamespace:
            return SimpleNamespace(is_paid=True, raw_status="paid")

        return SimpleNamespace(check_paid=_check_paid)

    marked: dict[str, bool] = {"done": False}

    def _fake_mark_paid(_db: object, target: SimpleNamespace) -> SimpleNamespace:
        marked["done"] = True
        target.paid_at = "now"
        return target

    monkeypatch.setattr(service, "_resolve_provider", _fake_resolve)
    monkeypatch.setattr(service, "mark_paid", _fake_mark_paid)
    assert asyncio.run(service.check_and_mark_paid(_FakeDB(), SimpleNamespace(id=1), order)) is True
    assert marked["done"] is True


def test_check_and_mark_paid_noop_when_unpaid(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unpaid invoice leaves the order untouched."""
    service = OrderService()
    order = _order(invoice_id="inv_1", payment_provider="qonto", paid_at=None)

    async def _fake_resolve(_db: object, _user: object) -> SimpleNamespace:
        async def _check_paid(_invoice_id: str, _payment_link_id: str | None = None) -> SimpleNamespace:
            return SimpleNamespace(is_paid=False, raw_status="unpaid")

        return SimpleNamespace(check_paid=_check_paid)

    monkeypatch.setattr(service, "_resolve_provider", _fake_resolve)
    assert asyncio.run(service.check_and_mark_paid(_FakeDB(), SimpleNamespace(id=1), order)) is False


class _ReconcileQuery:
    """Returns canned rows for the reconciliation queries (orders via all, user via first)."""

    def __init__(self, rows: list, one: object) -> None:
        self._rows = rows
        self._one = one

    def filter(self, *_conditions: object) -> "_ReconcileQuery":
        return self

    def all(self) -> list:
        return self._rows

    def first(self) -> object:
        return self._one


class _ReconcileDB:
    """Serves the pending orders for an Order query and the owner for a User query."""

    def __init__(self, orders: list, user: object) -> None:
        self._orders = orders
        self._user = user

    def query(self, entity: object) -> _ReconcileQuery:
        if entity is Order:
            return _ReconcileQuery(self._orders, None)
        return _ReconcileQuery([], self._user)


def test_reconcile_pending_orders_returns_newly_paid_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """The pass marks paid only the orders whose provider confirms payment."""
    service = OrderService()
    paid = _order(id=1, user_id=9, invoice_id="inv_1", payment_provider="stripe", paid_at=None)
    unpaid = _order(id=2, user_id=9, invoice_id="inv_2", payment_provider="stripe", paid_at=None)
    db = _ReconcileDB([paid, unpaid], SimpleNamespace(id=9))

    async def _fake_check(_db: object, _user: object, order: SimpleNamespace) -> bool:
        return order.id == 1

    monkeypatch.setattr(service, "check_and_mark_paid", _fake_check)
    assert asyncio.run(service.reconcile_pending_orders(db)) == [1]


def test_refund_order_refunds_via_provider_and_marks(monkeypatch: pytest.MonkeyPatch) -> None:
    """A paid order is refunded through its provider, then marked refunded."""
    service = OrderService()
    order = _order(invoice_id="inv_1", payment_provider="stripe", paid_at="now", status="paid")
    refunded: dict[str, bool] = {"provider": False}

    async def _fake_resolve(_db: object, _user: object) -> SimpleNamespace:
        async def _refund(_invoice_id: str) -> None:
            refunded["provider"] = True

        return SimpleNamespace(refund=_refund)

    def _fake_mark_refunded(_db: object, target: SimpleNamespace) -> SimpleNamespace:
        target.status = "refunded"
        return target

    monkeypatch.setattr(service, "_resolve_provider", _fake_resolve)
    monkeypatch.setattr(service, "mark_refunded", _fake_mark_refunded)
    result = asyncio.run(service.refund_order(_FakeDB(), SimpleNamespace(id=1), order))
    assert refunded["provider"] is True
    assert result.status == "refunded"


def test_refund_order_rejects_unpaid() -> None:
    """An unpaid order has nothing to refund."""
    order = _order(invoice_id="inv_1", payment_provider="stripe", paid_at=None, status="payment_pending")
    with pytest.raises(ValueError):
        asyncio.run(OrderService().refund_order(_FakeDB(), SimpleNamespace(id=1), order))
