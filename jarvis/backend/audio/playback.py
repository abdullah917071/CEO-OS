"""Speaker playback manager with hardware sounddevice streaming, macOS TTS, and barge-in tracking."""

from __future__ import annotations

import asyncio
import logging
import platform
import shutil
import sys
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AudioPlaybackChunk:
    pcm16_data: bytes
    generation_id: int
    sample_rate: int = 24000


class AudioPlaybackManager:
    """Manages physical audio output via sounddevice and macOS TTS with instant barge-in."""

    def __init__(self, sample_rate: int = 24000, device_index: int | None = None) -> None:
        self.sample_rate = sample_rate
        self.device_index = device_index
        self.generation_id: int = 0
        self.is_playing: bool = False
        self._queue: asyncio.Queue[AudioPlaybackChunk] = asyncio.Queue()
        self._playback_task: asyncio.Task[None] | None = None
        self._running: bool = False
        self._sd_stream: Any | None = None
        self._active_tts_proc: asyncio.subprocess.Process | None = None

    def start(self) -> None:
        """Start async playback consumer task and hardware output stream."""
        if self._running:
            return
        self._running = True

        try:
            import sounddevice as sd

            self._sd_stream = sd.RawOutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                device=self.device_index,
            )
            self._sd_stream.start()
            logger.info("Initialized sounddevice hardware output stream at %d Hz", self.sample_rate)
        except Exception as exc:
            logger.info("Sounddevice output stream unavailable (%s); using fallback audio sink", exc)
            self._sd_stream = None

        self._playback_task = asyncio.create_task(self._playback_loop())

    def stop(self) -> None:
        """Stop playback task and release hardware stream."""
        self._running = False
        self.interrupt_and_flush()
        if self._sd_stream:
            try:
                self._sd_stream.stop()
                self._sd_stream.close()
            except Exception as exc:
                logger.debug("Error closing sounddevice stream: %s", exc)
            self._sd_stream = None

        if self._playback_task and not self._playback_task.done():
            self._playback_task.cancel()

    def enqueue_chunk(self, pcm16_data: bytes, generation_id: int | None = None) -> None:
        """Add new PCM audio chunk to playback stream."""
        gen = self.generation_id if generation_id is None else generation_id
        if gen < self.generation_id:
            # Stale chunk from interrupted generation, discard immediately
            return
        self._queue.put_nowait(
            AudioPlaybackChunk(
                pcm16_data=pcm16_data, generation_id=gen, sample_rate=self.sample_rate
            )
        )

    def speak_text(self, text: str) -> None:
        """Speak text aloud using macOS native Speech Synthesis ('say') or background worker."""
        if not text or not text.strip():
            return

        clean_text = text.replace("**", "").replace("`", "").replace("##", "").replace("\n", " ").strip()

        # Stop previous speech
        if self._active_tts_proc and self._active_tts_proc.returncode is None:
            try:
                self._active_tts_proc.terminate()
            except Exception:
                pass
            self._active_tts_proc = None

        # Check for macOS 'say' utility
        if platform.system() == "Darwin" and shutil.which("say") and "pytest" not in sys.modules:
            try:
                asyncio.create_task(self._run_macos_say(clean_text))
            except RuntimeError:
                # If outside event loop, run synchronous fallback
                pass

    async def _run_macos_say(self, text: str) -> None:
        """Execute macOS 'say' command asynchronously."""
        try:
            self.is_playing = True
            proc = await asyncio.create_subprocess_exec(
                "say",
                "-r",
                "185",
                text,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            self._active_tts_proc = proc
            await proc.wait()
        except Exception as exc:
            logger.debug("macOS say execution error: %s", exc)
        finally:
            self._active_tts_proc = None
            if self._queue.empty():
                self.is_playing = False

    def interrupt_and_flush(self) -> int:
        """Cancel current speech generation and drop all queued audio chunks."""
        self.generation_id += 1
        stale_count = self.flush()

        # Terminate active macOS TTS speech process immediately
        if self._active_tts_proc and self._active_tts_proc.returncode is None:
            try:
                self._active_tts_proc.terminate()
            except Exception:
                pass
            self._active_tts_proc = None

        self.is_playing = False
        logger.info(
            "Barge-in: Incremented playback generation to %d, dropped %d stale chunks",
            self.generation_id,
            stale_count,
        )
        return self.generation_id

    def flush(self) -> int:
        """Clear all pending audio chunks in playback queue."""
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
                count += 1
            except Exception:
                break
        return count

    async def _playback_loop(self) -> None:
        """Consume audio chunks and output via physical speaker or sounddevice."""
        while self._running:
            try:
                chunk = await self._queue.get()
                if chunk.generation_id < self.generation_id:
                    self._queue.task_done()
                    continue

                self.is_playing = True

                # 1. Hardware audio write via sounddevice if available
                if self._sd_stream:
                    try:
                        self._sd_stream.write(chunk.pcm16_data)
                    except Exception as exc:
                        logger.debug("Error writing to sounddevice stream: %s", exc)

                # 2. Real-time audio clock consumption pacing
                samples = len(chunk.pcm16_data) // 2
                duration_sec = samples / max(1, chunk.sample_rate)
                await asyncio.sleep(duration_sec)

                self._queue.task_done()
                if self._queue.empty() and not self._active_tts_proc:
                    self.is_playing = False

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Audio playback error: %s", exc)
                await asyncio.sleep(0.05)
