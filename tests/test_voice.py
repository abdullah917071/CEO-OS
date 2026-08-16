from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

import pytest

from voice.providers import Utf8VoiceProvider
from voice.runtime import VoicePolicy, VoicePolicyError, VoiceRuntime


class SlowSpeechProvider(Utf8VoiceProvider):
    async def synthesize(self, text: str) -> Any:
        for chunk in (b"one", b"two"):
            await asyncio.sleep(0.05)
            yield chunk


async def wait_for_event(events: list[dict[str, Any]], event_type: str) -> dict[str, Any]:
    for _ in range(100):
        for event in events:
            if event.get("type") == event_type:
                return event
        await asyncio.sleep(0.01)
    raise AssertionError(f"Missing event: {event_type}")


def json_collector(events: list[dict[str, Any]]) -> Any:
    async def collect(event: dict[str, Any]) -> None:
        events.append(event)

    return collect


def audio_collector(audio: list[bytes]) -> Any:
    async def collect(chunk: bytes) -> None:
        audio.append(chunk)

    return collect


@pytest.mark.asyncio
async def test_voice_streams_transcript_into_durable_task_and_speech() -> None:
    provider = Utf8VoiceProvider()
    runtime = VoiceRuntime(provider, provider, VoicePolicy(enabled=True))
    events: list[dict[str, Any]] = []
    audio: list[bytes] = []
    submitted: list[str] = []
    task_id = uuid4()

    async def submit(text: str) -> UUID:
        submitted.append(text)
        return task_id

    async def cancel(_: UUID) -> None:
        raise AssertionError("Task should not be cancelled")

    async def wait(_: UUID) -> str:
        return "Completed safely."

    session = await runtime.open_session(
        json_collector(events), audio_collector(audio), submit, cancel, wait
    )
    await session.append(b"hello!")
    await session.commit()
    completed = await wait_for_event(events, "voice.task.completed")
    await wait_for_event(events, "voice.speech.completed")

    assert submitted == ["hello!"]
    assert completed["task_id"] == str(task_id)
    assert any(event["type"] == "voice.transcript.delta" for event in events)
    assert any(event["type"] == "voice.acknowledgment" for event in events)
    assert b"".join(audio).startswith(b"I")
    assert runtime.status()["retention"] == "none"
    await runtime.close_session(session)


@pytest.mark.asyncio
async def test_voice_stop_cancels_active_task_blocks_audio_and_resume_does_not_replay() -> None:
    provider = Utf8VoiceProvider()
    runtime = VoiceRuntime(provider, provider, VoicePolicy(enabled=True))
    events: list[dict[str, Any]] = []
    cancelled: list[UUID] = []
    task_id = uuid4()
    release = asyncio.Event()

    async def submit(_: str) -> UUID:
        return task_id

    async def cancel(value: UUID) -> None:
        cancelled.append(value)

    async def wait(_: UUID) -> str:
        await release.wait()
        return "Too late"

    session = await runtime.open_session(
        json_collector(events), lambda _: asyncio.sleep(0), submit, cancel, wait
    )
    await session.append(b"first!")
    await session.commit()
    await wait_for_event(events, "voice.acknowledgment")
    await session.stop()
    assert cancelled == [task_id]
    with pytest.raises(VoicePolicyError, match="stopped"):
        await session.append(b"second")
    await session.resume()
    release.set()
    await asyncio.sleep(0.02)
    assert not any(event["type"] == "voice.task.completed" for event in events)
    assert session.generation == 2
    await runtime.close_session(session)


@pytest.mark.asyncio
async def test_voice_replacement_and_audio_bounds_fail_closed() -> None:
    provider = Utf8VoiceProvider()
    runtime = VoiceRuntime(
        provider,
        provider,
        VoicePolicy(enabled=True, max_frame_bytes=8, max_turn_bytes=8),
    )
    events: list[dict[str, Any]] = []
    cancelled: list[UUID] = []
    ids = iter((uuid4(), uuid4()))

    async def submit(_: str) -> UUID:
        return next(ids)

    async def cancel(value: UUID) -> None:
        cancelled.append(value)

    session = await runtime.open_session(
        json_collector(events),
        lambda _: asyncio.sleep(0),
        submit,
        cancel,
        lambda _: asyncio.sleep(60, result="done"),
    )
    with pytest.raises(VoicePolicyError, match="complete samples"):
        await session.append(b"odd")
    with pytest.raises(VoicePolicyError, match="too large"):
        await session.append(b"0123456789")
    await session.append(b"first!")
    await session.commit()
    first = await wait_for_event(events, "voice.acknowledgment")
    await session.append(b"newest")
    await session.commit(replace_active=True)
    await wait_for_event(events, "voice.objective.replaced")
    assert cancelled == [UUID(first["task_id"])]
    await runtime.close_session(session)


@pytest.mark.asyncio
async def test_voice_audio_barge_in_interrupts_active_speech() -> None:
    provider = Utf8VoiceProvider()
    runtime = VoiceRuntime(provider, SlowSpeechProvider(), VoicePolicy(enabled=True))
    events: list[dict[str, Any]] = []
    task_id = uuid4()

    session = await runtime.open_session(
        json_collector(events),
        lambda _: asyncio.sleep(0),
        lambda _: asyncio.sleep(0, result=task_id),
        lambda _: asyncio.sleep(0),
        lambda _: asyncio.sleep(60, result="done"),
    )
    await session.append(b"first!")
    await session.commit()
    await wait_for_event(events, "voice.speech.started")
    await session.append(b"barge!")
    await wait_for_event(events, "voice.speech.interrupted")
    assert not any(
        event["type"] == "voice.speech.completed" and event.get("purpose") == "acknowledgment"
        for event in events
    )
    await runtime.close_session(session)
