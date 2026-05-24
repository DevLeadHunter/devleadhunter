"""
Credit transaction model for tracking credit purchases and usage.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, ForeignKey, String, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base


class TransactionType:
    """Transaction type constants."""
    PURCHASE = "PURCHASE"
    USAGE = "USAGE"
    REFUND = "REFUND"
    FREE_GIFT = "FREE_GIFT"


class CreditTransaction(Base):
    """
    Credit transaction model for tracking credit purchases and usage.
    
    This model tracks all credit-related transactions including:
    - Credit purchases (when user buys credits)
    - Credit usage (when user uses credits for searches, emails, etc.)
    - Credit refunds (when credits are refunded)
    - Free gifts (credits given for free, e.g., on signup)
    
    Attributes:
        id: Unique identifier
        user_id: User who owns this transaction
        transaction_type: Type of transaction (PURCHASE, USAGE, REFUND, FREE_GIFT)
        amount: Number of credits (positive for credit additions, negative for usage)
        description: Description of the transaction
        transaction_metadata: Optional JSON metadata for additional information
        created_at: Timestamp when transaction was created
        user: Relationship to User model
    """
    __tablename__ = "credit_transactions"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    transaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Transaction type: PURCHASE, USAGE, REFUND, FREE_GIFT"
    )
    amount: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of credits (positive for additions, negative for usage)"
    )
    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Human-readable description of the transaction"
    )
    transaction_metadata: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        comment="Optional JSON metadata for additional transaction information"
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Relationship to User
    user: Mapped["User"] = relationship("User", back_populates="credit_transactions")
    
    def __repr__(self) -> str:
        """String representation of the credit transaction."""
        return (
            f"<CreditTransaction id={self.id} "
            f"user_id={self.user_id} "
            f"type={self.transaction_type} "
            f"amount={self.amount} "
            f"description={self.description}>"
        )

