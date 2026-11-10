"""
Runs the background loops of the product modules that are switched on, and only those.

The super admin can switch a module off at any time: within one check its loops are cancelled, and switching it
back on starts them again. A loop that died is started again at the next check, as long as its module is on.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.product_modules.contract import ProductModule
from core.product_modules.registry import ProductModuleRegistry, product_module_registry
from services.product_module_service import ProductModuleService, product_module_service

logger = logging.getLogger(__name__)


class ProductModuleLoopSupervisor:
    """Keeps each switched-on module's loops running and the others stopped."""

    CHECK_INTERVAL_SECONDS: float = 30.0

    def __init__(
        self,
        registry: ProductModuleRegistry,
        service: ProductModuleService,
        session_factory: Callable[[], Session] = SessionLocal,
    ) -> None:
        self._registry: ProductModuleRegistry = registry
        self._service: ProductModuleService = service
        self._session_factory: Callable[[], Session] = session_factory
        self._tasks: dict[str, list[asyncio.Task[None]]] = {}

    async def run_forever(self) -> None:
        """Reconcile the running loops with the switches, every ``CHECK_INTERVAL_SECONDS``."""
        while True:
            try:
                self.reconcile()
            except Exception:
                logger.exception("[ProductModules] Could not reconcile the module loops")
            await asyncio.sleep(self.CHECK_INTERVAL_SECONDS)

    def reconcile(self) -> None:
        """Start the loops of the modules switched on, cancel those of the modules switched off."""
        with self._session_factory() as db:
            enabled_keys: set[str] = {module.key for module in self._service.enabled_modules(db)}
        for module in self._registry.installed():
            if module.key in enabled_keys:
                self._ensure_running(module)
            else:
                self._stop(module.key)

    def running_keys(self) -> set[str]:
        """
        The modules whose loops are running.

        Returns:
            Their keys.
        """
        return {key for key, tasks in self._tasks.items() if any(not task.done() for task in tasks)}

    def _ensure_running(self, module: ProductModule) -> None:
        tasks: list[asyncio.Task[None]] = self._tasks.get(module.key, [])
        if tasks and all(not task.done() for task in tasks):
            return
        if tasks:
            logger.warning("[ProductModules] A loop of %s stopped; starting its loops again", module.key)
            self._stop(module.key)
        self._tasks[module.key] = [asyncio.create_task(loop()) for loop in module.background_loops()]
        if self._tasks[module.key]:
            logger.info("[ProductModules] %s: %d loop(s) started", module.key, len(self._tasks[module.key]))

    def _stop(self, key: str) -> None:
        tasks: list[asyncio.Task[None]] = self._tasks.pop(key, [])
        for task in tasks:
            task.cancel()
        if tasks:
            logger.info("[ProductModules] %s switched off: its loops are stopped", key)


product_module_loop_supervisor = ProductModuleLoopSupervisor(product_module_registry, product_module_service)
