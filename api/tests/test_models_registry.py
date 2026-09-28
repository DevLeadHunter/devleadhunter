"""The models package exports every model: ``init_db()`` imports it to create every table."""

import importlib
import inspect
import pkgutil

import models
from core.database import Base


def _every_model_name() -> set[str]:
    names: set[str] = set()
    for module_info in pkgutil.iter_modules(models.__path__):
        module = importlib.import_module(f"models.{module_info.name}")
        for name, value in vars(module).items():
            if inspect.isclass(value) and issubclass(value, Base) and value.__module__ == module.__name__:
                names.add(name)
    return names


def test_the_models_package_imports_and_exports_every_model() -> None:
    every_model = _every_model_name()

    assert {name for name in every_model if not hasattr(models, name)} == set()
    assert every_model - set(models.__all__) == set()
