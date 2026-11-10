"""The product-module switches: discovery, defaults, the super admin's changes and the loops that follow them."""

import asyncio
from collections.abc import Iterator
from importlib.metadata import EntryPoint

import pytest
from fastapi import APIRouter
from sqlalchemy.orm import Session

from core.product_modules.contract import BackgroundLoop, ProductModule
from core.product_modules.registry import ProductModuleRegistry, product_module_registry
from models.product_module_state import ProductModuleState
from services.product_module_loop_supervisor import ProductModuleLoopSupervisor
from services.product_module_service import (
    BaseModuleNotSwitchableError,
    ProductModuleNotInstalledError,
    ProductModuleService,
    product_module_service,
)


class _ReceptionistLikeModule(ProductModule):
    key = "ai-assistant"
    label = "Réceptionniste IA"
    enabled_by_default = True


class _WalletLikeModule(ProductModule):
    key = "apple-wallet"
    label = "Cartes Apple Wallet"


class _BrokenModule(ProductModule):
    key = "broken"
    label = "Module cassé"

    def load(self) -> None:
        raise RuntimeError("missing table")


class _WebsitesImpostor(ProductModule):
    key = "websites"
    label = "Faux sites web"


class _ModuleWithBrokenRoutes(ProductModule):
    key = "broken-routes"
    label = "Routes cassées"

    def routers(self) -> list[APIRouter]:
        raise ImportError("cannot import name 'router'")


@pytest.fixture
def two_modules_installed() -> Iterator[None]:
    product_module_registry.use([_WalletLikeModule(), _ReceptionistLikeModule()])
    yield


def test_the_websites_module_is_always_on_even_with_nothing_installed(db: Session) -> None:
    assert product_module_service.is_enabled(db, "websites") is True
    assert product_module_service.is_enabled(db, "ai-assistant") is False


def test_an_installed_module_follows_its_default_until_a_switch_is_stored(
    db: Session, two_modules_installed: None
) -> None:
    assert product_module_service.is_enabled(db, "ai-assistant") is True
    assert product_module_service.is_enabled(db, "apple-wallet") is False
    assert [module.key for module in product_module_service.enabled_modules(db)] == ["ai-assistant"]


def test_the_super_admin_switch_wins_over_the_default(db: Session, two_modules_installed: None) -> None:
    product_module_service.set_enabled(db, "ai-assistant", False, user_id=1)
    product_module_service.set_enabled(db, "apple-wallet", True, user_id=1)

    assert product_module_service.is_enabled(db, "ai-assistant") is False
    assert product_module_service.is_enabled(db, "apple-wallet") is True
    stored: ProductModuleState | None = db.get(ProductModuleState, "ai-assistant")
    assert stored is not None and stored.updated_by_user_id == 1 and stored.updated_at is not None


def test_a_stored_switch_of_a_module_not_installed_never_enables_it(db: Session) -> None:
    db.add(ProductModuleState(module_key="apple-wallet", is_enabled=True))
    db.commit()

    assert product_module_service.is_enabled(db, "apple-wallet") is False
    statuses = {status.key: status for status in product_module_service.statuses(db)}
    assert statuses["apple-wallet"].is_installed is False
    assert statuses["apple-wallet"].is_switchable is False


def test_the_websites_module_cannot_be_switched_off(db: Session) -> None:
    with pytest.raises(BaseModuleNotSwitchableError):
        product_module_service.set_enabled(db, "websites", False, user_id=1)


def test_a_module_not_installed_cannot_be_switched(db: Session) -> None:
    with pytest.raises(ProductModuleNotInstalledError):
        product_module_service.set_enabled(db, "apple-wallet", True, user_id=1)


def test_the_admin_page_lists_websites_first_then_the_installed_modules(
    db: Session, two_modules_installed: None
) -> None:
    statuses = product_module_service.statuses(db)

    assert [status.key for status in statuses] == ["websites", "ai-assistant", "apple-wallet"]
    assert statuses[0].is_switchable is False and statuses[0].is_enabled is True
    assert statuses[1].is_enabled is True and statuses[2].is_enabled is False


def test_a_module_that_fails_to_load_is_left_out_with_its_reason() -> None:
    registry = ProductModuleRegistry()
    broken = EntryPoint(name="broken", value=f"{__name__}:_BrokenModule", group="devleadhunter.product_modules")
    impostor = EntryPoint(name="impostor", value=f"{__name__}:_WebsitesImpostor", group="devleadhunter.product_modules")
    healthy = EntryPoint(name="wallet", value=f"{__name__}:_WalletLikeModule", group="devleadhunter.product_modules")

    modules: dict[str, ProductModule] = {}
    for entry_point in (broken, impostor, healthy):
        module = registry._load_entry_point(entry_point)
        if module is not None and module.key != "websites":
            modules[module.key] = module

    assert list(modules) == ["apple-wallet"]
    assert "RuntimeError: missing table" in registry.load_failures()["broken"]


def test_a_module_whose_routes_cannot_import_is_left_out_at_discovery_not_at_boot() -> None:
    """The core mounts the routers while it boots: a module failing there would take the API down with it."""
    registry = ProductModuleRegistry()
    entry_point = EntryPoint(
        name="broken-routes", value=f"{__name__}:_ModuleWithBrokenRoutes", group="devleadhunter.product_modules"
    )

    assert registry._load_entry_point(entry_point) is None
    assert "ImportError: cannot import name 'router'" in registry.load_failures()["broken-routes"]


def test_the_loops_follow_the_switch(db: Session, two_modules_installed: None) -> None:
    started: list[str] = []

    async def receptionist_loop() -> None:
        started.append("ai-assistant")
        await asyncio.sleep(3600)

    class _LoopingModule(_ReceptionistLikeModule):
        def background_loops(self) -> list[BackgroundLoop]:
            return [receptionist_loop]

    registry = ProductModuleRegistry()
    registry.use([_LoopingModule(), _WalletLikeModule()])
    service = ProductModuleService(registry)
    supervisor = ProductModuleLoopSupervisor(registry, service, session_factory=lambda: _NonClosingSession(db))

    async def scenario() -> None:
        supervisor.reconcile()
        await asyncio.sleep(0)
        assert supervisor.running_keys() == {"ai-assistant"}
        supervisor.reconcile()
        await asyncio.sleep(0)
        assert started == ["ai-assistant"]

        service.set_enabled(db, "ai-assistant", False, user_id=1)
        supervisor.reconcile()
        await asyncio.sleep(0)
        assert supervisor.running_keys() == set()

        service.set_enabled(db, "ai-assistant", True, user_id=1)
        supervisor.reconcile()
        await asyncio.sleep(0)
        assert supervisor.running_keys() == {"ai-assistant"}
        assert started == ["ai-assistant", "ai-assistant"]
        service.set_enabled(db, "ai-assistant", False, user_id=1)
        supervisor.reconcile()

    asyncio.run(scenario())


class _NonClosingSession:
    """The test's session behind a ``with`` block that must not close it."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def __enter__(self) -> Session:
        return self._session

    def __exit__(self, *exc_info: object) -> None:
        return None
