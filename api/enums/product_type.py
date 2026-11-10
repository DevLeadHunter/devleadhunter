"""Product types sold through DevLeadHunter (multi-product from day one)."""

from enum import Enum


class ProductType(str, Enum):
    """Type of product an order is for."""

    WEBSITE = "website"


PRODUCT_LABELS: dict[str, str] = {
    ProductType.WEBSITE.value: "Site web",
}

# Default sale price per product, in cents (editable per order). The product modules bill their own
# subscriptions, outside the orders.
PRODUCT_DEFAULT_AMOUNT_CENTS: dict[str, int] = {
    ProductType.WEBSITE.value: 50000,  # 500 €
}
