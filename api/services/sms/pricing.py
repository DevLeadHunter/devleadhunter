"""Estimate the cost of an SMS from its destination country when the provider returns no price.

smsmode's REST v1 send response does not carry a ``price`` for our account (the billed
amount is known from the account plan, not returned per message), so the cost is estimated
from the billed segment count and the per-segment price of the destination country: the
account's real French rate (``SMSMODE_PRICE_PER_SEGMENT_EUR``, read on the smsmode dashboard),
the public price list elsewhere. A price actually returned by the provider is always preferred
over this estimate.
"""

from __future__ import annotations

from typing import ClassVar

from core.config import settings
from services.country_profiles import DEFAULT_COUNTRY_CODE
from services.sms.phone_normalizer import PhoneNumberPlans


class SmsPricing:
    """Per-segment prices of the countries we text, in euro cents.

    The public prices come from smsmode's base-plan price list, read on 2026-10-02 (euros per segment:
    Belgium 0.0616, Switzerland 0.0667, Canada 0.022). France reads the account's own rate, above its
    public 0.0445.
    """

    PUBLIC_PRICE_CENTS_PER_SEGMENT_BY_COUNTRY: ClassVar[dict[str, float]] = {
        "BE": 6.16,
        "CH": 6.67,
        "CA": 2.2,
    }
    FALLBACK_PRICE_CENTS_PER_SEGMENT: ClassVar[float] = 6.67

    @classmethod
    def price_cents_per_segment(cls, country: str | None) -> float:
        """The per-segment price of a destination country.

        Args:
            country: ISO 3166-1 alpha-2 code of the destination, ``None`` when the number's country is unknown.

        Returns:
            The price of one segment in euro cents: the account's rate for France, the public list
            elsewhere, the dearest listed price for an unknown or unlisted destination.
        """
        if country is None:
            return cls.FALLBACK_PRICE_CENTS_PER_SEGMENT
        cleaned = country.strip().upper()
        if cleaned == DEFAULT_COUNTRY_CODE:
            return settings.smsmode_price_per_segment_eur * 100
        return cls.PUBLIC_PRICE_CENTS_PER_SEGMENT_BY_COUNTRY.get(cleaned, cls.FALLBACK_PRICE_CENTS_PER_SEGMENT)

    @classmethod
    def estimate_cents(cls, segments: int, *, country: str | None) -> int:
        """Estimate the cost of one send in cents from its billed segment count and destination country.

        Args:
            segments: Number of billed SMS segments (at least one is charged).
            country: ISO code of the destination country, ``None`` when unknown.

        Returns:
            The estimated cost in whole cents.
        """
        billed_segments = max(int(segments or 0), 1)
        return round(billed_segments * cls.price_cents_per_segment(country))

    @classmethod
    def estimate_cents_for_number(cls, segments: int, *, to_e164: str) -> int:
        """Estimate the cost of one send from its billed segments and the country of the recipient's number.

        Args:
            segments: Number of billed SMS segments.
            to_e164: The recipient number in E.164, whose dial code names the destination country.

        Returns:
            The estimated cost in whole cents.
        """
        return cls.estimate_cents(segments, country=PhoneNumberPlans.country_of_e164(to_e164))

    @staticmethod
    def french_amount_label(cents: int) -> str:
        """Render a cents amount the French way for a log line: ``13 c`` or ``1,20 €``.

        Args:
            cents: The amount in euro cents.

        Returns:
            The amount with its unit.
        """
        if cents < 100:
            return f"{cents} c"
        euros = f"{cents / 100:.2f}".replace(".", ",")
        return f"{euros} €"
