"""Website sale price per user — the single source for ``{prix}``, the order default, and the sale drawer.

Léo launches at 500 €, but the price is configurable per user so a later
"sites à 200 €" adapts the whole software (email variable, new orders, invoice)
from a single setting rather than a hard-coded amount.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.user import User
from services.country_profiles import DEFAULT_COUNTRY_CODE, CountryProfiles

# Launch price, used when a user has not set their own.
DEFAULT_SALE_PRICE_CENTS = 50000


class PricingService:
    """Resolve and format the website sale price a user charges."""

    @staticmethod
    def sale_price_cents(db: Session, user_id: int) -> int:
        """
        Return the user's configured website sale price, in cents.

        Args:
            db: Active database session.
            user_id: Owner of the price.

        Returns:
            The stored price, or ``DEFAULT_SALE_PRICE_CENTS`` (500 €) when unset.
        """
        user: User | None = db.get(User, user_id)
        if user is None or user.site_sale_price_cents is None:
            return DEFAULT_SALE_PRICE_CENTS
        return user.site_sale_price_cents

    @staticmethod
    def format_price(cents: int) -> str:
        """
        Render a cents amount as a French euro string ("500 €", "499,90 €").

        Args:
            cents: Amount in cents.

        Returns:
            The euro-formatted string, with a French decimal comma when needed.
        """
        return CountryProfiles.get(DEFAULT_COUNTRY_CODE).format_price(cents)
