"""
Payment Pydantic schemas for request/response validation.
"""
from typing import Optional
from pydantic import BaseModel, Field


class CheckoutSessionCreate(BaseModel):
    """
    Schema for creating a checkout session.
    
    Attributes:
        credits: Number of credits to purchase
        success_url: URL to redirect after successful payment (optional, defaults to frontend success page)
        cancel_url: URL to redirect if payment is cancelled (optional, defaults to frontend cancel page)
    """
    credits: int = Field(
        ...,
        ge=1,
        description="Number of credits to purchase"
    )
    success_url: Optional[str] = Field(
        None,
        description="URL to redirect after successful payment"
    )
    cancel_url: Optional[str] = Field(
        None,
        description="URL to redirect if payment is cancelled"
    )


class CheckoutSessionResponse(BaseModel):
    """
    Schema for checkout session response.
    
    Attributes:
        session_id: Stripe checkout session ID
        url: Stripe checkout session URL to redirect user
        amount: Payment amount in cents
        credits: Number of credits being purchased
    """
    session_id: str = Field(..., description="Stripe checkout session ID")
    url: str = Field(..., description="Stripe checkout session URL")
    amount: int = Field(..., description="Payment amount in cents")
    credits: int = Field(..., description="Number of credits being purchased")


class PaymentStatusResponse(BaseModel):
    """
    Schema for payment status response.
    
    Attributes:
        status: Payment status (success, pending, failed)
        message: Status message
    """
    status: str = Field(..., description="Payment status")
    message: str = Field(..., description="Status message")

