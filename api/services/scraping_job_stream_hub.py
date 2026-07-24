"""
WebSocket hub for live scraping job progress (logs + prospects).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)

MAX_BUFFER = 500


class ScrapingJobStreamHub:
    """Broadcast scraping events to subscribed WebSocket clients."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._buffers: dict[str, list[dict[str, Any]]] = defaultdict(list)

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[job_id].add(websocket)
        for event in self._buffers.get(job_id, []):
            await websocket.send_json(event)

    def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        clients = self._connections.get(job_id)
        if not clients:
            return
        clients.discard(websocket)
        if not clients:
            self._connections.pop(job_id, None)

    async def broadcast(self, job_id: str, event: dict[str, Any]) -> None:
        buffer = self._buffers[job_id]
        buffer.append(event)
        if len(buffer) > MAX_BUFFER:
            self._buffers[job_id] = buffer[-MAX_BUFFER:]

        stale: list[WebSocket] = []
        for websocket in list(self._connections.get(job_id, set())):
            try:
                await websocket.send_json(event)
            except Exception as exc:
                logger.debug("WS send failed for job %s: %s", job_id, exc)
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(job_id, websocket)

    def clear(self, job_id: str) -> None:
        self._buffers.pop(job_id, None)
        self._connections.pop(job_id, None)


scraping_job_stream_hub = ScrapingJobStreamHub()
