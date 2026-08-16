"""Data models and message schemas for Gemini Live Bidirectional WebSocket API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# ── Client-to-Server Setup & Messages ───────────────────────────────────────


class GeminiVoiceConfig(BaseModel):
    prebuilt_voice_config: dict[str, str] = Field(default_factory=lambda: {"voice_name": "Puck"})


class GeminiSpeechConfig(BaseModel):
    voice_config: GeminiVoiceConfig = Field(default_factory=GeminiVoiceConfig)


class GeminiGenerationConfig(BaseModel):
    temperature: float = 0.6
    response_modalities: list[str] = Field(default_factory=lambda: ["AUDIO"])
    speech_config: GeminiSpeechConfig = Field(default_factory=GeminiSpeechConfig)


class GeminiFunctionDeclaration(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class GeminiToolDef(BaseModel):
    function_declarations: list[GeminiFunctionDeclaration] = Field(default_factory=list)


class GeminiLiveSetup(BaseModel):
    model: str
    generation_config: GeminiGenerationConfig = Field(default_factory=GeminiGenerationConfig)
    system_instruction: dict[str, Any] | None = None
    tools: list[GeminiToolDef] = Field(default_factory=list)


class GeminiClientSetupMessage(BaseModel):
    setup: GeminiLiveSetup


class GeminiMediaChunk(BaseModel):
    mime_type: str = "audio/pcm;rate=16000"
    data: str  # Base64 encoded PCM16


class GeminiRealtimeInput(BaseModel):
    media_chunks: list[GeminiMediaChunk] = Field(default_factory=list)


class GeminiClientAudioMessage(BaseModel):
    realtime_input: GeminiRealtimeInput


class GeminiFunctionResponse(BaseModel):
    name: str
    response: dict[str, Any]
    id: str | None = None


class GeminiToolResponseMessage(BaseModel):
    tool_response: dict[str, Any]


# ── Server-to-Client Responses ──────────────────────────────────────────────


class GeminiServerContentPart(BaseModel):
    text: str | None = None
    inline_data: dict[str, str] | None = None  # mime_type, data (base64)
    function_call: dict[str, Any] | None = None  # name, args, id


class GeminiModelTurn(BaseModel):
    parts: list[GeminiServerContentPart] = Field(default_factory=list)


class GeminiServerContent(BaseModel):
    model_turn: GeminiModelTurn | None = None
    turn_complete: bool = False
    interrupted: bool = False


class GeminiToolCall(BaseModel):
    function_calls: list[dict[str, Any]] = Field(default_factory=list)


class GeminiServerMessage(BaseModel):
    setup_complete: dict[str, Any] | None = None
    server_content: GeminiServerContent | None = None
    tool_call: GeminiToolCall | None = None
    tool_call_cancellation: dict[str, Any] | None = None
