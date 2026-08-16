"""State machine definitions for Jarvis lifecycle."""

from __future__ import annotations

from enum import StrEnum


class JarvisState(StrEnum):
    STARTING = "STARTING"
    IDLE_WAKE_WORD = "IDLE_WAKE_WORD"
    WAKE_DETECTED = "WAKE_DETECTED"
    CONNECTING = "CONNECTING"
    ACTIVE = "ACTIVE"
    ENDING = "ENDING"
    ERROR = "ERROR"
