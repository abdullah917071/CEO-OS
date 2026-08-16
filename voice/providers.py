from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
from websockets.asyncio.client import ClientConnection, connect

from voice.contracts import (
    SpeechProvider,
    TranscriptEvent,
    TranscriptionProvider,
    TranscriptionStream,
)


class OpenAITranscriptionStream:
    def __init__(self, api_key: str, model: str, url: str) -> None:
        self.api_key, self.model, self.url = api_key, model, url
        self._socket: ClientConnection | None = None
        self._reader: asyncio.Task[None] | None = None
        self._events: asyncio.Queue[TranscriptEvent | None] = asyncio.Queue()

    async def start(self) -> None:
        self._socket = await connect(
            self.url,
            additional_headers={"Authorization": f"Bearer {self.api_key}"},
            max_size=1_000_000,
        )
        await self._send(
            {
                "type": "session.update",
                "session": {
                    "type": "transcription",
                    "audio": {
                        "input": {
                            "format": {"type": "audio/pcm", "rate": 24_000},
                            "transcription": {"model": self.model},
                            "turn_detection": None,
                        }
                    },
                },
            }
        )
        self._reader = asyncio.create_task(self._read())

    async def append(self, audio: bytes) -> None:
        await self._send(
            {"type": "input_audio_buffer.append", "audio": base64.b64encode(audio).decode()}
        )

    async def commit(self) -> None:
        await self._send({"type": "input_audio_buffer.commit"})

    async def _send(self, value: dict[str, Any]) -> None:
        if self._socket is None:
            raise RuntimeError("Transcription stream is not started")
        await self._socket.send(json.dumps(value, separators=(",", ":")))

    async def _read(self) -> None:
        assert self._socket is not None
        try:
            async for raw in self._socket:
                value = json.loads(raw)
                event_type = value.get("type")
                if event_type == "conversation.item.input_audio_transcription.delta":
                    await self._events.put(TranscriptEvent("delta", str(value.get("delta", ""))))
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    await self._events.put(
                        TranscriptEvent("completed", str(value.get("transcript", "")))
                    )
                elif event_type == "error":
                    error = value.get("error", {})
                    await self._events.put(
                        TranscriptEvent("error", str(error.get("message", "Provider error")))
                    )
        finally:
            await self._events.put(None)

    async def events(self) -> AsyncIterator[TranscriptEvent]:
        while (event := await self._events.get()) is not None:
            yield event

    async def close(self) -> None:
        if self._socket is not None:
            await self._socket.close()
            self._socket = None
        if self._reader is not None:
            self._reader.cancel()
            await asyncio.gather(self._reader, return_exceptions=True)
            self._reader = None


class OpenAITranscriptionProvider:
    name = "openai-realtime-transcription"

    def __init__(self, api_key: str, model: str, url: str) -> None:
        self.api_key, self.model, self.url = api_key, model, url

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def connect(self) -> TranscriptionStream:
        if not self.available:
            raise RuntimeError("Voice transcription provider is unavailable")
        return OpenAITranscriptionStream(self.api_key, self.model, self.url)


class OpenAISpeechProvider:
    name = "openai-speech"

    def __init__(self, api_key: str, model: str, voice: str, base_url: str) -> None:
        self.api_key, self.model, self.voice, self.base_url = api_key, model, voice, base_url

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        if not self.available:
            raise RuntimeError("Voice speech provider is unavailable")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {
            "model": self.model,
            "voice": self.voice,
            "input": text,
            "response_format": "pcm",
        }
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            async with client.stream(
                "POST", "/v1/audio/speech", headers=headers, json=payload
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(4096):
                    if chunk:
                        yield chunk


class Utf8TranscriptionStream:
    """Deterministic test stream: PCM bytes are treated as UTF-8 transcript fixtures."""

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.queue: asyncio.Queue[TranscriptEvent | None] = asyncio.Queue()

    async def start(self) -> None:
        return None

    async def append(self, audio: bytes) -> None:
        self.buffer.extend(audio)
        await self.queue.put(TranscriptEvent("delta", audio.decode()))

    async def commit(self) -> None:
        await self.queue.put(TranscriptEvent("completed", self.buffer.decode()))
        self.buffer.clear()

    async def events(self) -> AsyncIterator[TranscriptEvent]:
        while (event := await self.queue.get()) is not None:
            yield event

    async def close(self) -> None:
        await self.queue.put(None)


class Utf8VoiceProvider(TranscriptionProvider, SpeechProvider):
    name = "deterministic-utf8"
    available = True

    def connect(self) -> TranscriptionStream:
        return Utf8TranscriptionStream()

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        for start in range(0, len(text.encode()), 4):
            await asyncio.sleep(0)
            yield text.encode()[start : start + 4]
