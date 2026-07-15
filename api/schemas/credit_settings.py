"""
Credit settings Pydantic schemas for request/response validation.
"""
from typing import Optional, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator, ConfigDict, field_serializer


class CreditSettingsBase(BaseModel):
    """
    Base credit settings schema with common fields.
    
    Attributes:
        price_per_credit: Price of one credit in EUR
        credits_per_search: Number of credits required for a search operation
        credits_per_result: Number of credits required per prospect found
        credits_per_email: Number of credits required per email sent
        free_credits_on_signup: Number of free credits given on user registration
    """
    price_per_credit: Decimal = Field(
        ...,
        ge=Decimal("0.01"),
        description="Price of one credit in EUR (max 10 digits, 2 decimal places)"
    )
    credits_per_search: int = Field(
        ...,
        ge=1,
        description="Number of credits required for a search operation"
    )
    credits_per_result: int = Field(
        ...,
        ge=1,
        description="Number of credits required per prospect found"
    )
    credits_per_email: int = Field(
        ...,
        ge=1,
        description="Number of credits required per email sent"
    )
    free_credits_on_signup: int = Field(
        ...,
        ge=0,
        description="Number of free credits given on user registration"
    )
    minimum_credits_purchase: int = Field(
        ...,
        ge=1,
        description="Minimum number of credits that can be purchased"
    )


class CreditSettingsUpdate(BaseModel):
    """
    Schema for updating credit settings.
    
    Attributes:
        price_per_credit: Price of one credit in EUR (optional)
        credits_per_search: Number of credits required for a search operation (optional)
        credits_per_result: Number of credits required per prospect found (optional)
        credits_per_email: Number of credits required per email sent (optional)
        free_credits_on_signup: Number of free credits given on user registration (optional)
    """
    price_per_credit: Optional[Decimal] = Field(
        None,
        ge=Decimal("0.01"),
        description="Price of one credit in EUR (max 10 digits, 2 decimal places)"
    )
    credits_per_search: Optional[int] = Field(
        None,
        ge=1,
        description="Number of credits required for a search operation"
    )
    credits_per_result: Optional[int] = Field(
        None,
        ge=1,
        description="Number of credits required per prospect found"
    )
    credits_per_email: Optional[int] = Field(
        None,
        ge=1,
        description="Number of credits required per email sent"
    )
    free_credits_on_signup: Optional[int] = Field(
        None,
        ge=0,
        description="Number of free credits given on user registration"
    )
    minimum_credits_purchase: Optional[int] = Field(
        None,
        ge=1,
        description="Minimum number of credits that can be purchased"
    )
    
    @model_validator(mode='after')
    def check_at_least_one_field(self) -> 'CreditSettingsUpdate':
        """
        Ensure at least one field is provided for update.
        
        Returns:
            CreditSettingsUpdate instance
            
        Raises:
            ValueError: If no fields are provided
        """
        if all(
            field is None for field in [
                self.price_per_credit,
                self.credits_per_search,
                self.credits_per_result,
                self.credits_per_email,
                self.free_credits_on_signup,
                self.minimum_credits_purchase
            ]
        ):
            raise ValueError("At least one field must be provided for update")
        return self


class CreditSettingsResponse(CreditSettingsBase):
    """
    Schema for credit settings response.
    
    Attributes:
        id: Settings unique identifier (always 1)
        created_at: Timestamp when settings were created
        updated_at: Timestamp when settings were last updated
    """
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
    
    @field_serializer('price_per_credit')
    def serialize_price_per_credit(self, value: Decimal) -> float:
        """
        Serialize Decimal to float for JSON response.
        
        Args:
            value: Decimal value to serialize
            
        Returns:
            float representation of the Decimal value
        """
        return float(value)

