"""smsmode implementation of :class:`SmsProvider` (REST API v1).

Contract confirmed against a production integration:
``POST https://rest.smsmode.com/sms/v1/messages`` with an ``X-Api-Key`` header
and body ``{recipient:{to}, body:{text}, from, refClient?, callbackUrlStatus?}``;
the response carries ``messageId`` and, when priced, ``price.amount`` (euros).
"""

from __future__ import annotations

import logging

import httpx

from core.config import settings

from .sms_provider import SmsProvider, SmsSendResult

logger = logging.getLogger(__name__)


class SmsModeProvider(SmsProvider):
    """Send SMS through the smsmode REST v1 API (single platform account)."""

    def __init__(self) -> None:
        """Load the platform API key and base URLs from settings."""
        self._api_key: str = settings.smsmode_api_key
        self._base_url: str = settings.smsmode_base_url
        self._credit_url: str = settings.smsmode_credit_url

    @property
    def is_configured(self) -> bool:
        """Whether a smsmode API key is available.

        Returns:
            ``True`` when a non-empty key is configured.
        """
        return bool(self._api_key)

    async def get_credit_balance(self) -> float | None:
        """Read the smsmode account's remaining credit balance.

        Calls the smsmode HTTP API ``credit.do`` endpoint, which answers with the
        remaining credits as a bare number. The key is sent both as the REST
        ``X-Api-Key`` header (what our account uses) and as the legacy
        ``accessToken`` query param, so the same key works whichever the endpoint
        expects. Any transport, HTTP or parse error yields ``None`` — the balance
        is an admin convenience, never worth surfacing an exception for.

        Returns:
            The remaining credits, or ``None`` when unconfigured or unreadable.
        """
        if not self.is_configured:
            return None
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
                response = await client.get(
                    self._credit_url,
                    params={"accessToken": self._api_key},
                    headers={"X-Api-Key": self._api_key, "Accept": "text/plain"},
                )
        except httpx.HTTPError as exc:
            logger.error("[smsmode] transport error reading credit balance: %s", exc)
            return None
        if response.status_code >= 400:
            logger.error("[smsmode] %s reading credit balance: %s", response.status_code, response.text[:300])
            return None
        balance = self._parse_credit(response.text)
        if balance is None:
            logger.warning(
                "[smsmode] unreadable credit balance from %s (status %s): %r",
                self._credit_url,
                response.status_code,
                response.text[:200],
            )
        return balance

    @staticmethod
    def _parse_credit(raw: str) -> float | None:
        """Extract the credit number from a ``credit.do`` response.

        The endpoint returns a bare number (e.g. ``"123"`` or ``"123.5"``); some
        variants prefix a status as ``"code | value"``. We take the last token and
        read it as a float, tolerating a comma decimal separator.

        Args:
            raw: The raw response body.

        Returns:
            The parsed balance, or ``None`` when no number can be read.
        """
        token = raw.strip().split("|")[-1].strip().replace(",", ".")
        try:
            return float(token)
        except ValueError:
            return None

    async def send(
        self,
        *,
        to_e164: str,
        sender: str,
        text: str,
        ref_client: str | None = None,
        callback_url: str | None = None,
        callback_url_mo: str | None = None,
    ) -> SmsSendResult:
        """Send one SMS through smsmode.

        Args:
            to_e164: Recipient in E.164 format.
            sender: Alphanumeric sender id.
            text: Message body.
            ref_client: Reference echoed back on the callbacks.
            callback_url: Delivery-receipt (DLR) callback URL.
            callback_url_mo: Incoming-message (MO / STOP opt-out) callback URL.

        Returns:
            The send outcome, ``success=False`` on any transport or API error.
        """
        if not self.is_configured:
            return SmsSendResult(success=False, error="smsmode non configuré (SMSMODE_API_KEY absent)")

        payload: dict[str, object] = {
            "recipient": {"to": to_e164},
            "body": {"text": text},
            "from": sender,
        }
        if ref_client:
            payload["refClient"] = ref_client
        if callback_url:
            payload["callbackUrlStatus"] = callback_url
        if callback_url_mo:
            payload["callbackUrlMo"] = callback_url_mo

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                response = await client.post(
                    self._base_url,
                    json=payload,
                    headers={"X-Api-Key": self._api_key, "Accept": "application/json"},
                )
        except httpx.HTTPError as exc:
            logger.error("[smsmode] transport error sending to %s: %s", to_e164, exc)
            return SmsSendResult(success=False, error=str(exc))

        if response.status_code >= 400:
            logger.error("[smsmode] %s sending to %s: %s", response.status_code, to_e164, response.text[:500])
            return SmsSendResult(success=False, error=self._extract_error(response))

        try:
            data = response.json()
        except ValueError:
            return SmsSendResult(success=False, error="Réponse smsmode illisible")

        message_id = str(data.get("messageId") or "").strip()
        if not message_id:
            logger.warning("[smsmode] response without messageId for %s: %s", to_e164, response.text[:300])
            return SmsSendResult(success=False, error="Réponse smsmode sans messageId")

        price = data.get("price") if isinstance(data.get("price"), dict) else None
        price_cents: int | None = None
        if price is not None:
            try:
                price_cents = round(float(price.get("amount", 0)) * 100)
            except (TypeError, ValueError):
                price_cents = None
        return SmsSendResult(success=True, provider_message_id=message_id, price_cents=price_cents)

    @staticmethod
    def _extract_error(response: httpx.Response) -> str:
        """Turn a smsmode 4xx/5xx body into a short human message.

        smsmode returns ``{title, message, detail, errorCode}``; we surface
        ``message`` (+ ``detail``) so the SMS log shows why it failed, not raw JSON.

        Args:
            response: The failed HTTP response.

        Returns:
            A readable one-line error.
        """
        try:
            body = response.json()
        except ValueError:
            body = None
        if isinstance(body, dict):
            message = str(body.get("message") or body.get("title") or "").strip()
            detail = str(body.get("detail") or "").strip()
            if message and detail:
                return f"{message} — {detail}"
            if message:
                return message
        return f"Erreur smsmode ({response.status_code})"


smsmode_provider = SmsModeProvider()
