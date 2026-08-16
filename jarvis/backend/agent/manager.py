"""Jarvis Agent Manager: orchestrates microphone capture, wake word, and Gemini Live."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from jarvis.backend.agent.events import JarvisEventBus
from jarvis.backend.agent.state import JarvisState
from jarvis.backend.audio.capture import AudioCaptureStream
from jarvis.backend.audio.playback import AudioPlaybackManager
from jarvis.backend.audio.processing import AudioProcessor
from jarvis.backend.config.database import JarvisDatabase
from jarvis.backend.config.secrets import JarvisSecretsManager
from jarvis.backend.config.settings import JarvisSettings
from jarvis.backend.gemini.auth import GeminiAuthManager
from jarvis.backend.gemini.session import GeminiLiveSession
from jarvis.backend.tools.permissions import ToolPermissionManager
from jarvis.backend.tools.registry import JarvisToolRegistry
from jarvis.backend.usage.tracker import JarvisUsageTracker
from jarvis.backend.wakeword.detector import WakeDetectionResult
from jarvis.backend.wakeword.manager import WakeWordManager

logger = logging.getLogger(__name__)


class JarvisAgentManager:
    """Central coordinator for Jarvis voice assistant on macOS."""

    def __init__(self, settings: JarvisSettings | None = None) -> None:
        self.settings = settings or JarvisSettings()
        self.state: JarvisState = JarvisState.STARTING

        # Core subsystems
        db_path = self.settings.database_path or Path("./data/jarvis/jarvis.sqlite3")
        sa_path = self.settings.service_account_path or Path(
            "./data/secrets/jarvis_service_account.json"
        )

        self.db = JarvisDatabase(db_path)
        self.secrets_manager = JarvisSecretsManager(sa_path)
        self.auth_manager = GeminiAuthManager(self.secrets_manager)
        self.permission_manager = ToolPermissionManager(self.db)
        self.tool_registry = JarvisToolRegistry(self.permission_manager)
        self.event_bus = JarvisEventBus()
        self.usage_tracker = JarvisUsageTracker(self.db)

        # Audio subsystems
        self.audio_processor = AudioProcessor(
            echo_cancellation=self.settings.audio.echo_cancellation,
            noise_suppression=self.settings.audio.noise_suppression,
        )
        self.playback_manager = AudioPlaybackManager(
            sample_rate=self.settings.audio.output_sample_rate
        )
        self.capture_stream = AudioCaptureStream(
            sample_rate=self.settings.audio.input_sample_rate,
            chunk_size_ms=self.settings.audio.chunk_size_ms,
            pre_roll_buffer_ms=self.settings.wakeword.pre_roll_buffer_ms,
        )

        # Wake-word subsystem
        self.wakeword_manager = WakeWordManager(
            config=self.settings.wakeword,
            on_wake_detected=self._on_wake_detected,
        )

        # Active Gemini Live Session (None when IDLE)
        self.active_session: GeminiLiveSession | None = None
        self._is_running: bool = False

        # Bind audio frame listener
        self.capture_stream.add_listener(self._handle_audio_frame)

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def is_muted(self) -> bool:
        return self.capture_stream.is_muted

    def start(self) -> None:
        """Start Jarvis in IDLE_WAKE_WORD state."""
        if self._is_running:
            return

        self._is_running = True
        self.capture_stream.start()
        self.wakeword_manager.start()
        self._transition_to(JarvisState.IDLE_WAKE_WORD)
        self.db.log_event(
            "INFO", "AGENT_STARTED", f"Jarvis listening for '{self.settings.wakeword.wake_word}'"
        )
        logger.info("Jarvis Agent Manager started. State: IDLE_WAKE_WORD")

    def stop(self) -> None:
        """Stop Jarvis completely."""
        self._is_running = False
        if self.active_session:
            asyncio.create_task(self.end_session("agent_stopped"))

        self.wakeword_manager.stop()
        self.capture_stream.stop()
        self.playback_manager.stop()
        self._transition_to(JarvisState.STARTING)
        self.db.log_event("INFO", "AGENT_STOPPED", "Jarvis agent stopped")
        logger.info("Jarvis Agent Manager stopped")

    def set_muted(self, muted: bool) -> None:
        """Toggle microphone mute."""
        self.capture_stream.set_muted(muted)
        self.event_bus.emit("MICROPHONE_MUTE_CHANGED", {"muted": muted})

    async def activate_session(self, trigger_source: str = "manual") -> None:
        """Establish Gemini Live session and enter ACTIVE state."""
        if self.state in (JarvisState.CONNECTING, JarvisState.ACTIVE):
            logger.info("Session already active or connecting")
            return

        self._transition_to(JarvisState.CONNECTING)
        self.wakeword_manager.pause()

        pre_roll = self.capture_stream.get_pre_roll_audio()

        session = GeminiLiveSession(
            auth_manager=self.auth_manager,
            config=self.settings.gemini,
            tool_registry=self.tool_registry,
            playback_manager=self.playback_manager,
            audio_processor=self.audio_processor,
            on_event=self._on_session_event,
            on_session_ended=self._on_session_ended_callback,
        )
        self.active_session = session

        try:
            await session.start(initial_audio=pre_roll)
            self._transition_to(JarvisState.ACTIVE)
            self.db.log_event(
                "INFO", "SESSION_CONNECTED", f"Gemini Live session connected ({trigger_source})"
            )
        except Exception as exc:
            logger.error("Failed to establish Gemini Live session: %s", exc)
            self._transition_to(JarvisState.ERROR)
            self.db.log_event("ERROR", "SESSION_CONNECT_FAILED", str(exc))
            # Return safely to idle wake word
            await asyncio.sleep(1.5)
            await self.end_session(reason="connect_error")

    async def end_session(self, reason: str = "user_ended") -> None:
        """Close Gemini Live session and return to IDLE_WAKE_WORD mode."""
        self._transition_to(JarvisState.ENDING)

        if self.active_session:
            session = self.active_session
            self.active_session = None
            await session.stop(reason=reason)

            # Record session metrics
            duration = time.time() - session.started_at
            self.usage_tracker.record_completed_session(
                session_id=session.session_id,
                started_at=session.started_at,
                duration_sec=duration,
                user_speech_sec=session.total_user_speech_sec,
                gemini_speech_sec=session.total_gemini_speech_sec,
                tool_calls_count=session.tool_calls_count,
                disconnect_reason=reason,
                model_name=self.settings.gemini.model_name,
            )

        self.wakeword_manager.resume()
        self._transition_to(JarvisState.IDLE_WAKE_WORD)
        self.db.log_event(
            "INFO", "SESSION_ENDED", f"Session ended ({reason}). Returned to IDLE_WAKE_WORD"
        )

    def update_settings(self, settings: JarvisSettings) -> None:
        """Hot reload settings across subsystems."""
        self.settings = settings
        self.db.save_settings(settings)
        self.wakeword_manager.update_config(settings.wakeword)
        self.audio_processor.echo_cancellation = settings.audio.echo_cancellation
        self.audio_processor.noise_suppression = settings.audio.noise_suppression
        logger.info("Jarvis settings updated successfully")

    def _handle_audio_frame(self, pcm16_bytes: bytes) -> None:
        """Main audio processing router."""
        rms = self.audio_processor.calculate_rms(pcm16_bytes)
        is_speech = self.audio_processor.is_speech(pcm16_bytes)

        # Broadcast real-time telemetry for dashboard audio meter
        self.event_bus.emit(
            "AUDIO_FRAME_TELEMETRY",
            {
                "rms": rms,
                "meter": self.audio_processor.get_meter_bars(rms),
                "is_speech": is_speech,
                "state": self.state.value,
            },
        )

        if self.state == JarvisState.IDLE_WAKE_WORD:
            # Strictly local wake word processing — NO cloud communication
            self.wakeword_manager.process_audio_frame(pcm16_bytes, is_speech=is_speech)

        elif self.state == JarvisState.ACTIVE and self.active_session:
            # Active conversation stream to Gemini Live
            self.active_session.feed_microphone_chunk(pcm16_bytes)

    def _on_wake_detected(self, result: WakeDetectionResult) -> None:
        """Triggered locally when wake word is spoken."""
        self._transition_to(JarvisState.WAKE_DETECTED)
        msg = (
            f"Wake word '{self.settings.wakeword.wake_word}' detected "
            f"confidence {result.confidence:.2f} ({result.latency_ms:.0f}ms)"
        )
        self.db.log_event("INFO", "WAKE_DETECTED", msg)
        # Transition into Gemini Live session
        asyncio.create_task(self.activate_session(trigger_source="wake_word"))

    def _on_session_event(self, event_type: str, data: dict[str, Any]) -> None:
        self.event_bus.emit(event_type, data)

    def _on_session_ended_callback(self, reason: str) -> None:
        asyncio.create_task(self.end_session(reason=reason))

    def _transition_to(self, new_state: JarvisState) -> None:
        old_state = self.state
        self.state = new_state
        self.event_bus.emit(
            "STATE_CHANGED", {"from_state": old_state.value, "to_state": new_state.value}
        )
        logger.info("Jarvis state: %s ➔ %s", old_state.value, new_state.value)

    async def execute_directive(self, text: str) -> dict[str, Any]:
        """Execute directive, run required tools, speak response aloud, and broadcast events."""
        raw_msg = text.strip()
        clean_lower = raw_msg.lower()

        # Strip wake word prefixes
        for prefix in ("jarvis,", "jarvis", "hey jarvis,", "hey jarvis", "ok jarvis,", "ok jarvis"):
            if clean_lower.startswith(prefix):
                clean_lower = clean_lower[len(prefix) :].strip()
                break

        # Broadcast user transcript
        self.event_bus.emit("JARVIS_TRANSCRIPT", {"role": "user", "text": raw_msg})

        tool_calls_executed: list[dict[str, Any]] = []
        reply_text = ""

        # 1. Complex Task Delegation to Joice
        if any(
            kw in clean_lower
            for kw in (
                "analyze",
                "strategy",
                "competitor",
                "research",
                "suppremo",
                "plan a",
                "build a",
                "delegate to joice",
                "ask joice",
                "write code",
                "financial report",
                "swarm",
            )
        ):
            res = await self.tool_registry.execute_tool("delegate_to_joice", {"goal": raw_msg})
            tool_calls_executed.append(
                {"name": "delegate_to_joice", "arguments": {"goal": raw_msg}, "output": res}
            )
            reply_text = "I'll ask Joice to handle that."

        # 2. Spotify & Media Control
        elif any(k in clean_lower for k in ("spotify", "music", "play focus", "play song")):
            res = await self.tool_registry.execute_tool("open_spotify", {})
            tool_calls_executed.append({"name": "open_spotify", "arguments": {}, "output": res})
            reply_text = "Opening Spotify."

        # 3. Audio & Volume Controls
        elif "mute" in clean_lower and "unmute" not in clean_lower:
            res = await self.tool_registry.execute_tool("mute", {})
            tool_calls_executed.append({"name": "mute", "arguments": {}, "output": res})
            reply_text = "Muted."

        elif "unmute" in clean_lower:
            res = await self.tool_registry.execute_tool("unmute", {})
            tool_calls_executed.append({"name": "unmute", "arguments": {}, "output": res})
            reply_text = "Unmuted."

        elif any(k in clean_lower for k in ("volume down", "lower volume", "turn volume down")):
            res = await self.tool_registry.execute_tool("set_volume", {"level": 30})
            tool_calls_executed.append({"name": "set_volume", "arguments": {"level": 30}, "output": res})
            reply_text = "Volume lowered."

        elif any(k in clean_lower for k in ("volume up", "raise volume", "turn volume up")):
            res = await self.tool_registry.execute_tool("set_volume", {"level": 70})
            tool_calls_executed.append({"name": "set_volume", "arguments": {"level": 70}, "output": res})
            reply_text = "Volume raised."

        # 4. System Status & Telemetry
        elif any(k in clean_lower for k in ("system stats", "cpu", "battery", "system status", "health")):
            res = await self.tool_registry.execute_tool("get_system_stats", {})
            tool_calls_executed.append({"name": "get_system_stats", "arguments": {}, "output": res})
            sys_info = res.get("system", "macOS")
            reply_text = f"System online: {sys_info}."

        # 5. Application Launch
        elif clean_lower.startswith("open "):
            app_target = clean_lower.replace("open ", "").strip()
            if "youtube" in app_target:
                q = app_target.replace("youtube", "").replace("search for", "").strip()
                args = {"query": q} if q else {}
                res = await self.tool_registry.execute_tool("open_youtube", args)
                tool_calls_executed.append({"name": "open_youtube", "arguments": args, "output": res})
                reply_text = "Opening YouTube." if not q else f"Searching YouTube for '{q}'."
            elif app_target.startswith("http") or ".com" in app_target or ".org" in app_target:
                url = app_target if app_target.startswith("http") else f"https://{app_target}"
                res = await self.tool_registry.execute_tool("open_url", {"url": url})
                tool_calls_executed.append({"name": "open_url", "arguments": {"url": url}, "output": res})
                reply_text = "Opening URL."
            else:
                app_name = app_target.title()
                res = await self.tool_registry.execute_tool("open_application", {"application": app_name})
                tool_calls_executed.append({"name": "open_application", "arguments": {"application": app_name}, "output": res})
                reply_text = f"Opening {app_name}."

        # 6. Web Search
        elif clean_lower.startswith("search ") or "search google" in clean_lower:
            q = clean_lower.replace("search google for", "").replace("search google", "").replace("search for", "").replace("search", "").strip()
            res = await self.tool_registry.execute_tool("search_google", {"query": q})
            tool_calls_executed.append({"name": "search_google", "arguments": {"query": q}, "output": res})
            reply_text = f"Searching Google for '{q}'."

        else:
            reply_text = f"Processing directive: {raw_msg}."

        # Broadcast tool events
        for tc in tool_calls_executed:
            self.event_bus.emit(
                "TOOL_EXECUTION",
                {"tool_name": tc["name"], "arguments": tc["arguments"], "output": tc["output"]},
            )

        # Broadcast model transcript
        self.event_bus.emit("JARVIS_TRANSCRIPT", {"role": "model", "text": reply_text})

        # Speak aloud on macOS speakers
        self.playback_manager.speak_text(reply_text)

        return {
            "status": "SUCCESS",
            "response": reply_text,
            "spoken_response": reply_text,
            "tool_calls": tool_calls_executed,
        }

    def get_status(self) -> dict[str, Any]:
        """Aggregate real-time system status."""
        usage = self.usage_tracker.get_today_stats()
        sa_meta = self.secrets_manager.get_public_metadata()

        return {
            "state": self.state.value,
            "is_running": self._is_running,
            "is_muted": self.capture_stream.is_muted,
            "wake_word": self.settings.wakeword.wake_word,
            "wake_model": self.settings.wakeword.model_name,
            "gemini_model": self.settings.gemini.model_name,
            "gemini_voice": self.settings.gemini.voice_name,
            "gemini_connected": self.state == JarvisState.ACTIVE,
            "active_session_id": self.active_session.session_id if self.active_session else None,
            "service_account_configured": sa_meta["configured"],
            "project_id": sa_meta.get("project_id") or self.settings.gemini.project_id,
            "today_sessions": usage.total_sessions_today,
            "active_minutes_today": usage.active_minutes_today,
            "estimated_cost_usd_today": usage.estimated_cost_usd_today,
            "tool_calls_today": usage.total_tool_calls_today,
        }
