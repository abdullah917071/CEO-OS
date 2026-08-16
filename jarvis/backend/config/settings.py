"""Configuration settings and defaults for Jarvis Voice Assistant."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class GeminiConfig:
    project_id: str = "project-b92aa8b2-0d4c-4606-834"
    location: str = "us-central1"
    model_name: str = "gemini-2.0-flash-exp"
    voice_name: str = "Puck"  # Puck, Charon, Kore, Fenrir, Aoede
    temperature: float = 0.6
    system_instruction: str = (
        "You are Jarvis, a realtime desktop AI assistant for macOS.\n"
        "Speak naturally, clearly, and concisely.\n"
        "Do not unnecessarily describe actions before performing them.\n"
        "When the user requests an action that can be accomplished "
        "using an available tool, use the tool.\n"
        "Maintain context throughout the active voice session.\n"
        "You may be interrupted at any time. If the user speaks while you "
        "are responding, prioritize their latest instruction.\n"
        "For simple confirmations, respond briefly.\n"
        "Responses must sound natural and conversational when spoken aloud."
    )
    inactivity_timeout_seconds: int = 60
    max_session_duration_minutes: int = 15
    context_compression: bool = True
    auto_reconnect: bool = True
    session_ending_phrases: list[str] = field(
        default_factory=lambda: [
            "thanks jarvis",
            "thank you jarvis",
            "that's all",
            "thats all",
            "go to sleep",
            "stop listening",
            "goodbye",
            "bye jarvis",
            "sleep",
        ]
    )


@dataclass(slots=True)
class WakeWordConfig:
    wake_word: str = "Jarvis"
    model_name: str = "jarvis.onnx"
    sensitivity: float = 0.5
    require_wake_word: bool = True
    activation_sound: bool = True
    activation_phrase: str = "Yes?"
    pre_roll_buffer_ms: int = 500  # Rolling buffer to capture words immediately following wake word


@dataclass(slots=True)
class AudioConfig:
    input_device: str = "default"
    output_device: str = "default"
    input_sample_rate: int = 16000  # 16kHz PCM16 for Gemini Live input
    output_sample_rate: int = 24000  # 24kHz PCM16 for Gemini Live output
    channels: int = 1
    chunk_size_ms: int = 100  # 100ms chunks for low-latency streaming
    echo_cancellation: bool = True
    noise_suppression: bool = True
    auto_gain_control: bool = True
    microphone_gain: float = 1.0
    output_volume: float = 1.0


def _get_default_data_dir() -> Path:
    target = Path.home() / "Library" / "Application Support" / "Jarvis"
    try:
        target.mkdir(parents=True, exist_ok=True)
        return target
    except Exception:
        fallback = Path("./data/jarvis")
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def _get_default_db_path() -> Path:
    return _get_default_data_dir() / "jarvis.sqlite3"


def _get_default_sa_path() -> Path:
    preferred = _get_default_data_dir() / "service_account.json"
    if preferred.exists():
        return preferred
    fallback = Path("./data/secrets/jarvis_service_account.json")
    return fallback if fallback.exists() else preferred


@dataclass(slots=True)
class JarvisSettings:
    app_data_dir: Path = field(default_factory=_get_default_data_dir)
    database_path: Path = field(default_factory=_get_default_db_path)
    service_account_path: Path = field(default_factory=_get_default_sa_path)
    launch_at_login: bool = False
    start_wake_listener_on_boot: bool = True
    store_voice_transcripts: bool = False
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    wakeword: WakeWordConfig = field(default_factory=WakeWordConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)

    def ensure_directories(self) -> None:
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        # Ensure local fallback directory also exists
        local_data = Path("./data/jarvis")
        local_data.mkdir(parents=True, exist_ok=True)
