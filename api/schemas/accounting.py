"""
Accounting schemas for admin financial data.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from decimal import Decimal


class StripePaymentInfo(BaseModel):
    """
    Detailed Stripe payment information.
    """
    payment_intent_id: Optional[str] = Field(None, description="Stripe Payment Intent ID")
    session_id: Optional[str] = Field(None, description="Stripe Checkout Session ID")
    amount: Decimal = Field(..., description="Payment amount in cents")
    currency: str = Field(default="eur", description="Payment currency")
    status: str = Field(..., description="Payment status")
    payment_method_type: Optional[str] = Field(None, description="Payment method type (card, etc.)")
    payment_method_brand: Optional[str] = Field(None, description="Payment method brand (Visa, Mastercard, etc.)")
    payment_method_last4: Optional[str] = Field(None, description="Last 4 digits of the payment method")
    payment_date: datetime = Field(..., description="Payment date")
    amount_received: Optional[Decimal] = Field(None, description="Amount received after fees")
    application_fee_amount: Optional[Decimal] = Field(None, description="Stripe application fee")
    net_amount: Optional[Decimal] = Field(None, description="Net amount after all fees")
    available_at: Optional[datetime] = Field(None, description="When funds become available (if provided by Stripe)")
    refund_amount: Optional[Decimal] = Field(None, description="Refunded amount if any")
    refund_date: Optional[datetime] = Field(None, description="Refund date if any")
    customer_country: Optional[str] = Field(None, description="Customer country code")
    customer_name: Optional[str] = Field(None, description="Customer name")
    customer_email: Optional[str] = Field(None, description="Customer email")
    ip_address: Optional[str] = Field(None, description="Customer IP address")
    user_agent: Optional[str] = Field(None, description="Customer user agent")


class CreditPurchaseTransaction(BaseModel):
    """
    Credit purchase transaction with payment details.
    """
    transaction_id: int = Field(..., description="Credit transaction ID")
    user_id: int = Field(..., description="User ID who purchased")
    user_name: str = Field(..., description="User name")
    user_email: str = Field(..., description="User email")
    credits_amount: int = Field(..., description="Number of credits purchased")
    credits_available_date: datetime = Field(..., description="When credits became available")
    payment_info: Optional[StripePaymentInfo] = Field(None, description="Stripe payment details")
    euros_amount: Optional[Decimal] = Field(None, description="Amount paid in euros")
    description: str = Field(..., description="Transaction description")


class AccountingSummary(BaseModel):
    """
    Accounting summary with total funds.
    """
    total_paid: Decimal = Field(..., description="Total amount paid by customers (in euros)")
    total_refunded: Decimal = Field(default=Decimal("0"), description="Total amount refunded (in euros)")
    total_stripe_fees: Decimal = Field(default=Decimal("0"), description="Total Stripe fees (in euros)")
    net_total: Decimal = Field(..., description="Net total after fees and refunds (in euros)")
    total_transactions: int = Field(..., description="Total number of transactions")
    available_balance: Optional[Decimal] = Field(None, description="Available balance on Stripe account")


class AccountingResponse(BaseModel):
    """
    Accounting data response.
    """
    summary: AccountingSummary = Field(..., description="Accounting summary")
    transactions: List[CreditPurchaseTransaction] = Field(..., description="List of credit purchase transactions")




