"""Qonto implementation of the encashment contract.

Real Business API calls (httpx) against the base host in ``settings``, with the
environment guard and staging-token header kept from the socle. The client is
found-or-created, the invoice is finalized (``status: unpaid``) so Qonto owns
its number, and the PDF is fetched after Qonto has generated it (async, ~10s).

Qonto is Léo's account only, so the VAT block is his franchise-en-base regime:
rate 0 everywhere, and an exemption reason that follows the client's country —
``S293B`` (art. 293 B du CGI) for a French client, the reverse charge for a
business of another EU country, the export of services for a client outside the
EU. Every invoice stays in euros (the client's bank converts).
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import httpx

from core.config import settings
from enums.payment_provider import PaymentEnvironment, PaymentProvider
from models.payment_account import PaymentAccount
from services.country_profiles import CountryProfiles
from services.payment_providers.base import (
    BillingClient,
    InvoiceRequest,
    IssuedInvoice,
    PaymentProviderClient,
    PaymentState,
)

logger = logging.getLogger(__name__)

_INVOICE_DUE_DAYS = 30
# Offered on the invoice's pay page. Transfer is listed alongside the card methods
# so attaching a payment link adds ways to pay instead of replacing the transfer.
_PAYMENT_METHODS = ["bank_transfer", "credit_card", "apple_pay"]
# Payment-link statuses meaning the buyer has paid: "processing" = a card/Apple Pay
# payment cleared by the buyer but not yet settled by Mollie onto the invoice.
_PAID_LINK_STATUSES = frozenset({"paid", "processing"})
_VAT_RATE = "0"


@dataclass(frozen=True)
class VatExemption:
    """The VAT exemption of an invoice: Qonto's reason code and the mention the client reads.

    Qonto prints its own legal mention from the code; ``mention`` is repeated in the
    invoice notes only outside France, where the client does not know the French article.
    """

    code: str
    mention: str
    repeat_mention: bool


# Qonto's codes name articles of the French tax code: 293 B franchise en base, 283-2 reverse charge
# on an intra-EU B2B service, 259-1 a service to a business established outside the EU.
_VAT_EXEMPTION_FRANCE = VatExemption("S293B", "TVA non applicable, art. 293 B du CGI", repeat_mention=False)
_VAT_EXEMPTION_EU_BUSINESS = VatExemption(
    "S283", "Autoliquidation, art. 196 directive TVA (art. 283-2 du CGI)", repeat_mention=True
)
_VAT_EXEMPTION_EXPORT = VatExemption(
    "S259", "TVA non applicable, exportation hors UE (art. 259-1 du CGI)", repeat_mention=True
)


# The invoice PDF is generated asynchronously by Qonto — poll for its attachment.
_PDF_POLL_ATTEMPTS = 6
_PDF_POLL_DELAY_SECONDS = 3.0


class QontoEnvironmentError(RuntimeError):
    """Raised when the runtime and the stored credentials disagree on environment.

    Deliberately fatal: a silent fallback here is exactly the failure mode that
    would let a bug write into real accounting, so a mismatch stops the request.
    """


class QontoPaymentProvider(PaymentProviderClient):
    """Issues invoices and payment links through a user's Qonto organization."""

    provider = PaymentProvider.QONTO

    def __init__(
        self,
        account: PaymentAccount,
        access_token: str | None = None,
        *,
        api_credentials: tuple[str, str] | None = None,
    ) -> None:
        """
        Build the provider for a connected account, guarding the environment.

        Args:
            account: The user's connected Qonto account.
            access_token: A valid (refreshed if needed) OAuth access token.
            api_credentials: ``(login, secret)`` API-key pair — the admin-only
                fallback used when no OAuth tokens are stored.

        Raises:
            ValueError: When neither an access token nor API credentials are given.
            QontoEnvironmentError: If the runtime environment is inconsistent
                with itself or with the account's stored environment.
        """
        if not access_token and not api_credentials:
            raise ValueError("Qonto provider needs an OAuth access token or API-key credentials.")
        self._account = account
        self._access_token = access_token
        self._api_credentials = api_credentials
        self._assert_environment_consistent()

    def _assert_environment_consistent(self) -> None:
        """
        Fail loudly on any environment inconsistency before a call goes out.

        Raises:
            QontoEnvironmentError: On an unknown environment, a sandbox runtime
                with no staging token, or a runtime/account environment mismatch.
        """
        runtime = settings.qonto_environment
        valid = {environment.value for environment in PaymentEnvironment}
        if runtime not in valid:
            raise QontoEnvironmentError(f"QONTO_ENVIRONMENT is '{runtime}', expected one of {sorted(valid)}.")
        if runtime == PaymentEnvironment.SANDBOX.value and not settings.qonto_staging_token:
            raise QontoEnvironmentError("Sandbox runtime without QONTO_STAGING_TOKEN — refusing to call Qonto.")
        if self._account.environment != runtime:
            raise QontoEnvironmentError(
                f"Account credentials belong to '{self._account.environment}' but the runtime is '{runtime}'."
            )

    def _authorized_headers(self) -> dict[str, str]:
        """
        Build the request headers, adding the staging-token header in sandbox.

        Returns:
            Headers carrying the OAuth bearer token — or the ``login:secret``
            API-key form Qonto expects — plus ``X-Qonto-Staging-Token`` in sandbox.
        """
        if self._access_token:
            authorization = f"Bearer {self._access_token}"
        else:
            login, secret = self._api_credentials or ("", "")
            authorization = f"{login}:{secret}"
        headers = {"Authorization": authorization}
        if settings.qonto_environment == PaymentEnvironment.SANDBOX.value:
            headers["X-Qonto-Staging-Token"] = settings.qonto_staging_token
        return headers

    async def _request(self, method: str, path: str, *, params: dict | None = None, json: dict | None = None) -> dict:
        """
        Call the Qonto Business API and return the parsed JSON body.

        Args:
            method: HTTP verb.
            path: Path under ``/v2`` (e.g. ``/clients``).
            params: Optional query parameters.
            json: Optional JSON request body.

        Returns:
            The parsed response body.

        Raises:
            Exception: With the response text when the call fails.
        """
        url = f"{settings.qonto_api_base_url}/v2{path}"
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method, url, headers=self._authorized_headers(), params=params, json=json, timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as error:
            logger.error("Qonto API %s %s failed: %s", method, path, error.response.text)
            raise Exception(f"Qonto API error ({error.response.status_code}): {error.response.text}")

    async def ensure_client(self, client: BillingClient) -> str:
        """
        Find a Qonto client by email and refresh it, or create one, returning its id.

        A match is patched with the reviewed details rather than reused as-is:
        Qonto refuses to invoice a client whose TIN is missing, and the documented
        fix is to update the client and retry — otherwise a counterpart created
        before the operator filled the SIREN in would fail the sale forever.

        Args:
            client: The billing counterpart details.

        Returns:
            The Qonto client id.
        """
        body = self._client_body(client)
        if client.email:
            found = await self._request("GET", "/clients", params={"filter[email]": client.email})
            existing = found.get("clients") or []
            if existing:
                client_id = existing[0]["id"]
                await self._request("PATCH", f"/clients/{client_id}", json=body)
                return client_id

        created = await self._request("POST", "/clients", json=body)
        return created["client"]["id"]

    def _client_body(self, client: BillingClient) -> dict:
        """
        Build the Qonto client payload, dropping the parts we don't have.

        Args:
            client: The billing counterpart details.

        Returns:
            The request body shared by client creation and update.
        """
        body: dict = {"kind": "company", "name": client.name, "currency": "EUR", "locale": "FR"}
        if client.email:
            body["email"] = client.email
        address = {
            key: value
            for key, value in {
                "street_address": client.address,
                "city": client.city,
                "zip_code": client.zip_code,
                "country_code": client.country_code,
            }.items()
            if value
        }
        if address:
            body["billing_address"] = address
        if client.tax_id:
            body["tax_identification_number"] = client.tax_id
        if client.vat_number:
            body["vat_number"] = client.vat_number
        return body

    async def create_invoice(self, client_id: str, request: InvoiceRequest) -> IssuedInvoice:
        """
        Issue a finalized Qonto invoice and return its artifacts.

        Args:
            client_id: Qonto client id from :meth:`ensure_client`.
            request: The invoice details.

        Returns:
            The issued invoice (``payment_url`` is the transfer-payable Qonto page;
            a card button is added best-effort when the payment-links provider is on).

        Raises:
            ValueError: When no IBAN is configured for the account.
        """
        if not self._account.qonto_iban:
            raise ValueError("Configurez l'IBAN Qonto dans les réglages avant d'émettre une facture.")

        today = datetime.now(UTC).date()
        currency = (request.currency or "EUR").upper()
        exemption = self.vat_exemption_for(request.client.country_code)
        body = {
            "client_id": client_id,
            "issue_date": today.isoformat(),
            "due_date": (today + timedelta(days=_INVOICE_DUE_DAYS)).isoformat(),
            "currency": currency,
            "status": "unpaid",
            "payment_methods": {"iban": self._account.qonto_iban},
            "items": [
                {
                    "title": request.label,
                    "description": request.description or request.label,
                    "quantity": "1",
                    "unit": "unit",
                    "unit_price": {"value": f"{request.amount_cents / 100:.2f}", "currency": currency},
                    "vat_rate": _VAT_RATE,
                    "vat_exemption_reason": exemption.code,
                }
            ],
        }
        if exemption.repeat_mention:
            body["terms_and_conditions"] = exemption.mention
        invoice = (await self._request("POST", "/client_invoices", json=body))["client_invoice"]
        payment_link_id = await self._enable_card_payment(invoice, request)
        return IssuedInvoice(
            provider=self.provider.value,
            invoice_id=invoice["id"],
            invoice_number=invoice.get("number"),
            payment_url=invoice.get("invoice_url"),
            payment_link_id=payment_link_id,
        )

    @staticmethod
    def vat_exemption_for(country_code: str | None) -> VatExemption:
        """The VAT exemption to put on an invoice billed to a client of ``country_code``.

        Args:
            country_code: ISO code of the client's billing country (``None`` reads as France).

        Returns:
            The exemption code and mention for that country.
        """
        country = CountryProfiles.get(country_code)
        if country.code == "FR":
            return _VAT_EXEMPTION_FRANCE
        return _VAT_EXEMPTION_EU_BUSINESS if country.in_european_union else _VAT_EXEMPTION_EXPORT

    async def _enable_card_payment(self, invoice: dict, request: InvoiceRequest) -> str | None:
        """
        Best-effort: attach a card payment link to the invoice's pay page.

        The invoice is transfer-payable without this; a card button only appears
        when the user's payment-links provider is connected, so a failure here is
        logged and swallowed rather than failing the sale.

        Args:
            invoice: The issued invoice as returned by Qonto.
            request: The invoice details (amount and debtor of the link).

        Returns:
            The created payment link's id, or None when none could be attached.
        """
        currency = (request.currency or "EUR").upper()
        body = {
            "payment_link": {
                "invoice_id": invoice["id"],
                "invoice_number": invoice.get("number"),
                "amount": {"value": f"{request.amount_cents / 100:.2f}", "currency": currency},
                "debitor_name": request.client.name,
                "potential_payment_methods": _PAYMENT_METHODS,
            }
        }
        try:
            created = await self._request("POST", "/payment_links", json=body)
        except Exception:
            logger.info("Qonto card payment link not created for invoice %s — transfer only.", invoice["id"])
            return None
        return (created.get("payment_link") or {}).get("id")

    async def get_invoice_pdf(self, invoice_id: str) -> bytes:
        """
        Fetch the invoice PDF bytes once Qonto has generated it.

        Args:
            invoice_id: The Qonto invoice id.

        Returns:
            The raw PDF bytes.

        Raises:
            RuntimeError: When the PDF is still not ready after polling.
        """
        attachment_id = await self._await_attachment_id(invoice_id)
        attachment = (await self._request("GET", f"/attachments/{attachment_id}"))["attachment"]
        async with httpx.AsyncClient() as client:
            response = await client.get(attachment["url"], timeout=60.0)
            response.raise_for_status()
            return response.content

    async def _await_attachment_id(self, invoice_id: str) -> str:
        """
        Poll the invoice until its (asynchronously generated) PDF attachment exists.

        Args:
            invoice_id: The Qonto invoice id.

        Returns:
            The attachment id of the generated PDF.

        Raises:
            RuntimeError: When no attachment appears within the poll budget.
        """
        for attempt in range(_PDF_POLL_ATTEMPTS):
            invoice = (await self._request("GET", f"/client_invoices/{invoice_id}"))["client_invoice"]
            attachment_id = invoice.get("attachment_id")
            if attachment_id:
                return attachment_id
            if attempt < _PDF_POLL_ATTEMPTS - 1:
                await asyncio.sleep(_PDF_POLL_DELAY_SECONDS)
        raise RuntimeError(f"Qonto invoice {invoice_id} PDF not ready after {_PDF_POLL_ATTEMPTS} attempts.")

    async def check_paid(self, invoice_id: str, payment_link_id: str | None = None) -> PaymentState:
        """
        Read the payment status, treating a buyer-paid card/Apple Pay link as paid.

        A card/Apple Pay payment only flips the invoice to "paid" once Mollie settles
        it (up to ~2 weeks for a first payout), so the buyer would otherwise wait for
        delivery. When the invoice is still unpaid the attached payment link is read:
        a "processing" (buyer paid, settling) or "paid" link means it's paid. Bank
        transfers settle straight onto the invoice, so they never need this.

        Args:
            invoice_id: The Qonto invoice id.
            payment_link_id: The attached payment link id, when one was created.

        Returns:
            The normalized payment state.
        """
        invoice = (await self._request("GET", f"/client_invoices/{invoice_id}"))["client_invoice"]
        status = invoice.get("status")
        if status == "paid":
            return PaymentState(is_paid=True, raw_status=status)
        if payment_link_id:
            link_status = await self._payment_link_status(payment_link_id)
            if link_status in _PAID_LINK_STATUSES:
                return PaymentState(is_paid=True, raw_status=f"link:{link_status}")
        return PaymentState(is_paid=False, raw_status=status)

    async def _payment_link_status(self, payment_link_id: str) -> str | None:
        """
        Read a payment link's status, returning None when it can't be fetched.

        Degrades gracefully: a lookup failure falls back to the invoice status
        (settlement) rather than breaking reconciliation.

        Args:
            payment_link_id: The Qonto payment link id.

        Returns:
            The link status, or None on failure.
        """
        try:
            response = await self._request("GET", f"/payment_links/{payment_link_id}")
        except Exception as error:
            logger.warning("Qonto payment link %s status unavailable: %s", payment_link_id, error)
            return None
        return (response.get("payment_link") or {}).get("status")
