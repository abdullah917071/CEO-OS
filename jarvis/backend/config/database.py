"""SQLite database engine for Jarvis settings, sessions, tool permissions, and logs."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jarvis.backend.config.settings import AudioConfig, GeminiConfig, JarvisSettings, WakeWordConfig

logger = logging.getLogger(__name__)


class JarvisDatabase:
    """SQLite database manager for persistent Jarvis configurations, sessions, and telemetry."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or Path("./data/jarvis/jarvis.sqlite3")
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            fallback = Path("./data/jarvis/jarvis.sqlite3")
            fallback.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = fallback
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tool_permissions (
                    tool_name TEXT PRIMARY KEY,
                    mode TEXT NOT NULL, -- ALLOW, ASK, DENY
                    description TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    duration_seconds REAL DEFAULT 0,
                    user_speech_seconds REAL DEFAULT 0,
                    gemini_speech_seconds REAL DEFAULT 0,
                    tool_calls_count INTEGER DEFAULT 0,
                    disconnect_reason TEXT,
                    transcript_summary TEXT
                );

                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    input_audio_seconds REAL DEFAULT 0,
                    output_audio_seconds REAL DEFAULT 0,
                    estimated_cost_usd REAL DEFAULT 0,
                    tool_calls_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT NOT NULL
                );
                """
            )
            conn.commit()

    def save_settings(self, settings: JarvisSettings) -> None:
        """Persist full Jarvis configuration to SQLite."""
        now = datetime.now(UTC).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                ("gemini", json.dumps(asdict(settings.gemini)), now),
            )
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                ("wakeword", json.dumps(asdict(settings.wakeword)), now),
            )
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                ("audio", json.dumps(asdict(settings.audio)), now),
            )
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                (
                    "general",
                    json.dumps(
                        {
                            "launch_at_login": settings.launch_at_login,
                            "start_wake_listener_on_boot": settings.start_wake_listener_on_boot,
                            "store_voice_transcripts": settings.store_voice_transcripts,
                        }
                    ),
                    now,
                ),
            )
            conn.commit()

    def load_settings(self) -> JarvisSettings:
        """Load stored configurations with safe defaults."""
        settings = JarvisSettings()
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT key, value FROM settings")
                rows = {row["key"]: row["value"] for row in cursor.fetchall()}

                if "gemini" in rows:
                    g_data = json.loads(rows["gemini"])
                    settings.gemini = GeminiConfig(**g_data)
                if "wakeword" in rows:
                    w_data = json.loads(rows["wakeword"])
                    settings.wakeword = WakeWordConfig(**w_data)
                if "audio" in rows:
                    a_data = json.loads(rows["audio"])
                    settings.audio = AudioConfig(**a_data)
                if "general" in rows:
                    gen = json.loads(rows["general"])
                    settings.launch_at_login = gen.get("launch_at_login", False)
                    settings.start_wake_listener_on_boot = gen.get(
                        "start_wake_listener_on_boot", True
                    )
                    settings.store_voice_transcripts = gen.get("store_voice_transcripts", False)
        except Exception as exc:
            logger.warning("Error loading settings from DB, using defaults: %s", exc)
        return settings

    def get_tool_permissions(self) -> dict[str, str]:
        """Fetch tool permission mapping."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT tool_name, mode FROM tool_permissions")
            return {row["tool_name"]: row["mode"] for row in cursor.fetchall()}

    def set_tool_permission(self, tool_name: str, mode: str, description: str = "") -> None:
        """Update tool permission (ALLOW, ASK, DENY)."""
        now = datetime.now(UTC).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO tool_permissions (
                    tool_name, mode, description, updated_at
                ) VALUES (?, ?, ?, ?)
                """,
                (tool_name, mode.upper(), description, now),
            )
            conn.commit()

    def log_event(self, level: str, event_type: str, message: str) -> None:
        """Record structured event in log table."""
        now = datetime.now(UTC).isoformat()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "INSERT INTO logs (timestamp, level, event_type, message) VALUES (?, ?, ?, ?)",
                    (now, level, event_type, message),
                )
                conn.commit()
        except Exception as exc:
            logger.error("Failed to write log to SQLite: %s", exc)

    def get_recent_logs(self, limit: int = 50) -> Sequence[dict[str, Any]]:
        """Fetch latest event logs."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT timestamp, level, event_type, message FROM logs ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
