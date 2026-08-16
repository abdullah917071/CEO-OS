from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import asdict
from typing import Any

from fastapi import WebSocket

from core.contracts import RuntimeEvent


def serialize_event(event: RuntimeEvent) -> dict[str, Any]:
    data = asdict(event)
    data["task_id"] = str(event.task_id) if event.task_id else None
    data["occurred_at"] = event.occurred_at.isoformat()
    return data


class EventHub:
    def __init__(self, history_limit: int = 200) -> None:
        if history_limit < 1:
            raise ValueError("history_limit must be positive")
        self._connections: set[WebSocket] = set()
        self._history: deque[dict[str, Any]] = deque(maxlen=history_limit)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def publish(self, event: RuntimeEvent) -> None:
        payload = serialize_event(event)
        async with self._lock:
            self._history.append(payload)
            connections = tuple(self._connections)
        failed: list[WebSocket] = []
        for connection in connections:
            try:
                await connection.send_json(payload)
            except RuntimeError:
                failed.append(connection)
        if failed:
            async with self._lock:
                for connection in failed:
                    self._connections.discard(connection)

    async def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        async with self._lock:
            return list(self._history)[-limit:][::-1]
