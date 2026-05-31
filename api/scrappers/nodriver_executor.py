"""
Dedicated asyncio loop for nodriver browser automation.

nodriver requires the Browser to be created and used on the same event loop.
When uvicorn runs with SelectorEventLoop on Windows, browser work is dispatched
to this singleton thread loop.

Progress / WebSocket callbacks must run on the **uvicorn** loop — see
``ScrapeProgressReporter`` which marshals handlers back to the main loop.
"""
from __future__ import annotations

import asyncio
import sys
import threading
from typing import Any, Callable, Coroutine, TypeVar

T = TypeVar("T")


class DedicatedAsyncLoop:
    """Singleton: one background thread + event loop for all nodriver work."""

    _instance: DedicatedAsyncLoop | None = None
    _init_lock = threading.Lock()

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ready = threading.Event()

    @classmethod
    def instance(cls) -> DedicatedAsyncLoop:
        with cls._init_lock:
            if cls._instance is None:
                cls._instance = cls()
                cls._instance._start_thread()
            return cls._instance

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            raise RuntimeError("Nodriver loop not initialized")
        return self._loop

    def _start_thread(self) -> None:
        def run() -> None:
            if sys.platform == "win32":
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._ready.set()
            self._loop.run_forever()

        self._thread = threading.Thread(target=run, daemon=True, name="nodriver-async-loop")
        self._thread.start()
        if not self._ready.wait(timeout=30):
            raise RuntimeError("Timeout starting nodriver asyncio loop")

    def run(self, coro: Coroutine[Any, Any, T], timeout: float = 600) -> T:
        """Blocking helper for scripts (``asyncio.run`` context). Prefer ``run_nodriver_task`` in async code."""
        fut = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return fut.result(timeout=timeout)


def _should_isolate_nodriver_loop() -> bool:
    """Run nodriver in a dedicated loop on Windows (uvicorn reload uses SelectorEventLoop)."""
    return sys.platform == "win32"


def _running_loop() -> asyncio.AbstractEventLoop | None:
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return None


async def run_nodriver_task(task: Callable[[], Coroutine[Any, Any, T]], *, timeout: float = 600) -> T:
    """
    Run nodriver coroutine work on the dedicated loop when required.

    Uses non-blocking ``wrap_future`` so the uvicorn loop keeps serving WebSockets
    while nodriver scrapes on the background thread.
    """
    if not _should_isolate_nodriver_loop():
        return await task()

    current = _running_loop()
    dedicated = DedicatedAsyncLoop.instance()

    # Already on the nodriver loop (nested call) — run inline.
    if current is dedicated.loop:
        return await task()

    fut = asyncio.run_coroutine_threadsafe(task(), dedicated.loop)
    return await asyncio.wait_for(asyncio.wrap_future(fut), timeout=timeout)
