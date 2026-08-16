"""WebSocket endpoints streaming live audio meters, state changes, and bidirectional audio."""

from __future__ import annotations

import asyncio
import base64
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


@ws_router.websocket("/ws/jarvis/live")
async def jarvis_live_audio_websocket(websocket: WebSocket) -> None:
    """Bidirectional audio and transcript streaming between browser and Gemini Live."""
    await websocket.accept()
    mgr = get_jarvis_manager()
    event_queue = mgr.event_bus.create_queue_subscription()

    async def _send_events() -> None:
        try:
            while True:
                event = await event_queue.get()
                if event.event_type in (
                    "AI_SPEAKING",
                    "AI_TRANSCRIPT",
                    "USER_TRANSCRIPT",
                    "AI_INTERRUPTED",
                    "AI_TURN_COMPLETE",
                    "USER_SPEAKING",
                    "TOOL_CALLED",
                    "TOOL_FINISHED",
                    "JARVIS_TRANSCRIPT",
                ):
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
        except Exception as exc:
            logger.debug("Live WebSocket sender closed: %s", exc)

    async def _receive_client_data() -> None:
        try:
            while True:
                raw_msg = await websocket.receive_text()
                try:
                    payload = json.loads(raw_msg)
                    msg_type = payload.get("type", "")

                    if msg_type == "AUDIO_INPUT":
                        b64_pcm = payload.get("b64_pcm")
                        if b64_pcm:
                            pcm_bytes = base64.b64decode(b64_pcm)
                            mgr.capture_stream.push_external_frame(pcm_bytes)
                            if mgr.active_session and mgr.active_session.is_active:
                                mgr.active_session.feed_microphone_chunk(pcm_bytes)

                    elif msg_type == "USER_TEXT":
                        text = payload.get("text", "").strip()
                        if text:
                            if mgr.active_session and mgr.active_session.is_active:
                                await mgr.active_session.send_text_directive(text)
                            else:
                                await mgr.execute_directive(text)

                    elif msg_type == "INTERRUPT":
                        mgr.playback_manager.interrupt_and_flush()
                        mgr.event_bus.emit("AI_INTERRUPTED", {})

                except Exception as exc:
                    logger.warning("Error handling client message in live websocket: %s", exc)
        except WebSocketDisconnect:
            logger.debug("Live WebSocket client disconnected")
        except Exception as exc:
            logger.debug("Live WebSocket receiver error: %s", exc)

    send_task = asyncio.create_task(_send_events())
    recv_task = asyncio.create_task(_receive_client_data())

    try:
        done, pending = await asyncio.wait(
            [send_task, recv_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
    finally:
        mgr.event_bus.remove_queue_subscription(event_queue)
