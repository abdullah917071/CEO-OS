"""WebSocket endpoint streaming live audio meters and state changes to dashboard."""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from jarvis.backend.api.routes import get_jarvis_manager

logger = logging.getLogger(__name__)

ws_router = APIRouter(tags=["jarvis-websocket"])


@ws_router.websocket("/ws/jarvis/status")
async def jarvis_status_websocket(websocket: WebSocket) -> None:
    """Stream real-time Jarvis state, audio meter levels, and events to frontend."""
    await websocket.accept()
    mgr = get_jarvis_manager()
    event_queue = mgr.event_bus.create_queue_subscription()

    try:
        # Send initial full status payload
        await websocket.send_text(json.dumps({"type": "STATUS_UPDATE", "data": mgr.get_status()}))

        while True:
            # Wait for event or send heartbeat
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": event.event_type,
                            "timestamp": event.timestamp,
                            "data": event.data,
                        }
                    )
                )
                event_queue.task_done()
            except TimeoutError:
                # Periodic heartbeat status
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "HEARTBEAT",
                            "data": mgr.get_status(),
                        }
                    )
                )
    except WebSocketDisconnect:
        logger.debug("Jarvis dashboard WebSocket disconnected")
    except Exception as exc:
        logger.error("Jarvis WebSocket stream error: %s", exc)
    finally:
        mgr.event_bus.remove_queue_subscription(event_queue)
