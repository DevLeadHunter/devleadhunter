"""
The product module whose code is running.

The core names the module at work each time it hands over to a module's code that may send: its routes, its
background loops, its Stripe events and the beacons of its demo pages. What the core then does on the module's behalf
(logging an email it sends) is filed under that module without the module saying so.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token

_module_key_at_work: ContextVar[str | None] = ContextVar("product_module_at_work", default=None)


class ModuleAtWork:
    """Names the module at work for the current request or task, and tells the core which one it is."""

    @staticmethod
    def key() -> str | None:
        """
        The module whose route, loop or event handler is running.

        Returns:
            The module key, or None while the core runs its own code.
        """
        return _module_key_at_work.get()

    @staticmethod
    def begin(module_key: str) -> None:
        """
        Name the module at work until the current task ends (a request, a background loop).

        Args:
            module_key: The module whose code the task runs.
        """
        _module_key_at_work.set(module_key)

    @staticmethod
    @contextmanager
    def during(module_key: str) -> Iterator[None]:
        """
        Name the module at work for the time of one call, inside a task that goes on with the core's code.

        Args:
            module_key: The module the call hands over to.

        Yields:
            Nothing; the module at work is the one of before once the block is left.
        """
        token: Token[str | None] = _module_key_at_work.set(module_key)
        try:
            yield
        finally:
            _module_key_at_work.reset(token)
