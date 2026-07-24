"""Product types sold through DevLeadHunter (multi-product from day one)."""

from enum import Enum


class ProductType(str, Enum):
    """Type of product an order is for."""

    WEBSITE = "website"
    APPLE_WALLET = "apple_wallet"  # future product — reserved


PRODUCT_LABELS: dict[str, str] = {
    ProductType.WEBSITE.value: "Site web",
    ProductType.APPLE_WALLET.value: "Carte de fidélité Apple Wallet",
}

# Default sale price per product, in cents (editable per order).
PRODUCT_DEFAULT_AMOUNT_CENTS: dict[str, int] = {
    ProductType.WEBSITE.value: 50000,  # 500 €
    ProductType.APPLE_WALLET.value: 0,
}
