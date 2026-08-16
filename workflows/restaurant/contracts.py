"""Contracts, request, and result models for the Restaurant Booking Workflow."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReservationRequest:
    """Input parameters for a restaurant reservation request."""

    restaurant_name: str
    party_size: int = 2
    date: str = "today"
    time: str = "19:00"
    flexibility_minutes: int = 30
    special_requests: str = ""
    booking_name: str = "Abdullah"
    location_bias: str = "San Francisco"


@dataclass
class ReservationResult:
    """Structured outcome and evidence trail from the restaurant booking workflow."""

    status: str  # "confirmed" | "unavailable" | "failed"
    restaurant_name: str
    address: str
    phone_number: str
    confirmed_time: str
    party_size: int
    booking_name: str
    call_id: str | None = None
    calendar_event_id: str | None = None
    memory_id: str | None = None
    summary: str = ""
    evidence: list[str] = field(default_factory=list)
