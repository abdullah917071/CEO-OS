"""Capability tools for the Restaurant Booking workflow."""

from __future__ import annotations

import dataclasses
from typing import Any

from core.contracts import CapabilitySpec, RiskLevel, ToolResult
from workflows.restaurant.contracts import ReservationRequest
from workflows.restaurant.workflow import RestaurantBookingWorkflow


class RestaurantBookingTool:
    """Capability tool providing the end-to-end restaurant reservation workflow."""

    def __init__(self, workflow: RestaurantBookingWorkflow) -> None:
        self._workflow = workflow

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="workflow.restaurant.book",
            description=(
                "Autonomous restaurant booking workflow: search places, place telephone call, "
                "schedule calendar event, save episodic memory, and generate executive report"
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "restaurant_name": {
                        "type": "string",
                        "description": "Name of the restaurant to find and book",
                    },
                    "party_size": {
                        "type": "integer",
                        "description": "Number of guests in party",
                        "default": 2,
                    },
                    "date": {
                        "type": "string",
                        "description": "Desired reservation date (e.g. today, 2026-08-16)",
                        "default": "today",
                    },
                    "time": {
                        "type": "string",
                        "description": "Desired reservation time (e.g. 7:00 PM, 19:00)",
                        "default": "19:00",
                    },
                    "booking_name": {
                        "type": "string",
                        "description": "Name under which to book the reservation",
                        "default": "Abdullah",
                    },
                    "location_bias": {
                        "type": "string",
                        "description": "City or neighborhood for location search",
                        "default": "San Francisco",
                    },
                },
                "required": ["restaurant_name"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:workflow",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        restaurant_name = str(arguments.get("restaurant_name", "")).strip()
        party_size = int(arguments.get("party_size", 2))
        date = str(arguments.get("date", "today"))
        time_str = str(arguments.get("time", "19:00"))
        booking_name = str(arguments.get("booking_name", "Abdullah"))
        location_bias = str(arguments.get("location_bias", "San Francisco"))
        special_requests = str(arguments.get("special_requests", ""))

        req = ReservationRequest(
            restaurant_name=restaurant_name,
            party_size=party_size,
            date=date,
            time=time_str,
            booking_name=booking_name,
            location_bias=location_bias,
            special_requests=special_requests,
        )

        result = await self._workflow.execute(req, idempotency_key=idempotency_key)
        return ToolResult(
            output=dataclasses.asdict(result),
            evidence=result.evidence,
        )
