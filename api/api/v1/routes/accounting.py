"""
Accounting routes for admin financial data (admin only).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User
from schemas.accounting import AccountingResponse
from services.accounting_service import accounting_service
from services.auth_service import require_admin

router = APIRouter(prefix="/accounting", tags=["accounting"])


@router.get("", response_model=AccountingResponse)
async def get_accounting_data(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AccountingResponse:
    """
    Get accounting data including transactions and financial summary (admin only).

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        current_user: Current authenticated admin user
        db: Database session

    Returns:
        Accounting data with summary and transactions

    Raises:
        HTTPException: If data retrieval fails
    """
    try:
        data = accounting_service.get_accounting_data(db, skip=skip, limit=limit)
        return AccountingResponse(**data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve accounting data: {e!s}"
        )
