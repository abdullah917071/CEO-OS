# Voice

Voice is an owner channel over the same CEO/task runtime, not a separate brain. The target pipeline is VAD, streaming speech-to-text, incremental CEO reasoning, and streaming text-to-speech.

The session contract supports barge-in, interruption, pause, resume, cancellation, objective changes, push-to-talk, and eventual wake-word activation. Acknowledgment is separated from task completion so long-running work remains conversational without making false claims.

Audio retention, speaker identity, recording consent, provider routing, and local/cloud boundaries are explicit policies. Continuous wake-word listening should use a small local detector.

## Voice V1

Milestone 7 uses a chained pipeline because CEO OS already owns a durable text runtime:

```text
24 kHz mono PCM16
  → streaming transcription
  → existing CEO task runtime
  → streaming PCM speech
```

The provider boundary is defined in `voice/contracts.py`. The first production adapters use
OpenAI realtime transcription and the streaming Speech API; deterministic providers exercise the
complete control loop without credentials. Provider credentials remain server-side and are never
included in voice status or events.

Clients connect to `/ws/voice`. Binary messages are PCM16 audio frames. JSON control messages are:

- `voice.turn.commit` with optional `replace_active: true`
- `voice.interrupt`
- `voice.stop`
- `voice.resume`

The server sends JSON transcript, acknowledgment, task, speech lifecycle, interruption, and error
events. Speech bytes are separate binary WebSocket messages. Acknowledgment never implies task
completion.

V1 is push-to-talk with explicit turn commits. It bounds each frame and turn, retains no audio, and
requires complete PCM16 samples. Incoming audio during synthesis performs barge-in. Stop advances a
generation, clears the uncommitted turn, interrupts speech, requests cancellation of the active
durable task, blocks audio, and resume never replays prior input or output.

Voice is disabled by default. It requires `CEO_OS_VOICE_ENABLED=true` and a configured server-side
provider credential. Wake word, automatic VAD, speaker recognition, stored recordings, and a voice
dashboard are intentionally outside V1.
