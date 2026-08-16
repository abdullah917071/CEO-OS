"""Contracts, schemas, and policy definitions for the Telephony subsystem."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CallStatus(StrEnum):
    """Lifecycle states of a telephone call."""

    QUEUED = "queued"
    RINGING = "ringing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BUSY = "busy"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CallDirection(StrEnum):
    """Direction of the phone call."""

    OUTBOUND = "outbound"
    INBOUND = "inbound"


@dataclass(frozen=True)
class CallTranscriptTurn:
    """A single turn in a telephone dialogue."""

    speaker: str  # "agent" | "party" | "system"
    text: str
    timestamp_ms: int = 0
    confidence: float = 1.0


@dataclass(frozen=True)
class CallSummary:
    """Structured synthesis of a completed telephone call."""

    call_id: str
    objective_completed: bool
    summary_text: str
    action_items: list[str] = field(default_factory=list)
    extracted_answers: dict[str, str] = field(default_factory=dict)
    sentiment: str = "neutral"


@dataclass
class CallRecord:
    """Complete record of a phone call including metadata and transcript."""

    id: str
    provider_call_id: str
    to_number: str
    from_number: str
    objective: str
    status: CallStatus = CallStatus.QUEUED
    direction: CallDirection = CallDirection.OUTBOUND
    duration_seconds: int = 0
    started_at: str | None = None
    ended_at: str | None = None
    turns: list[CallTranscriptTurn] = field(default_factory=list)
    summary: CallSummary | None = None
    extracted_data: dict[str, str] = field(default_factory=dict)
    cost_units: float = 0.0
    recording_url: str | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True)
class TelephonyPolicy:
    """Safety and resource bounds for telephone calls."""

    allowed_prefixes: tuple[str, ...] = ("+1", "+44", "+91")
    max_duration_seconds: int = 300
    recording_consent_required: bool = False
    cost_ceiling_per_call: float = 5.0
    require_e164: bool = True
