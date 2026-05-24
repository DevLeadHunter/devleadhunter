"""
Credit management routes.
"""
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from schemas.credit_transaction import (
    CreditTransactionCreate,
    CreditTransactionResponse,
    CreditBalanceResponse
)
from services.auth_service import require_auth, require_admin
from services.credit_service import credit_service, TransactionType
from models.user import User

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/balance", response_model=CreditBalanceResponse)
async def get_my_balance(
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
) -> CreditBalanceResponse:
    """
    Get current user's credit balance.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Credit balance information
    """
    balance = credit_service.get_user_balance(db, current_user.id)
    is_unlimited = balance == -1
    
    return CreditBalanceResponse(
        user_id=current_user.id,
        balance=balance if not is_unlimited else 0,
        is_unlimited=is_unlimited
    )


@router.get("/balance/{user_id}", response_model=CreditBalanceResponse)
async def get_user_balance(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> CreditBalanceResponse:
    """
    Get a user's credit balance (admin only).
    
    Args:
        user_id: User ID to get balance for
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        Credit balance information
        
    Raises:
        HTTPException: If user not found
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    balance = credit_service.get_user_balance(db, user_id)
    is_unlimited = balance == -1
    
    return CreditBalanceResponse(
        user_id=user_id,
        balance=balance if not is_unlimited else 0,
        is_unlimited=is_unlimited
    )


@router.get("/transactions", response_model=List[CreditTransactionResponse])
async def get_my_transactions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
) -> List[CreditTransactionResponse]:
    """
    Get current user's credit transactions.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        List of credit transactions
    """
    transactions = credit_service.get_user_transactions(
        db, current_user.id, limit=limit, skip=skip
    )
    return transactions


@router.post("/add", response_model=CreditTransactionResponse, status_code=status.HTTP_201_CREATED)
async def add_credits(
    user_id: int,
    amount: int,
    description: str = "Credit purchase",
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> CreditTransactionResponse:
    """
    Add credits to a user's account (admin only).
    
    Args:
        user_id: User ID to add credits to
        amount: Number of credits to add
        description: Description of the transaction
        current_user: Current authenticated admin user
        db: Database session
        
    Returns:
        Created credit transaction
        
    Raises:
        HTTPException: If user not found or invalid amount
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive"
        )
    
    transaction = credit_service.add_credits(
        db=db,
        user_id=user_id,
        amount=amount,
        description=description,
        transaction_type=TransactionType.PURCHASE
    )
    
    return transaction


@router.post("/use", status_code=status.HTTP_200_OK)
async def use_credits(
    amount: int,
    description: str,
    metadata: str = None,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db)
) -> dict[str, Any]:
    """
    Use credits from current user's account.
    
    Args:
        amount: Number of credits to use
        description: Description of the transaction
        metadata: Optional JSON metadata
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        Success status and remaining balance
        
    Raises:
        HTTPException: If insufficient credits or invalid amount
    """
    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive"
        )
    
    success = credit_service.use_credits(
        db=db,
        user_id=current_user.id,
        amount=amount,
        description=description,
        metadata=metadata
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient credits"
        )
    
    balance = credit_service.get_user_balance(db, current_user.id)
    
    return {
        "success": True,
        "message": f"Used {amount} credits",
        "remaining_balance": balance if balance != -1 else "unlimited"
    }

