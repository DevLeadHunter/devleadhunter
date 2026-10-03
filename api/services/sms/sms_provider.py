"""Provider-agnostic SMS sending contract.

Keeping the app behind this interface makes swapping smsmode for another A2P
provider (SMSFactor…) a one-file change: only a new :class:`SmsProvider`
implementation, never the sending service, the queue or the routes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(slots=True)
class SmsSendResult:
    """Outcome of a single SMS send.

    Attributes:
        success: Whether the provider accepted the message for delivery.
        provider_message_id: The provider's id, used later to match DLR callbacks.
        price_cents: Cost of the send in cents, when the provider returns it.
        provider_text: The body as the provider acknowledged it (its opt-out mention included), when returned.
        provider_segments: The segments the provider counted and bills, when returned.
        error: A human-readable failure reason, when ``success`` is ``False``.
    """

    success: bool
    provider_message_id: str | None = None
    price_cents: int | None = None
    provider_text: str | None = None
    provider_segments: int | None = None
    error: str | None = None


class SmsProvider(ABC):
    """Sends one SMS through a concrete A2P provider."""

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Whether the provider has the credentials it needs to send."""
        raise NotImplementedError

    @abstractmethod
    async def get_credit_balance(self) -> float | None:
        """Read the platform account's remaining credit balance.

        Returns:
            The remaining credits, or ``None`` when the provider is not
            configured or the balance could not be read (never raises).
        """
        raise NotImplementedError

    @abstractmethod
    async def send(
        self,
        *,
        to_e164: str,
        sender: str,
        text: str,
        opt_out_mention: bool = False,
        ref_client: str | None = None,
        callback_url: str | None = None,
        callback_url_mo: str | None = None,
    ) -> SmsSendResult:
        """Send *text* to *to_e164* from the alphanumeric *sender*.

        Args:
            to_e164: Recipient in E.164 format (``+33…``, ``+41…``).
            sender: Alphanumeric sender id (≤11 chars, e.g. ``Dibodev``).
            text: Message body, without any opt-out mention.
            opt_out_mention: Whether the provider must append its own opt-out mention — a marketing
                SMS carries one, a service SMS does not.
            ref_client: Our own reference echoed back on the callbacks.
            callback_url: Public URL the provider POSTs delivery receipts to.
            callback_url_mo: Public URL the provider POSTs incoming replies (STOP) to.

        Returns:
            The send outcome.
        """
        raise NotImplementedError
