"""
Credit transaction Pydantic schemas for request/response validation.
"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class CreditTransactionBase(BaseModel):
    """
    Base credit transaction schema with common fields.
    
    Attributes:
        transaction_type: Type of transaction (PURCHASE, USAGE, REFUND, FREE_GIFT)
        amount: Number of credits (positive for additions, negative for usage)
        description: Description of the transaction
        transaction_metadata: Optional JSON metadata
    """
    transaction_type: str = Field(
        ...,
        description="Transaction type: PURCHASE, USAGE, REFUND, FREE_GIFT"
    )
    amount: int = Field(
        ...,
        description="Number of credits (positive for additions, negative for usage)"
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Human-readable description of the transaction"
    )
    transaction_metadata: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional JSON metadata for additional transaction information"
    )


class CreditTransactionCreate(CreditTransactionBase):
    """
    Schema for creating a new credit transaction.
    
    Attributes:
        user_id: ID of the user who owns this transaction
    """
    user_id: int = Field(..., description="ID of the user who owns this transaction")


class CreditTransactionResponse(CreditTransactionBase):
    """
    Schema for credit transaction response.
    
    Attributes:
        id: Transaction unique identifier
        user_id: ID of the user who owns this transaction
        created_at: Timestamp when transaction was created
    """
    id: int
    user_id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class CreditBalanceResponse(BaseModel):
    """
    Schema for user credit balance response.
    
    Attributes:
        user_id: ID of the user
        balance: Current credit balance
        is_unlimited: Whether user has unlimited credits (admin)
    """
    user_id: int
    balance: int
    is_unlimited: bool = Field(default=False, description="True if user has unlimited credits (admin)")
    
    model_config = ConfigDict(from_attributes=True)

