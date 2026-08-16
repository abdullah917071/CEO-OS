"""Microphone audio capture stream with rolling pre-roll buffer."""

from __future__ import annotations

import asyncio
import collections
import logging
from collections.abc import Callable

logger = logging.getLogger(__name__)


class AudioCaptureStream:
    """Captures continuous 16kHz PCM16 audio chunks with rolling pre-roll buffer."""

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size_ms: int = 100,
        pre_roll_buffer_ms: int = 500,
    ) -> None:
        self.sample_rate = sample_rate
        self.chunk_size_ms = chunk_size_ms
        self.chunk_bytes = int(sample_rate * 2 * (chunk_size_ms / 1000.0))  # 16-bit mono
        self.max_pre_roll_chunks = max(1, pre_roll_buffer_ms // chunk_size_ms)
        self._pre_roll_buffer: collections.deque[bytes] = collections.deque(
            maxlen=self.max_pre_roll_chunks
        )
        self._listeners: list[Callable[[bytes], None]] = []
        self._is_capturing: bool = False
        self._capture_task: asyncio.Task[None] | None = None
        self._is_muted: bool = False

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
        """Feed an audio frame (e.g. from sounddevice or simulated stream)."""
        if self._is_muted:
            pcm16_data = b"\x00" * len(pcm16_data)

        self._pre_roll_buffer.append(pcm16_data)
        for listener in list(self._listeners):
            try:
                listener(pcm16_data)
            except Exception as exc:
                logger.error("Error in audio capture listener: %s", exc)

    def start(self) -> None:
        if self._is_capturing:
            return
        self._is_capturing = True
        self._capture_task = asyncio.create_task(self._hardware_or_simulated_capture())

    def stop(self) -> None:
        self._is_capturing = False
        if self._capture_task and not self._capture_task.done():
            self._capture_task.cancel()
        self._pre_roll_buffer.clear()

    async def _hardware_or_simulated_capture(self) -> None:
        """Capture loop from sounddevice or heartbeat baseline generator."""
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
