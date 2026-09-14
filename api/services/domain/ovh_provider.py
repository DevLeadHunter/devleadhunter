"""OVH registrar provider — buy a ``.fr`` and point its DNS at the Vercel demo-host.

The account owner is the operator (Léo): the domain is bought on his OVH account, so the
registrant/contact defaults come from that account and no per-client legal data is needed.

Credentials come from the ``OVH_*`` settings. When they are absent the provider is **inert**
(:pyattr:`is_configured` is ``False``): callers skip the purchase and the manual domain flow
stays. This is the first-touch-with-real-money piece, so it is exercised behind an explicit
operator action, never silently on a webhook, until it has been validated on a real order.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Any

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 30.0


class DomainProviderError(RuntimeError):
    """A registrar call failed — carries a human message for the operator."""


class OvhDomainProvider:
    """Register a ``.fr`` and set its apex DNS via the OVH API (signed requests)."""

    def __init__(self) -> None:
        self._endpoint = settings.ovh_endpoint.rstrip("/")
        self._app_key = settings.ovh_application_key
        self._app_secret = settings.ovh_application_secret
        self._consumer_key = settings.ovh_consumer_key
        self._subsidiary = settings.ovh_subsidiary
        self._time_delta: int | None = None  # OVH server time minus local time, resolved once

    @property
    def is_configured(self) -> bool:
        """True when all three OVH credentials are present."""
        return bool(self._app_key and self._app_secret and self._consumer_key)

    def _sign(self, method: str, url: str, body: str, timestamp: int) -> str:
        """Build the ``X-Ovh-Signature`` for a request (SHA1 of the OVH-ordered fields)."""
        # SHA1 is mandated by the OVH signature scheme — not a security choice on our side.
        to_sign = "+".join([self._app_secret or "", self._consumer_key or "", method, url, body, str(timestamp)])
        return "$1$" + hashlib.sha1(to_sign.encode("utf-8")).hexdigest()

    async def _timestamp(self, client: httpx.AsyncClient) -> int:
        """Current time aligned to the OVH server clock (drift breaks the signature)."""
        if self._time_delta is None:
            response = await client.get(f"{self._endpoint}/auth/time")
            response.raise_for_status()
            self._time_delta = int(response.text) - int(time.time())
        return int(time.time()) + self._time_delta

    async def _request(self, client: httpx.AsyncClient, method: str, path: str, body: dict[str, Any] | None = None):
        """Perform one signed OVH API call and return the parsed JSON (or ``None``)."""
        url = f"{self._endpoint}{path}"
        body_str = json.dumps(body) if body is not None else ""
        timestamp = await self._timestamp(client)
        headers = {
            "X-Ovh-Application": self._app_key or "",
            "X-Ovh-Consumer": self._consumer_key or "",
            "X-Ovh-Timestamp": str(timestamp),
            "X-Ovh-Signature": self._sign(method, url, body_str, timestamp),
            "Content-Type": "application/json",
        }
        response = await client.request(method, url, headers=headers, content=body_str or None)
        if response.status_code >= 400:
            raise DomainProviderError(f"OVH {method} {path} → {response.status_code}: {response.text[:300]}")
        return response.json() if response.content else None

    async def account_id(self) -> str | None:
        """The OVH account id (nichandle) behind the credentials — a free, no-spend auth check.

        Returns:
            The nichandle when the signed call succeeds, else ``None`` (unconfigured or auth failed).
        """
        if not self.is_configured:
            return None
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                me = await self._request(client, "GET", "/me")
        except (httpx.HTTPError, DomainProviderError) as exc:
            logger.warning("OVH auth check failed: %s", exc)
            return None
        return (me or {}).get("nichandle")

    async def register(self, domain: str, *, duration: str = "P1Y") -> dict[str, Any]:
        """Buy a domain on the operator's OVH account (cart → configure → checkout, auto-paid).

        Args:
            domain: The full domain to register (e.g. ``"tacos-maru.fr"``).
            duration: ISO-8601 registration period (default one year).

        Returns:
            The OVH order payload (contains ``orderId`` / ``url``).

        Raises:
            DomainProviderError: When the provider is not configured or any OVH step fails.
        """
        if not self.is_configured:
            raise DomainProviderError("OVH n'est pas configuré (clés API manquantes)")
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                cart = await self._request(client, "POST", "/order/cart", {"ovhSubsidiary": self._subsidiary})
                cart_id = cart["cartId"]
                await self._request(client, "POST", f"/order/cart/{cart_id}/assign")

                offers = await self._request(client, "GET", f"/order/cart/{cart_id}/domain?domain={domain}")
                logger.info("OVH cart offers for %s: %s", domain, offers)
                offer = self._pick_create_offer(offers, domain)
                # `duration` must be ISO8601 (P1Y) — the offer's own value is a plain string, so use the param.
                # planCode / pricingMode refine the plan when the offer carries them.
                item_config: dict[str, Any] = {"domain": domain, "duration": duration}
                for key in ("planCode", "pricingMode"):
                    if offer.get(key):
                        item_config[key] = offer[key]
                item = await self._request(client, "POST", f"/order/cart/{cart_id}/domain", item_config)
                item_id = item["itemId"]

                await self._apply_required_configuration(client, cart_id, item_id)

                # Dry-run first (GET checkout validates the cart WITHOUT ordering) — a misconfigured
                # cart fails here, so we never place a paid order we cannot complete.
                await self._request(client, "GET", f"/order/cart/{cart_id}/checkout")
                order = await self._request(
                    client,
                    "POST",
                    f"/order/cart/{cart_id}/checkout",
                    {"autoPayWithPreferredPaymentMethod": True, "waiveRetractationPeriod": True},
                )
        except DomainProviderError:
            raise
        except Exception as exc:
            # Any unexpected OVH response shape becomes a clean error (never a 500) — with context to debug.
            raise DomainProviderError(f"Commande OVH échouée pour {domain} : {exc!r}") from exc
        logger.info("OVH domain order placed for %s (orderId=%s)", domain, (order or {}).get("orderId"))
        return order or {}

    @staticmethod
    def _pick_create_offer(offers: list[dict[str, Any]] | None, domain: str) -> dict[str, Any]:
        """Pick a standard registration offer, refusing premium/aftermarket (surprise pricing)."""
        for offer in offers or []:
            if offer.get("premium") or offer.get("orderable") is False:
                continue
            if offer.get("action") in (None, "create"):
                return offer
        raise DomainProviderError(f"Aucune offre d'enregistrement standard pour {domain} (premium/indisponible ?)")

    async def _apply_required_configuration(self, client: httpx.AsyncClient, cart_id: str, item_id: str) -> None:
        """Fill the cart item's required configurations, defaulting contacts to the account owner.

        OVH exposes what a given TLD needs (OWNER_CONTACT, DNS, ADMIN/TECH_ACCOUNT…). We only set
        the labels OVH marks required and can default to the account (``/me`` owner + OVH DNS); the
        first live order surfaces anything unexpected via :class:`DomainProviderError`.
        """
        required = await self._request(client, "GET", f"/order/cart/{cart_id}/item/{item_id}/requiredConfiguration")
        labels = {entry.get("label") for entry in (required or []) if entry.get("required")}
        owner = None
        if {"OWNER_CONTACT", "ADMIN_ACCOUNT", "TECH_ACCOUNT"} & labels:
            me = await self._request(client, "GET", "/me")
            owner = (me or {}).get("nichandle")
        values = {
            "OWNER_CONTACT": f"/me/contact/{owner}" if owner else None,
            "ADMIN_ACCOUNT": owner,
            "TECH_ACCOUNT": owner,
            "DNS": "dns.ovh.net;ns.ovh.net",
        }
        for label in labels:
            value = values.get(label)
            if value is None:
                logger.warning("OVH requiredConfiguration %s has no default — first order may need it", label)
                continue
            await self._request(
                client,
                "POST",
                f"/order/cart/{cart_id}/item/{item_id}/configuration",
                {"label": label, "value": value},
            )

    async def order_status(self, order_id: int) -> str | None:
        """Current OVH status of an order (``checking``/``delivering``/``delivered``/``notPaid``…).

        Args:
            order_id: The OVH order id returned at checkout.

        Returns:
            The raw status string, or ``None`` when unconfigured or the read fails (best-effort).
        """
        if not self.is_configured:
            return None
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                status = await self._request(client, "GET", f"/me/order/{order_id}/status")
        except (httpx.HTTPError, DomainProviderError) as exc:
            logger.warning("OVH order status read failed for %s: %s", order_id, exc)
            return None
        return status if isinstance(status, str) else None

    async def zone_ready(self, domain: str) -> bool:
        """Whether the domain's DNS zone exists yet (OVH creates it once the order is active).

        Args:
            domain: The domain whose zone to probe.

        Returns:
            ``True`` when the zone responds, ``False`` while the registration is still processing.
        """
        if not self.is_configured:
            return False
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
                await self._request(client, "GET", f"/domain/zone/{domain}")
        except DomainProviderError:
            return False
        return True

    @staticmethod
    def _is_parking_record(record: dict[str, Any] | None, field_type: str) -> bool:
        """Whether an apex/``www`` record is OVH parking to strip before pointing at Vercel.

        Every apex/``www`` ``A``/``AAAA``/``CNAME`` is parking. A ``TXT`` is only OVH's own web
        redirection marker (``"<code>|…"``) — never a real ``SPF``/``DKIM``/verification ``TXT``,
        which must survive.
        """
        if (record or {}).get("subDomain", "") not in ("", "www"):
            return False
        if field_type in ("A", "AAAA", "CNAME"):
            return True
        return bool(re.match(r"^\d+\|", str((record or {}).get("target", "")).lstrip('"')))

    async def point_to_vercel(self, domain: str, *, ip: str | None = None) -> None:
        """Point the apex **and** ``www`` at the Vercel demo-host only, then refresh the zone.

        OVH seeds a freshly-registered ``.fr`` with default records pointing at its own parking:
        an apex ``A`` to ``213.186.33.5`` plus web-redirection ``TXT`` markers (``"1|www…"``,
        ``"3|welcome"``) that drive the OVH page and the apex→www redirect. Left in place, the
        apex round-robins between OVH and Vercel, Vercel refuses to issue the TLS certificate,
        and ``www`` still shows the OVH page. So we delete every apex/``www`` A/AAAA/CNAME and the
        OVH parking ``TXT`` markers, then point both apex and ``www`` at Vercel with ``A`` records
        (``www`` as ``A`` rather than ``CNAME`` so it never collides with a lingering ``TXT``).

        Args:
            domain: The registered domain whose zone to edit.
            ip: The apex target IP (defaults to :pyattr:`settings.vercel_apex_ip`).

        Raises:
            DomainProviderError: When the provider is not configured or any OVH step fails.
        """
        if not self.is_configured:
            raise DomainProviderError("OVH n'est pas configuré (clés API manquantes)")
        target = ip or settings.vercel_apex_ip
        removed: list[int] = []
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            # Delete apex/www parking. We inspect each record rather than trusting OVH's
            # ``?subDomain=`` filter, which does not reliably match the default parking records.
            for field_type in ("A", "AAAA", "CNAME", "TXT"):
                record_ids = await self._request(client, "GET", f"/domain/zone/{domain}/record?fieldType={field_type}")
                for record_id in record_ids or []:
                    record = await self._request(client, "GET", f"/domain/zone/{domain}/record/{record_id}")
                    if self._is_parking_record(record, field_type):
                        await self._request(client, "DELETE", f"/domain/zone/{domain}/record/{record_id}")
                        removed.append(record_id)
            # Point both apex and www at Vercel (same anycast IP) with A records.
            for sub_domain in ("", "www"):
                await self._request(
                    client,
                    "POST",
                    f"/domain/zone/{domain}/record",
                    {"fieldType": "A", "subDomain": sub_domain, "target": target},
                )
            await self._request(client, "POST", f"/domain/zone/{domain}/refresh")
        logger.warning("OVH re-point %s → %s on apex+www (removed parking records: %s)", domain, target, removed)


ovh_domain_provider = OvhDomainProvider()
