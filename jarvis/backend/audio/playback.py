"""Speaker playback manager with generation ID tracking for instant barge-in cancellation."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AudioPlaybackChunk:
    pcm16_data: bytes
    generation_id: int
    sample_rate: int = 24000


class AudioPlaybackManager:
    """Manages audio playback queue with generation IDs for instantaneous barge-in."""

    def __init__(self, sample_rate: int = 24000) -> None:
        self.sample_rate = sample_rate
        self.generation_id: int = 0
        self.is_playing: bool = False
        self._queue: asyncio.Queue[AudioPlaybackChunk] = asyncio.Queue()
        self._playback_task: asyncio.Task[None] | None = None
        self._running: bool = False

    def start(self) -> None:
        """Start async playback consumer task."""
        if self._running:
            return
        self._running = True
        self._playback_task = asyncio.create_task(self._playback_loop())

    def stop(self) -> None:
        """Stop playback task and flush queue."""
        self._running = False
        self.flush()
        if self._playback_task and not self._playback_task.done():
            self._playback_task.cancel()

    def enqueue_chunk(self, pcm16_data: bytes, generation_id: int | None = None) -> None:
        """Add new audio chunk to playback stream."""
        gen = self.generation_id if generation_id is None else generation_id
        if gen < self.generation_id:
            # Stale chunk from interrupted generation, discard immediately
            return
        self._queue.put_nowait(
            AudioPlaybackChunk(
                pcm16_data=pcm16_data, generation_id=gen, sample_rate=self.sample_rate
            )
        )

    def interrupt_and_flush(self) -> int:
        """Cancel current speech generation and drop all queued audio chunks."""
        self.generation_id += 1
        stale_count = self.flush()
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
        """Consume audio chunks and output via speaker."""
        while self._running:
            try:
                chunk = await self._queue.get()
                # Check if chunk was invalidated while in queue
                if chunk.generation_id < self.generation_id:
                    self._queue.task_done()
                    continue

                self.is_playing = True
                # Calculate chunk playback duration
                samples = len(chunk.pcm16_data) // 2
                duration_sec = samples / max(1, chunk.sample_rate)

                # Simulate real-time audio clock consumption
                await asyncio.sleep(duration_sec)

                self._queue.task_done()
                if self._queue.empty():
                    self.is_playing = False

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Audio playback error: %s", exc)
                await asyncio.sleep(0.05)
