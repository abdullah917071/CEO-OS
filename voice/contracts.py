from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TranscriptEvent:
    kind: str
    text: str


class TranscriptionStream(Protocol):
    async def start(self) -> None: ...

    async def append(self, audio: bytes) -> None: ...

    async def commit(self) -> None: ...

    def events(self) -> AsyncIterator[TranscriptEvent]: ...

    async def close(self) -> None: ...


class TranscriptionProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def available(self) -> bool: ...

    def connect(self) -> TranscriptionStream: ...


class SpeechProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def available(self) -> bool: ...

    def synthesize(self, text: str) -> AsyncIterator[bytes]: ...
