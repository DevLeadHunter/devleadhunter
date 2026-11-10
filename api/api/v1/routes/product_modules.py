"""
Product-module switches.

``GET /product-modules`` tells the dashboard which optional modules it may show; the ``/admin/product-modules``
routes let the super admin switch each installed module on or off, platform-wide.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from models.user import User
from schemas.product_module import (
    EnabledProductModuleResponse,
    ProductModuleStatusResponse,
    ProductModuleSwitchRequest,
)
from services.auth_service import get_current_active_user, require_super_admin
from services.product_module_service import (
    BaseModuleNotSwitchableError,
    ProductModuleNotInstalledError,
    ProductModuleStatus,
    product_module_service,
)

router = APIRouter(tags=["product-modules"])


@router.get("/product-modules", response_model=list[EnabledProductModuleResponse])
async def list_enabled_product_modules(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> list[EnabledProductModuleResponse]:
    """The optional modules installed and switched on, for the module switcher of the dashboard."""
    return [
        EnabledProductModuleResponse.model_validate(module) for module in product_module_service.enabled_modules(db)
    ]


@router.get("/admin/product-modules", response_model=list[ProductModuleStatusResponse])
async def list_product_module_statuses(
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> list[ProductModuleStatusResponse]:
    """Every module with its switch, for the super-admin page."""
    return [
        ProductModuleStatusResponse.model_validate(module_status)
        for module_status in product_module_service.statuses(db)
    ]


@router.patch("/admin/product-modules/{module_key}", response_model=ProductModuleStatusResponse)
async def switch_product_module(
    module_key: str,
    payload: ProductModuleSwitchRequest,
    current_user: User = Depends(require_super_admin),
    db: Session = Depends(get_db),
) -> ProductModuleStatusResponse:
    """Switch an installed module on or off; its pages, routes and loops follow within half a minute."""
    try:
        module_status: ProductModuleStatus = product_module_service.set_enabled(
            db, module_key, payload.is_enabled, user_id=current_user.id
        )
    except BaseModuleNotSwitchableError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le module Sites web est toujours actif.")
    except ProductModuleNotInstalledError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ce module n'est pas installé.")
    return ProductModuleStatusResponse.model_validate(module_status)
