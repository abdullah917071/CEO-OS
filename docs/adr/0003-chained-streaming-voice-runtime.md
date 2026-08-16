# ADR 0003 — Chained streaming voice runtime

Status: accepted on 2026-08-15.

## Context

CEO OS already owns durable text planning, capabilities, memory, cancellation, and evidence. A
speech-to-speech agent would duplicate or bypass those boundaries. Voice V1 needs incremental
transcription, streamed speech, and interruption while preserving the existing CEO runtime.

## Decision

Use a chained `streaming STT → existing CEO runtime → streaming TTS` architecture behind
project-owned protocols. The first production adapter uses OpenAI realtime transcription over a
server WebSocket and streaming Speech API PCM output. Add `websockets` as a direct, version-bounded
dependency; continue using the existing `httpx` dependency for speech streaming.

The browser/client connects only to CEO OS. Provider credentials remain server-side. Audio is
24 kHz mono PCM16, bounded per frame and turn, and not retained in V1. Tests use deterministic fake
providers and never require network access or credentials.

## Consequences

- The durable CEO planner remains the sole authority and provider SDKs do not enter the kernel.
- Transcription and synthesis can be replaced independently.
- Chained operation adds a boundary between transcription, reasoning, and speech, but makes policy,
  transcripts, task identity, cancellation, and verification explicit.
- A real provider smoke test requires an owner-supplied credential and is not faked when absent.

