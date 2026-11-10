"""Mounts the routers of the installed product modules, closed while their module is switched off."""

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from core.product_modules.registry import product_module_registry
from services.product_module_service import product_module_service


def module_switch_dependency(module_key: str) -> Callable[[Session], None]:
    """
    Build the dependency that answers 404 on every route of a module switched off.

    A 404 rather than a 403: for a visitor of a public page (a receptionist's widget, say), a module switched off
    is a page that no longer exists.

    Args:
        module_key: The module the routes belong to.

    Returns:
        The FastAPI dependency.
    """

    def require_module_switched_on(db: Session = Depends(get_db)) -> None:
        if not product_module_service.is_enabled(db, module_key):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module désactivé")

    return require_module_switched_on


def include_product_module_routers(router: APIRouter) -> None:
    """
    Mount, in order, the routers of every installed module behind its switch.

    Args:
        router: The API v1 router.
    """
    for module in product_module_registry.installed():
        dependency: Callable[[Session], None] = module_switch_dependency(module.key)
        for module_router in module.routers():
            router.include_router(module_router, dependencies=[Depends(dependency)])
