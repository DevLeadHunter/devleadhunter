"""
The product modules installed next to the core, discovered from their entry points.

A module is installed when its distribution is (``pip install``): it then declares, in the
``devleadhunter.product_modules`` group, the class implementing :class:`ProductModule`. Being installed is not being
switched on — that is the super admin's choice, stored by :mod:`services.product_module_service`.
"""

from __future__ import annotations

import logging
from importlib.metadata import EntryPoint, entry_points

from core.product_modules.contract import ENTRY_POINT_GROUP, WEBSITES_MODULE_KEY, ProductModule

logger = logging.getLogger(__name__)


class ProductModuleRegistry:
    """
    The installed product modules, discovered once, in the order of their keys.

    A module that fails to import or to load is logged and left out, with the reason kept for the admin page: a broken
    optional module must never take the core, and the campaigns it sends, down with it.
    """

    def __init__(self, entry_point_group: str = ENTRY_POINT_GROUP) -> None:
        self._entry_point_group: str = entry_point_group
        self._modules: dict[str, ProductModule] | None = None
        self._load_failures: dict[str, str] = {}

    def installed(self) -> list[ProductModule]:
        """
        Every installed module that loaded, discovering them on the first call.

        Returns:
            The modules, sorted by key.
        """
        return list(self._discovered().values())

    def get(self, key: str) -> ProductModule | None:
        """
        The installed module of this key.

        Args:
            key: A module key such as ``ai-assistant``.

        Returns:
            The module, or None when it is not installed (or failed to load).
        """
        return self._discovered().get(key)

    def load_failures(self) -> dict[str, str]:
        """
        The modules that are installed but could not load, with the reason.

        Returns:
            The error message by entry point name.
        """
        self._discovered()
        return dict(self._load_failures)

    def use(self, modules: list[ProductModule]) -> None:
        """
        Replace the discovered modules by these, already loaded (tests and tools only).

        Args:
            modules: The modules the core should see as installed.
        """
        self._modules = {module.key: module for module in sorted(modules, key=lambda module: module.key)}
        self._load_failures = {}

    def reset(self) -> None:
        """Forget the discovered modules, so the next call discovers them again."""
        self._modules = None
        self._load_failures = {}

    def _discovered(self) -> dict[str, ProductModule]:
        if self._modules is None:
            self._modules = self._discover()
        return self._modules

    def _discover(self) -> dict[str, ProductModule]:
        modules: dict[str, ProductModule] = {}
        for entry_point in entry_points(group=self._entry_point_group):
            module: ProductModule | None = self._load_entry_point(entry_point)
            if module is None:
                continue
            if module.key == WEBSITES_MODULE_KEY or module.key in modules:
                self._load_failures[entry_point.name] = f"Clé de module déjà prise : {module.key}"
                logger.error("[ProductModules] %s skipped: the key %s is already taken", entry_point.name, module.key)
                continue
            modules[module.key] = module
        return dict(sorted(modules.items()))

    def _load_entry_point(self, entry_point: EntryPoint) -> ProductModule | None:
        try:
            module_class: type[ProductModule] = entry_point.load()
            module: ProductModule = module_class()
            module.load()
            # Imports the lazy hooks now: a module that cannot import them is left out instead of breaking the boot.
            module.routers()
            module.background_loops()
            module.migrations()
            module.campaign_offer()
        except Exception as exc:
            self._load_failures[entry_point.name] = f"{type(exc).__name__}: {exc}"
            logger.exception("[ProductModules] %s could not load; the core runs without it", entry_point.name)
            return None
        logger.info("[ProductModules] %s loaded (%s)", module.key, entry_point.value)
        return module


product_module_registry = ProductModuleRegistry()
