"""Product types sold through DevLeadHunter (multi-product from day one)."""

from enum import Enum


class ProductType(str, Enum):
    """Type of product an order is for."""

    WEBSITE = "website"
    AI_ASSISTANT = "ai_assistant"  # multilingual AI receptionist (recurring subscription)
    APPLE_WALLET = "apple_wallet"  # future product — reserved


PRODUCT_LABELS: dict[str, str] = {
    ProductType.WEBSITE.value: "Site web",
    ProductType.AI_ASSISTANT.value: "Assistant IA",
    ProductType.APPLE_WALLET.value: "Carte de fidélité Apple Wallet",
}

# Default sale price per product, in cents (editable per order).
# The AI assistant is billed as a monthly subscription — this is the default monthly price.
PRODUCT_DEFAULT_AMOUNT_CENTS: dict[str, int] = {
    ProductType.WEBSITE.value: 50000,  # 500 €
    ProductType.AI_ASSISTANT.value: 9900,  # 99 €/mois
    ProductType.APPLE_WALLET.value: 0,
}
