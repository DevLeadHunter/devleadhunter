"""Asyncio event loop for uvicorn + nodriver on Windows.

With ``--reload``, uvicorn may pick ``SelectorEventLoop``, which breaks subprocess-based
scrapers (Playwright, Selenium, etc.).

Since **uvicorn ≥ 0.30**, ``loop=`` must be a known key (``auto``, ``asyncio``, …). On
Windows, after ``asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy())`` (see
``core.win32_asyncio.ensure_proactor_event_loop``), ``loop="asyncio"`` uses the Proactor
loop.

Pass this to ``uvicorn.run(..., loop=...)`` on Windows (after setting the policy):
"""

from __future__ import annotations

UVICORN_WINDOWS_NODRIVER_LOOP = "asyncio"
