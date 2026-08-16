"""Microphone audio capture stream with hardware sounddevice capture and rolling pre-roll buffer."""

from __future__ import annotations

import asyncio
import collections
import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class AudioCaptureStream:
    """Captures continuous 16kHz PCM16 audio chunks with rolling pre-roll buffer from microphone hardware."""

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size_ms: int = 100,
        pre_roll_buffer_ms: int = 500,
        device_index: int | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.chunk_size_ms = chunk_size_ms
        self.chunk_samples = int(sample_rate * (chunk_size_ms / 1000.0))
        self.chunk_bytes = self.chunk_samples * 2  # 16-bit mono PCM (2 bytes per sample)
        self.device_index = device_index
        self.max_pre_roll_chunks = max(1, pre_roll_buffer_ms // chunk_size_ms)
        self._pre_roll_buffer: collections.deque[bytes] = collections.deque(
            maxlen=self.max_pre_roll_chunks
        )
        self._listeners: list[Callable[[bytes], None]] = []
        self._is_capturing: bool = False
        self._capture_task: asyncio.Task[None] | None = None
        self._sd_stream: Any | None = None
        self._is_muted: bool = False
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def is_capturing(self) -> bool:
        return self._is_capturing

    @property
    def is_muted(self) -> bool:
        return self._is_muted

    def set_muted(self, muted: bool) -> None:
        self._is_muted = muted
        logger.info("Microphone mute status: %s", muted)

    def add_listener(self, callback: Callable[[bytes], None]) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[bytes], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def get_pre_roll_audio(self) -> bytes:
        """Retrieve and clear buffered pre-roll audio frames captured just before activation."""
        data = b"".join(self._pre_roll_buffer)
        self._pre_roll_buffer.clear()
        return data

    def push_external_frame(self, pcm16_data: bytes) -> None:
        """Feed an audio frame to pre-roll buffer and all registered listeners."""
        if self._is_muted:
            pcm16_data = b"\x00" * len(pcm16_data)

        self._pre_roll_buffer.append(pcm16_data)
        for listener in list(self._listeners):
            try:
                listener(pcm16_data)
            except Exception as exc:
                logger.error("Error in audio capture listener: %s", exc)

    def start(self) -> None:
        """Start microphone capture stream."""
        if self._is_capturing:
            return
        self._is_capturing = True
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

        # Attempt to initialize hardware stream or fallback to baseline loop
        self._capture_task = asyncio.create_task(self._run_capture_loop())

    def stop(self) -> None:
        """Stop microphone capture stream and release hardware."""
        self._is_capturing = False
        if self._sd_stream:
            try:
                self._sd_stream.stop()
                self._sd_stream.close()
            except Exception as exc:
                logger.debug("Error closing sounddevice stream: %s", exc)
            self._sd_stream = None

        if self._capture_task and not self._capture_task.done():
            self._capture_task.cancel()
        self._pre_roll_buffer.clear()

    async def _run_capture_loop(self) -> None:
        """Main capture worker: tries real hardware microphone via sounddevice first, falls back gracefully."""
        use_hardware = False

        try:
            import sounddevice as sd

            loop = asyncio.get_running_loop()

            def _audio_callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
                if status:
                    logger.debug("Audio stream status flag: %s", status)
                if not self._is_capturing:
                    return
                pcm_bytes = bytes(indata)
                loop.call_soon_threadsafe(self.push_external_frame, pcm_bytes)

            self._sd_stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=self.chunk_samples,
                channels=1,
                dtype="int16",
                device=self.device_index,
                callback=_audio_callback,
            )
            self._sd_stream.start()
            use_hardware = True
            logger.info(
                "Hardware microphone stream started: %d Hz, %d ms chunks",
                self.sample_rate,
                self.chunk_size_ms,
            )
        except Exception as exc:
            logger.info(
                "Microphone hardware stream unavailable (%s); using baseline generator", exc
            )
            use_hardware = False

        if use_hardware:
            # Keep task alive while hardware stream callbacks push frames
            while self._is_capturing:
                try:
                    await asyncio.sleep(0.5)
                except asyncio.CancelledError:
                    break
        else:
            # Baseline generator when no physical audio input device is available
            silence_frame = b"\x00" * self.chunk_bytes
            interval_sec = self.chunk_size_ms / 1000.0
            while self._is_capturing:
                try:
                    self.push_external_frame(silence_frame)
                    await asyncio.sleep(interval_sec)
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.error("Capture stream error: %s", exc)
                    await asyncio.sleep(0.1)
