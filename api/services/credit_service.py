"""
Credit service for managing user credits and transactions.
"""
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from models.user import User
from models.credit_transaction import CreditTransaction, TransactionType
from enums.user_role import UserRole


class CreditService:
    """
    Service for managing user credits and transactions.
    """
    
    @staticmethod
    def get_user_balance(db: Session, user_id: int) -> int:
        """
        Calculate the current credit balance for a user.
        
        Admins have unlimited credits (returns -1 to indicate unlimited).
        Regular users have their balance calculated from transactions.
        
        Args:
            db: Database session
            user_id: User ID to calculate balance for
            
        Returns:
            Credit balance. Returns -1 for unlimited (admin), otherwise sum of transactions
        """
        # Get user
        user: Optional[User] = db.query(User).filter(User.id == user_id).first()
        if not user:
            return 0
        
        # Admins have unlimited credits
        if user.role == UserRole.ADMIN.value:
            return -1  # -1 indicates unlimited
        
        # Calculate balance from transactions
        result = db.execute(
            select(func.sum(CreditTransaction.amount))
            .where(CreditTransaction.user_id == user_id)
        ).scalar()
        
        return int(result) if result is not None else 0
    
    @staticmethod
    def get_user_credits_consumed(db: Session, user_id: int) -> int:
        """
        Calculate total credits consumed by a user.
        
        Args:
            db: Database session
            user_id: User ID to calculate consumed credits for
            
        Returns:
            Total credits consumed (sum of negative transactions)
        """
        # Get user
        user: Optional[User] = db.query(User).filter(User.id == user_id).first()
        if not user:
            return 0
        
        # Admins have unlimited credits
        if user.role == UserRole.ADMIN.value:
            return 0  # Admins don't consume credits
        
        # Calculate sum of negative transactions (usage)
        result = db.execute(
            select(func.sum(CreditTransaction.amount))
            .where(
                CreditTransaction.user_id == user_id,
                CreditTransaction.amount < 0
            )
        ).scalar()
        
        # Return absolute value (consumed is positive)
        return abs(int(result)) if result is not None else 0
    
    @staticmethod
    def create_transaction(
        db: Session,
        user_id: int,
        transaction_type: str,
        amount: int,
        description: str,
        metadata: Optional[str] = None
    ) -> CreditTransaction:
        """
        Create a new credit transaction.
        
        Args:
            db: Database session
            user_id: User ID for the transaction
            transaction_type: Type of transaction (PURCHASE, USAGE, REFUND, FREE_GIFT)
            amount: Number of credits (positive for additions, negative for usage)
            description: Description of the transaction
            metadata: Optional JSON metadata
            
        Returns:
            Created CreditTransaction object
        """
        transaction = CreditTransaction(
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            description=description,
            transaction_metadata=metadata
        )
        
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        
        return transaction
    
    @staticmethod
    def add_credits(
        db: Session,
        user_id: int,
        amount: int,
        description: str,
        transaction_type: str = TransactionType.PURCHASE,
        metadata: Optional[str] = None
    ) -> CreditTransaction:
        """
        Add credits to a user's account.
        
        Args:
            db: Database session
            user_id: User ID to add credits to
            amount: Number of credits to add (must be positive)
            description: Description of the transaction
            transaction_type: Type of transaction (default: PURCHASE)
            metadata: Optional JSON metadata
            
        Returns:
            Created CreditTransaction object
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        return CreditService.create_transaction(
            db=db,
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            description=description,
            metadata=metadata
        )
    
    @staticmethod
    def use_credits(
        db: Session,
        user_id: int,
        amount: int,
        description: str,
        metadata: Optional[str] = None
    ) -> bool:
        """
        Use credits from a user's account.
        
        Args:
            db: Database session
            user_id: User ID to use credits from
            amount: Number of credits to use (must be positive)
            description: Description of the transaction
            metadata: Optional JSON metadata
            
        Returns:
            True if credits were successfully used, False if insufficient credits
            
        Raises:
            ValueError: If amount is not positive
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        # Get user
        user: Optional[User] = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Admins have unlimited credits
        if user.role == UserRole.ADMIN.value:
            return True
        
        # Check if user has enough credits
        balance = CreditService.get_user_balance(db, user_id)
        if balance < amount:
            return False
        
        # Create usage transaction (negative amount)
        CreditService.create_transaction(
            db=db,
            user_id=user_id,
            transaction_type=TransactionType.USAGE,
            amount=-amount,
            description=description,
            metadata=metadata
        )
        
        return True
    
    @staticmethod
    def get_user_transactions(
        db: Session,
        user_id: int,
        limit: int = 100,
        skip: int = 0
    ) -> list[CreditTransaction]:
        """
        Get credit transactions for a user.
        
        Args:
            db: Database session
            user_id: User ID to get transactions for
            limit: Maximum number of transactions to return
            skip: Number of transactions to skip
            
        Returns:
            List of CreditTransaction objects
        """
        return db.query(CreditTransaction)\
            .filter(CreditTransaction.user_id == user_id)\
            .order_by(CreditTransaction.created_at.desc())\
            .offset(skip)\
            .limit(limit)\
            .all()


# Singleton instance
credit_service = CreditService()

