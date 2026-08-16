# Milestone 7 — Voice V1 Execution Plan

`PLANS.md` remains the immutable governing roadmap. This file defines the concrete delivery and
acceptance contract for its Voice V1 milestone.

Status: implemented with deterministic and transport verification on 2026-08-15. Live OpenAI
speech verification and the roadmap's physical microphone/Chrome acceptance remain pending because
no provider credential is configured and containerized CEO OS cannot yet control the macOS host.

## Objective

Add a provider-neutral, streamed voice channel over the existing durable CEO task runtime. Voice
transports audio and session control; it does not become a second brain or bypass task policy.

## Acceptance criteria

- Client audio is bounded 24 kHz mono PCM16 and forwarded incrementally without persistence.
- Transcription deltas and committed utterances are distinct events.
- A committed utterance creates a normal durable CEO task and emits an immediate acknowledgment.
- Task completion is reported separately and synthesized as streamed PCM output.
- Barge-in cancels active synthesis before accepting the new turn.
- Stop invalidates the session generation, cancels synthesis, requests cancellation of the active
  task, blocks new audio, and never replays buffered data on resume.
- Objective replacement cancels the active non-terminal task before creating the replacement.
- Provider secrets never appear in status, events, transcripts, or logs.
- A deterministic fake provider verifies streaming, interruption, stop/resume, replacement, bounds,
  and WebSocket framing without external credentials.
- A configured OpenAI adapter uses realtime transcription and streaming speech while the default
  container truthfully reports voice disabled when credentials are absent.
- Existing tests, typing, lint, lock, dashboard, and container checks remain green.

## Verification result

- A loopback-only API instance accepted binary audio over `/ws/voice`, emitted transcript delta and
  completion events, created a durable CEO task, separated acknowledgment from task completion, and
  streamed both acknowledgment and completion audio as binary frames.
- Automated tests verify barge-in, speech cancellation, stop/resume generation invalidation, active
  task cancellation, objective replacement, no replay, audio bounds, disabled-provider behavior,
  and content-free status.
- The production adapter follows the documented realtime transcription event contract and streams
  PCM speech through the Speech API. It was not called without an owner-supplied credential.
- The rebuilt container is ready and truthfully reports voice disabled/unavailable with zero audio
  retention by default.
