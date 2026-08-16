from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from voice.contracts import SpeechProvider, TranscriptionProvider, TranscriptionStream

JsonSink = Callable[[dict[str, Any]], Awaitable[None]]
AudioSink = Callable[[bytes], Awaitable[None]]
SubmitTask = Callable[[str], Awaitable[UUID]]
CancelTask = Callable[[UUID], Awaitable[None]]
WaitTask = Callable[[UUID], Awaitable[str]]


class VoicePolicyError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class VoicePolicy:
    enabled: bool = False
    max_frame_bytes: int = 48_000
    max_turn_bytes: int = 4_800_000


class VoiceRuntime:
    def __init__(
        self,
        transcriber: TranscriptionProvider,
        speaker: SpeechProvider,
        policy: VoicePolicy,
    ) -> None:
        self.transcriber, self.speaker, self.policy = transcriber, speaker, policy
        self._sessions: set[VoiceSession] = set()

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.policy.enabled,
            "available": self.transcriber.available and self.speaker.available,
            "transcription_provider": self.transcriber.name,
            "speech_provider": self.speaker.name,
            "audio": {"format": "pcm16", "sample_rate_hz": 24_000, "channels": 1},
            "retention": "none",
            "session_count": len(self._sessions),
        }

    async def open_session(
        self,
        json_sink: JsonSink,
        audio_sink: AudioSink,
        submit_task: SubmitTask,
        cancel_task: CancelTask,
        wait_task: WaitTask,
    ) -> VoiceSession:
        if not self.policy.enabled or not self.transcriber.available or not self.speaker.available:
            raise VoicePolicyError("Voice runtime is disabled or unavailable")
        session = VoiceSession(
            self.transcriber.connect(),
            self.speaker,
            self.policy,
            json_sink,
            audio_sink,
            submit_task,
            cancel_task,
            wait_task,
        )
        self._sessions.add(session)
        await session.start()
        return session

    async def close_session(self, session: VoiceSession) -> None:
        await session.close()
        self._sessions.discard(session)

    async def shutdown(self) -> None:
        await asyncio.gather(
            *(session.close() for session in tuple(self._sessions)),
            return_exceptions=True,
        )
        self._sessions.clear()


class VoiceSession:
    def __init__(
        self,
        stream: TranscriptionStream,
        speaker: SpeechProvider,
        policy: VoicePolicy,
        json_sink: JsonSink,
        audio_sink: AudioSink,
        submit_task: SubmitTask,
        cancel_task: CancelTask,
        wait_task: WaitTask,
    ) -> None:
        self.stream, self.speaker, self.policy = stream, speaker, policy
        self.json_sink, self.audio_sink = json_sink, audio_sink
        self.submit_task, self.cancel_task, self.wait_task = submit_task, cancel_task, wait_task
        self.stopped = False
        self.generation = 0
        self.turn_bytes = 0
        self.active_task_id: UUID | None = None
        self._event_task: asyncio.Task[None] | None = None
        self._speech_task: asyncio.Task[None] | None = None
        self._result_task: asyncio.Task[None] | None = None
        self._speech_generation = 0

    async def start(self) -> None:
        await self.stream.start()
        self._event_task = asyncio.create_task(self._pump_transcripts())
        await self.json_sink({"type": "voice.session.ready", "generation": self.generation})

    async def append(self, audio: bytes) -> None:
        if self.stopped:
            raise VoicePolicyError("Voice session is stopped")
        if not audio or len(audio) > self.policy.max_frame_bytes:
            raise VoicePolicyError("Audio frame is empty or too large")
        if len(audio) % 2:
            raise VoicePolicyError("PCM16 audio frames must contain complete samples")
        if self.turn_bytes + len(audio) > self.policy.max_turn_bytes:
            raise VoicePolicyError("Audio turn exceeds configured limit")
        if self._speech_task is not None and not self._speech_task.done():
            await self.interrupt()
        self.turn_bytes += len(audio)
        await self.stream.append(audio)

    async def commit(self, *, replace_active: bool = False) -> None:
        if self.stopped:
            raise VoicePolicyError("Voice session is stopped")
        if self.turn_bytes == 0:
            raise VoicePolicyError("Cannot commit an empty audio turn")
        if replace_active and self.active_task_id is not None:
            await self.cancel_task(self.active_task_id)
            await self.json_sink(
                {"type": "voice.objective.replaced", "task_id": str(self.active_task_id)}
            )
            self.active_task_id = None
        self.turn_bytes = 0
        await self.stream.commit()

    async def interrupt(self) -> None:
        self._speech_generation += 1
        if self._speech_task is not None and not self._speech_task.done():
            self._speech_task.cancel()
            await asyncio.gather(self._speech_task, return_exceptions=True)
            await self.json_sink({"type": "voice.speech.interrupted"})

    async def stop(self) -> None:
        self.stopped = True
        self.generation += 1
        self.turn_bytes = 0
        await self.interrupt()
        if self.active_task_id is not None:
            await self.cancel_task(self.active_task_id)
            self.active_task_id = None
        await self.json_sink({"type": "voice.session.stopped", "generation": self.generation})

    async def resume(self) -> None:
        self.stopped = False
        self.generation += 1
        await self.json_sink({"type": "voice.session.resumed", "generation": self.generation})

    async def _pump_transcripts(self) -> None:
        async for event in self.stream.events():
            if event.kind == "delta":
                await self.json_sink({"type": "voice.transcript.delta", "text": event.text})
            elif event.kind == "error":
                await self.json_sink({"type": "voice.error", "message": event.text})
            elif event.text.strip() and not self.stopped:
                await self.json_sink({"type": "voice.transcript.completed", "text": event.text})
                task_id = await self.submit_task(event.text.strip())
                self.active_task_id = task_id
                await self.json_sink(
                    {
                        "type": "voice.acknowledgment",
                        "task_id": str(task_id),
                        "text": "I’m on it.",
                    }
                )
                self._speech_task = asyncio.create_task(self._speak("I’m on it.", "acknowledgment"))
                self._result_task = asyncio.create_task(
                    self._complete_task(task_id, self.generation)
                )

    async def _complete_task(self, task_id: UUID, generation: int) -> None:
        message = await self.wait_task(task_id)
        if self.active_task_id != task_id or self.stopped or self.generation != generation:
            return
        await self.json_sink(
            {"type": "voice.task.completed", "task_id": str(task_id), "text": message}
        )
        speech_generation = self._speech_generation
        if self._speech_task is not None:
            await asyncio.gather(self._speech_task, return_exceptions=True)
        if self._speech_generation != speech_generation:
            return
        self._speech_task = asyncio.create_task(self._speak(message, "completion"))

    async def _speak(self, text: str, purpose: str) -> None:
        await self.json_sink({"type": "voice.speech.started", "purpose": purpose})
        async for chunk in self.speaker.synthesize(text):
            await self.audio_sink(chunk)
        await self.json_sink({"type": "voice.speech.completed", "purpose": purpose})

    async def close(self) -> None:
        for task in (self._speech_task, self._result_task, self._event_task):
            if task is not None:
                task.cancel()
        await asyncio.gather(
            *(
                task
                for task in (self._speech_task, self._result_task, self._event_task)
                if task is not None
            ),
            return_exceptions=True,
        )
        await self.stream.close()
