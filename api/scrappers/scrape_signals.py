"""
Thread-safe side-channel for scrapers to flag a block/anomaly to the orchestrator.

Scrapers run deep in a nodriver worker thread and collapse every failure to ``[]`` or
an exception, so at the orchestrator a *block* (captcha / Cloudflare / no-feed) is
indistinguishable from a legitimately *empty* result. When a scraper detects a block it
calls :func:`note_block` with the captured HTML; the orchestrator consumes it with
:func:`pop_block` right after the scrape to classify the outcome and keep the HTML
snapshot for the admin monitoring page (reactive capture — no proactive probing).
"""
from __future__ import annotations

import threading
from typing import Optional, TypedDict


class BlockInfo(TypedDict):
    """A recorded block signal for one source."""

    reason: str
    html: Optional[str]


# Cap the captured HTML so a diagnostic row stays reasonable in size.
_MAX_HTML_CHARS: int = 200_000

_lock = threading.Lock()
_blocks: dict[str, BlockInfo] = {}


def note_block(source: str, *, reason: str, html: Optional[str] = None) -> None:
    """Flag that ``source`` was blocked on its last run (consumed by the orchestrator).

    Args:
        source: Source value (e.g. ``"google"``, ``"pagesjaunes"``).
        reason: Short human cause (``"captcha"``, ``"no feed"``, ``"all tiers blocked"``).
        html: Optional page HTML captured at the moment of the block (truncated).
    """
    snapshot = html[:_MAX_HTML_CHARS] if isinstance(html, str) and html else None
    with _lock:
        _blocks[source] = {"reason": reason, "html": snapshot}


def pop_block(source: str) -> Optional[BlockInfo]:
    """Return and clear the pending block signal for ``source`` (``None`` if none)."""
    with _lock:
        return _blocks.pop(source, None)


def clear(source: str) -> None:
    """Drop any stale block signal for ``source`` before a fresh run."""
    with _lock:
        _blocks.pop(source, None)
