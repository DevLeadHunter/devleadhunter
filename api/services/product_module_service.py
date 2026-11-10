"""
The super admin's switches for the optional product modules.

A module is usable when it is installed (its distribution is) AND switched on. A switch with no row yet falls back to
the module's own default; the websites module is the core and is always on.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.clock import naive_utc_now
from core.product_modules.contract import WEBSITES_MODULE_KEY, WEBSITES_MODULE_LABEL, ProductModule
from core.product_modules.registry import ProductModuleRegistry, product_module_registry
from models.product_module_state import ProductModuleState

_WEBSITES_DESCRIPTION: str = "Le module de base : prospects, sites démo, campagnes et ventes. Toujours actif."


class ProductModuleNotInstalledError(LookupError):
    """The module key names no installed module."""


class BaseModuleNotSwitchableError(ValueError):
    """The websites module is the core: it cannot be switched off."""


@dataclass(frozen=True)
class ProductModuleStatus:
    """What the admin page shows of one module."""

    key: str
    label: str
    description: str
    is_installed: bool
    is_enabled: bool
    is_switchable: bool
    load_error: str | None
    updated_at: datetime | None


class ProductModuleService:
    """Reads and flips the module switches; every read takes the caller's session."""

    def __init__(self, registry: ProductModuleRegistry) -> None:
        self._registry: ProductModuleRegistry = registry

    def is_enabled(self, db: Session, key: str) -> bool:
        """
        Whether the module of this key may run: installed and switched on.

        Args:
            db: Active database session.
            key: A module key such as ``ai-assistant``.

        Returns:
            True for the websites module, and for an installed module switched on (or on by default with no switch
            stored yet).
        """
        if key == WEBSITES_MODULE_KEY:
            return True
        module: ProductModule | None = self._registry.get(key)
        if module is None:
            return False
        state: ProductModuleState | None = db.get(ProductModuleState, key)
        return state.is_enabled if state is not None else module.enabled_by_default

    def enabled_modules(self, db: Session) -> list[ProductModule]:
        """
        The installed modules that are switched on.

        Args:
            db: Active database session.

        Returns:
            The modules, sorted by key.
        """
        return [module for module in self._registry.installed() if self.is_enabled(db, module.key)]

    def statuses(self, db: Session) -> list[ProductModuleStatus]:
        """
        Every module the admin page lists: the websites module, the installed ones, then the switches of modules
        that are no longer (or not yet) installed.

        Args:
            db: Active database session.

        Returns:
            One status per module.
        """
        states: dict[str, ProductModuleState] = {
            state.module_key: state for state in db.execute(select(ProductModuleState)).scalars()
        }
        statuses: list[ProductModuleStatus] = [
            ProductModuleStatus(
                key=WEBSITES_MODULE_KEY,
                label=WEBSITES_MODULE_LABEL,
                description=_WEBSITES_DESCRIPTION,
                is_installed=True,
                is_enabled=True,
                is_switchable=False,
                load_error=None,
                updated_at=None,
            )
        ]
        for module in self._registry.installed():
            state: ProductModuleState | None = states.pop(module.key, None)
            statuses.append(
                ProductModuleStatus(
                    key=module.key,
                    label=module.label,
                    description=module.description,
                    is_installed=True,
                    is_enabled=state.is_enabled if state is not None else module.enabled_by_default,
                    is_switchable=True,
                    load_error=None,
                    updated_at=state.updated_at if state is not None else None,
                )
            )
        load_failures: dict[str, str] = self._registry.load_failures()
        for key, state in sorted(states.items()):
            statuses.append(
                ProductModuleStatus(
                    key=key,
                    label=key,
                    description="",
                    is_installed=False,
                    is_enabled=state.is_enabled,
                    is_switchable=False,
                    load_error=load_failures.get(key),
                    updated_at=state.updated_at,
                )
            )
        return statuses

    def set_enabled(self, db: Session, key: str, is_enabled: bool, *, user_id: int) -> ProductModuleStatus:
        """
        Switch an installed module on or off.

        Args:
            db: Active database session.
            key: The module key.
            is_enabled: The new position of the switch.
            user_id: The super admin flipping it.

        Returns:
            The module's status after the change.

        Raises:
            BaseModuleNotSwitchableError: for the websites module.
            ProductModuleNotInstalledError: when no installed module has this key.
        """
        if key == WEBSITES_MODULE_KEY:
            raise BaseModuleNotSwitchableError(key)
        if self._registry.get(key) is None:
            raise ProductModuleNotInstalledError(key)
        state: ProductModuleState | None = db.get(ProductModuleState, key)
        if state is None:
            state = ProductModuleState(module_key=key, is_enabled=is_enabled)
            db.add(state)
        state.is_enabled = is_enabled
        state.updated_at = naive_utc_now()
        state.updated_by_user_id = user_id
        db.commit()
        return next(status for status in self.statuses(db) if status.key == key)


product_module_service = ProductModuleService(product_module_registry)
