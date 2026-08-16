"""Gemini Live Session Manager: coordinates realtime audio, barge-in, and auto-timeout."""

from __future__ import annotations

import asyncio
import base64
import logging
import time
from collections.abc import Callable
from typing import Any

from jarvis.backend.audio.playback import AudioPlaybackManager
from jarvis.backend.audio.processing import AudioProcessor
from jarvis.backend.config.settings import GeminiConfig
from jarvis.backend.gemini.auth import GeminiAuthManager
from jarvis.backend.gemini.live import GeminiLiveSocket
from jarvis.backend.tools.registry import JarvisToolRegistry

logger = logging.getLogger(__name__)


class GeminiLiveSession:
    """Coordinates an active Gemini Live real-time bidirectional session."""

    def __init__(
        self,
        auth_manager: GeminiAuthManager,
        config: GeminiConfig,
        tool_registry: JarvisToolRegistry,
        playback_manager: AudioPlaybackManager,
        audio_processor: AudioProcessor,
        on_event: Callable[[str, dict[str, Any]], None] | None = None,
        on_session_ended: Callable[[str], None] | None = None,
    ) -> None:
        self.auth_manager = auth_manager
        self.config = config
        self.tool_registry = tool_registry
        self.playback_manager = playback_manager
        self.audio_processor = audio_processor
        self.on_event = on_event
        self.on_session_ended = on_session_ended

        self.socket = GeminiLiveSocket(auth_manager, config)
        self.session_id: str = f"session_{int(time.time())}"
        self.started_at: float = time.time()
        self.last_activity_at: float = time.time()

        # Telemetry metrics
        self.total_user_speech_sec: float = 0.0
        self.total_gemini_speech_sec: float = 0.0
        self.tool_calls_count: int = 0

        self._mic_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._running: bool = False
        self._tasks: list[asyncio.Task[None]] = []
        self._is_gemini_speaking: bool = False

    @property
    def is_active(self) -> bool:
        return self._running and self.socket.is_connected

    async def start(self, initial_audio: bytes | None = None) -> None:
        """Connect to Gemini Live and spawn async workers."""
        if self._running:
            return

        self._running = True
        self.started_at = time.time()
        self.last_activity_at = time.time()

        declarations = self.tool_registry.get_gemini_declarations()
        await self.socket.connect(tool_declarations=declarations)

        self.playback_manager.start()

        # If pre-roll audio exists, feed it into the mic queue
        if initial_audio:
            self._mic_queue.put_nowait(initial_audio)

        self._tasks = [
            asyncio.create_task(self._mic_sender_loop()),
            asyncio.create_task(self._gemini_receiver_loop()),
            asyncio.create_task(self._watchdog_loop()),
        ]

        self._emit_event("SESSION_CONNECTED", {"session_id": self.session_id})
        logger.info("Gemini Live session %s started", self.session_id)

    def feed_microphone_chunk(self, pcm16_bytes: bytes) -> None:
        """Receive microphone audio chunk from capture stream."""
        if not self._running:
            return

        is_speech = self.audio_processor.is_speech(pcm16_bytes)
        if is_speech:
            self.last_activity_at = time.time()
            self.total_user_speech_sec += 0.1

            # Barge-in: if user speaks while Gemini outputting speech, interrupt immediately!
            if self._is_gemini_speaking or self.playback_manager.is_playing:
                logger.info("Barge-in detected: user speech interrupted Gemini output")
                self.playback_manager.interrupt_and_flush()
                self._is_gemini_speaking = False
                self._emit_event("AI_INTERRUPTED", {"session_id": self.session_id})

            rms = self.audio_processor.calculate_rms(pcm16_bytes)
            self._emit_event("USER_SPEAKING", {"rms": rms})

        self._mic_queue.put_nowait(pcm16_bytes)

    async def send_text_directive(self, text: str) -> None:
        """Send a direct text directive to the active Gemini Live session."""
        if not self._running or not self.socket.is_connected:
            return
        self.last_activity_at = time.time()
        self._emit_event("USER_TRANSCRIPT", {"text": text})
        await self.socket.send_text_message(text)

    async def stop(self, reason: str = "user_ended") -> None:
        """Gracefully disconnect Gemini Live and flush audio."""
        if not self._running:
            return

        self._running = False
        logger.info("Stopping Gemini Live session %s (reason: %s)", self.session_id, reason)

        # Cancel background workers
        for t in self._tasks:
            if not t.done():
                t.cancel()

        self.playback_manager.flush()
        await self.socket.close()

        self._emit_event(
            "SESSION_DISCONNECTED",
            {
                "session_id": self.session_id,
                "reason": reason,
                "duration_seconds": time.time() - self.started_at,
                "user_speech_seconds": self.total_user_speech_sec,
                "gemini_speech_seconds": self.total_gemini_speech_sec,
                "tool_calls_count": self.tool_calls_count,
            },
        )

        if self.on_session_ended:
            try:
                self.on_session_ended(reason)
            except Exception as exc:
                logger.error("Error in on_session_ended callback: %s", exc)

    async def _mic_sender_loop(self) -> None:
        """Stream microphone chunks to Gemini Live WebSocket."""
        while self._running:
            try:
                chunk = await self._mic_queue.get()
                await self.socket.send_audio_chunk(chunk, sample_rate=16000)
                self._mic_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Error in mic sender loop: %s", exc)
                await asyncio.sleep(0.05)

    async def _gemini_receiver_loop(self) -> None:
        """Process incoming Gemini Live messages, audio chunks, and tool requests."""
        async for msg in self.socket.receive_messages():
            if not self._running:
                break

            self.last_activity_at = time.time()

            # Handle server content (audio output & text)
            server_content = msg.get("serverContent")
            if server_content:
                if server_content.get("interrupted"):
                    logger.info("Gemini server reported interrupted state")
                    self.playback_manager.interrupt_and_flush()
                    self._is_gemini_speaking = False
                    self._emit_event("AI_INTERRUPTED", {})

                model_turn = server_content.get("modelTurn")
                if model_turn:
                    parts = model_turn.get("parts", [])
                    for part in parts:
                        # 1. Inline Audio Chunk
                        inline_data = part.get("inlineData")
                        if inline_data and inline_data.get("data"):
                            raw_b64 = inline_data["data"]
                            pcm_bytes = base64.b64decode(raw_b64)
                            self._is_gemini_speaking = True
                            self.total_gemini_speech_sec += len(pcm_bytes) / (24000 * 2)
                            self.playback_manager.enqueue_chunk(pcm_bytes)
                            self.audio_processor.notify_speaker_output(pcm_bytes)
                            self._emit_event(
                                "AI_SPEAKING",
                                {
                                    "bytes_count": len(pcm_bytes),
                                    "b64_pcm": raw_b64,
                                    "sample_rate": 24000,
                                },
                            )

                        # 2. Text / Transcript
                        text_part = part.get("text")
                        if text_part:
                            self._emit_event("AI_TRANSCRIPT", {"text": text_part})

                        # 3. Function Call
                        fn_call = part.get("functionCall")
                        if fn_call:
                            asyncio.create_task(self._handle_function_call(fn_call))

                if server_content.get("turnComplete"):
                    self._is_gemini_speaking = False
                    self._emit_event("AI_TURN_COMPLETE", {})

            # Handle top-level toolCall
            tool_call = msg.get("toolCall")
            if tool_call:
                calls = tool_call.get("functionCalls", [])
                for call in calls:
                    asyncio.create_task(self._handle_function_call(call))

    async def _handle_function_call(self, call_dict: dict[str, Any]) -> None:
        """Execute tool and return result to Gemini Live."""
        name = str(call_dict.get("name", ""))
        args = call_dict.get("args", {}) or {}
        call_id = call_dict.get("id")

        self.tool_calls_count += 1
        self._emit_event("TOOL_CALLED", {"name": name, "arguments": args})
        logger.info("Executing Gemini Live tool call: %s", name)

        result = await self.tool_registry.execute_tool(name, args)
        self._emit_event("TOOL_FINISHED", {"name": name, "result": result})

        await self.socket.send_tool_response(function_name=name, response=result, call_id=call_id)

    async def _watchdog_loop(self) -> None:
        """Monitor conversation silence and auto-disconnect when inactive."""
        timeout_sec = self.config.inactivity_timeout_seconds
        max_duration_sec = self.config.max_session_duration_minutes * 60

        while self._running:
            await asyncio.sleep(1.0)
            now = time.time()
            elapsed_silence = now - self.last_activity_at
            session_duration = now - self.started_at

            # Enforce max session duration
            if session_duration >= max_duration_sec:
                mins = session_duration / 60
                logger.info("Max session duration reached (%.1f min). Disconnecting.", mins)
                await self.stop(reason="max_duration_exceeded")
                break

            # Enforce silence timeout (only when not currently playing audio)
            if elapsed_silence >= timeout_sec and not self.playback_manager.is_playing:
                logger.info(
                    "Inactivity timeout (%.1fs silence). Returning to wake mode.",
                    elapsed_silence,
                )
                await self.stop(reason="inactivity_timeout")
                break

    def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        if self.on_event:
            try:
                self.on_event(event_type, data)
            except Exception as exc:
                logger.error("Error in on_event callback: %s", exc)
