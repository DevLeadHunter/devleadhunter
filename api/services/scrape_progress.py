"""
Progress reporting during scraper runs (logs + prospects found).

When nodriver runs on a dedicated thread loop (Windows), handlers are marshalled
back to the uvicorn loop so WebSocket broadcasts work in real time.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from models.prospect import ProspectCreate

LogHandler = Callable[[str], Awaitable[None]]
ProspectHandler = Callable[[ProspectCreate], Awaitable[None]]

T = TypeVar("T")


class ScrapeProgressReporter:
    """Optional async callbacks for live scraping progress."""

    def __init__(
        self,
        *,
        on_log: LogHandler | None = None,
        on_prospect: ProspectHandler | None = None,
        main_loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self._on_log = on_log
        self._on_prospect = on_prospect
        self._main_loop = main_loop

    def _resolve_main_loop(self) -> asyncio.AbstractEventLoop:
        if self._main_loop is not None:
            return self._main_loop
        return asyncio.get_running_loop()

    async def _dispatch(self, handler: Callable[[T], Awaitable[None]], value: T) -> None:
        if not handler:
            return

        try:
            current = asyncio.get_running_loop()
        except RuntimeError:
            current = None

        main_loop = self._resolve_main_loop()
        if current is main_loop:
            await handler(value)
            return

        fut = asyncio.run_coroutine_threadsafe(handler(value), main_loop)
        await asyncio.wrap_future(fut)

    async def log(self, message: str) -> None:
        await self._dispatch(self._on_log, message)

    async def prospect(self, prospect: ProspectCreate) -> None:
        await self._dispatch(self._on_prospect, prospect)
