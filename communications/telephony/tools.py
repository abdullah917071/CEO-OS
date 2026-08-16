"""Telephony capability tools for the CEO OS capability registry."""

from __future__ import annotations

import dataclasses
from typing import Any

from communications.telephony.manager import CallManager
from core.contracts import CapabilitySpec, RiskLevel, ToolResult


class OutboundCallTool:
    """Capability tool to place an outbound phone call and accomplish a conversation goal."""

    def __init__(self, manager: CallManager) -> None:
        self._manager = manager

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="telephony.call.outbound",
            description="Place an outbound phone call to accomplish a conversation objective",
            input_schema={
                "type": "object",
                "properties": {
                    "to_number": {
                        "type": "string",
                        "description": (
                            "Destination phone number in E.164 format (e.g. +14155550100)"
                        ),
                    },
                    "objective": {
                        "type": "string",
                        "description": (
                            "Clear goal for the call (e.g. ask opening hours, book table)"
                        ),
                    },
                    "from_number": {
                        "type": "string",
                        "description": "Optional caller ID number",
                    },
                },
                "required": ["to_number", "objective"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:telephony",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        to_number = str(arguments.get("to_number", "")).strip()
        objective = str(arguments.get("objective", "")).strip()
        from_number = arguments.get("from_number")

        record = await self._manager.initiate_call(
            to_number=to_number,
            objective=objective,
            from_number=str(from_number) if from_number else None,
            idempotency_key=idempotency_key,
        )

        summary_dict = dataclasses.asdict(record.summary) if record.summary else {}
        turns_dict = [dataclasses.asdict(t) for t in record.turns]

        evidence_msg = (
            f"Placed outbound call to {to_number} (duration: {record.duration_seconds}s, "
            f"status: {record.status.value}). "
            f"Summary: {record.summary.summary_text if record.summary else 'Completed'}"
        )

        return ToolResult(
            output={
                "call_id": record.id,
                "to_number": record.to_number,
                "status": record.status.value,
                "duration_seconds": record.duration_seconds,
                "summary": summary_dict,
                "extracted_data": record.extracted_data,
                "transcript": turns_dict,
                "cost_units": record.cost_units,
            },
            evidence=[evidence_msg],
        )


class CallStatusTool:
    """Capability tool to inspect call status and transcript turns."""

    def __init__(self, manager: CallManager) -> None:
        self._manager = manager

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="telephony.call.status",
            description="Inspect the status and transcript of a phone call",
            input_schema={
                "type": "object",
                "properties": {
                    "call_id": {"type": "string", "description": "Call ID to check"},
                },
                "required": ["call_id"],
            },
            risk=RiskLevel.READ,
            source="integration:telephony",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        call_id = str(arguments.get("call_id", ""))
        record = await self._manager.get_call(call_id)
        if record is None:
            raise ValueError(f"Call record not found: {call_id}")

        return ToolResult(
            output={
                "call_id": record.id,
                "to_number": record.to_number,
                "status": record.status.value,
                "duration_seconds": record.duration_seconds,
                "turns_count": len(record.turns),
            },
            evidence=[f"Retrieved status for call {call_id}: {record.status.value}"],
        )


class TerminateCallTool:
    """Capability tool to hang up or terminate an active call."""

    def __init__(self, manager: CallManager) -> None:
        self._manager = manager

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="telephony.call.terminate",
            description="Hang up or terminate an active phone call",
            input_schema={
                "type": "object",
                "properties": {
                    "call_id": {"type": "string", "description": "Call ID to hang up"},
                },
                "required": ["call_id"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:telephony",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        call_id = str(arguments.get("call_id", ""))
        record = await self._manager.terminate_call(call_id)
        return ToolResult(
            output={"call_id": record.id, "status": record.status.value},
            evidence=[f"Terminated phone call {call_id}"],
        )
