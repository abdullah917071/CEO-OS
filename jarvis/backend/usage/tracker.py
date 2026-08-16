"""Usage metrics, session tracking, and cost estimation for Jarvis."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from jarvis.backend.config.database import JarvisDatabase

logger = logging.getLogger(__name__)

# Approximate Gemini Live audio pricing ($0.00015 per audio minute approx)
PRICE_PER_AUDIO_MIN_USD = 0.001


@dataclass(slots=True)
class JarvisUsageStats:
    total_sessions_today: int
    active_minutes_today: float
    user_speech_minutes_today: float
    gemini_speech_minutes_today: float
    total_tool_calls_today: int
    estimated_cost_usd_today: float


class JarvisUsageTracker:
    """Tracks session durations and computes daily/monthly estimated usage."""

    def __init__(self, db: JarvisDatabase) -> None:
        self.db = db

    def record_completed_session(
        self,
        session_id: str,
        started_at: float,
        duration_sec: float,
        user_speech_sec: float,
        gemini_speech_sec: float,
        tool_calls_count: int,
        disconnect_reason: str,
        model_name: str = "gemini-2.0-flash-exp",
    ) -> None:
        """Persist session summary and usage record into SQLite."""
        now_iso = datetime.now(UTC).isoformat()
        start_iso = datetime.fromtimestamp(started_at, UTC).isoformat()
        audio_min = (user_speech_sec + gemini_speech_sec) / 60.0
        est_cost = audio_min * PRICE_PER_AUDIO_MIN_USD

        with self.db._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions (
                    session_id, started_at, ended_at, duration_seconds,
                    user_speech_seconds, gemini_speech_seconds, tool_calls_count, disconnect_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    start_iso,
                    now_iso,
                    duration_sec,
                    user_speech_sec,
                    gemini_speech_sec,
                    tool_calls_count,
                    disconnect_reason,
                ),
            )
            conn.execute(
                """
                INSERT INTO usage_records (
                    session_id, timestamp, model_name, input_audio_seconds,
                    output_audio_seconds, estimated_cost_usd, tool_calls_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    now_iso,
                    model_name,
                    user_speech_sec,
                    gemini_speech_sec,
                    est_cost,
                    tool_calls_count,
                ),
            )
            conn.commit()

        logger.info(
            "Recorded session %s (dur: %.1fs, user: %.1fs, gemini: %.1fs, tools: %d, cost: $%.4f)",
            session_id,
            duration_sec,
            user_speech_sec,
            gemini_speech_sec,
            tool_calls_count,
            est_cost,
        )

    def get_today_stats(self) -> JarvisUsageStats:
        """Calculate aggregated metrics for today."""
        today_prefix = datetime.now(UTC).strftime("%Y-%m-%d")
        with self.db._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as count,
                    COALESCE(SUM(duration_seconds), 0) as total_dur,
                    COALESCE(SUM(user_speech_seconds), 0) as total_user,
                    COALESCE(SUM(gemini_speech_seconds), 0) as total_gemini,
                    COALESCE(SUM(tool_calls_count), 0) as total_tools
                FROM sessions
                WHERE started_at LIKE ?
                """,
                (f"{today_prefix}%",),
            )
            row = cursor.fetchone()
            if not row:
                return JarvisUsageStats(0, 0.0, 0.0, 0.0, 0, 0.0)

            total_dur_min = row["total_dur"] / 60.0
            user_min = row["total_user"] / 60.0
            gemini_min = row["total_gemini"] / 60.0
            est_cost = (user_min + gemini_min) * PRICE_PER_AUDIO_MIN_USD

            return JarvisUsageStats(
                total_sessions_today=int(row["count"]),
                active_minutes_today=round(total_dur_min, 1),
                user_speech_minutes_today=round(user_min, 1),
                gemini_speech_minutes_today=round(gemini_min, 1),
                total_tool_calls_today=int(row["total_tools"]),
                estimated_cost_usd_today=round(est_cost, 4),
            )

    def list_recent_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve recent session history."""
        with self.db._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT session_id, started_at, ended_at, duration_seconds,
                       user_speech_seconds, gemini_speech_seconds,
                       tool_calls_count, disconnect_reason
                FROM sessions
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
