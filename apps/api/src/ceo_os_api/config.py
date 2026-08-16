import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CEO_OS_", extra="ignore")

    env: str = "development"
    database_url: str = "sqlite+aiosqlite:///./data/ceo_os.db"
    redis_url: str = "redis://localhost:6379/0"
    workspace_root: Path = Path("./data/workspaces")
    model_provider: str = "openrouter"
    model_name: str = "nvidia/nemotron-3.5-lightning:free"
    openai_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    cors_origins: str = (
        "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003,"
        "http://localhost:3004,http://localhost:3005,http://127.0.0.1:3000,http://127.0.0.1:3001,"
        "http://127.0.0.1:3002,http://127.0.0.1:3003,http://127.0.0.1:3004,http://127.0.0.1:3005"
    )
    computer_helper_path: Path = Path("computer/macos_helper/.build/release/ceo-os-mac-helper")
    computer_effects_enabled: bool = False
    computer_allowed_bundle_ids: str = ""
    browser_enabled: bool = False
    browser_headless: bool = True
    browser_effects_enabled: bool = False
    browser_persistent_profiles_enabled: bool = False
    browser_allowed_origins: str = ""
    browser_browsers_path: Path = Path(".playwright-browsers")
    browser_timeout_ms: int = 10_000
    vision_enabled: bool = False
    vision_effects_enabled: bool = False
    vision_allowed_app_names: str = ""
    vision_foreground_escalation_enabled: bool = False
    voice_enabled: bool = False
    voice_provider: str = "openai"
    voice_transcription_model: str = "gpt-live-transcribe"
    voice_speech_model: str = "gpt-4o-mini-tts"
    voice_name: str = "coral"
    voice_realtime_url: str = "wss://api.openai.com/v1/realtime?intent=transcription"
    voice_api_base_url: str = "https://api.openai.com"
    mcp_servers_config: Path | None = None
    mcp_servers: str = ""
    system_info_integration_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if "PYTEST_CURRENT_TEST" in os.environ:
        settings.model_provider = "deterministic"
    return settings
