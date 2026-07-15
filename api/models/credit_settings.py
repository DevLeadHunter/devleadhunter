"""
Credit settings model for storing credit pricing and costs configuration.
"""
from datetime import datetime
from typing import Optional
from decimal import Decimal
from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.database import Base


class CreditSettings(Base):
    """
    Credit settings model for storing credit pricing and costs.
    
    This model stores the configuration for the credit system, including:
    - Price per credit (in EUR)
    - Credits per search operation
    - Credits per prospect result
    - Credits per email sent
    - Free credits on signup
    
    Attributes:
        id: Unique identifier (always 1, single row configuration)
        price_per_credit: Price of one credit in EUR
        credits_per_search: Number of credits required for a search operation
        credits_per_result: Number of credits required per prospect found
        credits_per_email: Number of credits required per email sent
        free_credits_on_signup: Number of free credits given on user registration
        created_at: Timestamp when settings were created
        updated_at: Timestamp when settings were last updated
    """
    __tablename__ = "credit_settings"
    
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    price_per_credit: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.10"),
        comment="Price of one credit in EUR"
    )
    credits_per_search: Mapped[int] = mapped_column(
        nullable=False,
        default=5,
        comment="Number of credits required for a search operation"
    )
    credits_per_result: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
        comment="Number of credits required per prospect found"
    )
    credits_per_email: Mapped[int] = mapped_column(
        nullable=False,
        default=3,
        comment="Number of credits required per email sent"
    )
    free_credits_on_signup: Mapped[int] = mapped_column(
        nullable=False,
        default=15,
        comment="Number of free credits given on user registration"
    )
    minimum_credits_purchase: Mapped[int] = mapped_column(
        nullable=False,
        default=10,
        comment="Minimum number of credits that can be purchased"
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(onupdate=func.now(), nullable=True)
    
    def __repr__(self) -> str:
        """String representation of the credit settings."""
        return (
            f"<CreditSettings id={self.id} "
            f"price_per_credit={self.price_per_credit} "
            f"credits_per_search={self.credits_per_search} "
            f"credits_per_result={self.credits_per_result} "
            f"credits_per_email={self.credits_per_email} "
            f"free_credits_on_signup={self.free_credits_on_signup} "
            f"minimum_credits_purchase={self.minimum_credits_purchase}>"
        )

