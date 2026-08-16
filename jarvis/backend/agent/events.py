"""Internal event bus for Jarvis decoupled reactive coordination."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class JarvisEvent:
    event_type: str
    timestamp: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)


class JarvisEventBus:
    """Pub/Sub event bus distributing agent telemetry, VAD metrics, and tool actions."""

    def __init__(self) -> None:
        self._listeners: list[Callable[[JarvisEvent], None]] = []
        self._async_queues: list[asyncio.Queue[JarvisEvent]] = []

    def subscribe(self, callback: Callable[[JarvisEvent], None]) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unsubscribe(self, callback: Callable[[JarvisEvent], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def create_queue_subscription(self) -> asyncio.Queue[JarvisEvent]:
        q: asyncio.Queue[JarvisEvent] = asyncio.Queue(maxsize=100)
        self._async_queues.append(q)
        return q

    def remove_queue_subscription(self, q: asyncio.Queue[JarvisEvent]) -> None:
        if q in self._async_queues:
            self._async_queues.remove(q)

    def emit(self, event_type: str, data: dict[str, Any] | None = None) -> JarvisEvent:
        event = JarvisEvent(event_type=event_type, data=data or {})

        # Notify sync callbacks
        for listener in list(self._listeners):
            try:
                listener(event)
            except Exception as exc:
                logger.error("Error in event listener: %s", exc)

        # Notify async queues
        for q in list(self._async_queues):
            try:
                if q.full():
                    try:
                        q.get_nowait()
                    except Exception:
                        pass
                q.put_nowait(event)
            except Exception as exc:
                logger.debug("Failed putting event in queue: %s", exc)

        return event
