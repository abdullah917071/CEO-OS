"""Call Manager: coordinates telephony providers, lifecycle, policies, and memory retention."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from communications.telephony.contracts import (
    CallRecord,
    CallStatus,
    TelephonyPolicy,
)
from communications.telephony.provider import (
    DeterministicTelephonyProvider,
    TelephonyProvider,
)
from memory.service import MemoryService, Provenance

logger = logging.getLogger(__name__)


class CallManager:
    """Manages phone calls across provider adapters and records outcomes into long-term memory."""

    def __init__(
        self,
        provider: TelephonyProvider | None = None,
        memory_service: MemoryService | None = None,
        policy: TelephonyPolicy | None = None,
        default_caller_id: str = "+1-415-555-0199",
    ) -> None:
        self._provider = provider or DeterministicTelephonyProvider(policy)
        self._memory_service = memory_service
        self._policy = policy or TelephonyPolicy()
        self._default_caller_id = default_caller_id
        self._call_history: dict[str, CallRecord] = {}

    @property
    def provider(self) -> TelephonyProvider:
        return self._provider

    @property
    def policy(self) -> TelephonyPolicy:
        return self._policy

    def _validate_number(self, phone_number: str) -> None:
        clean = phone_number.strip()
        if not clean:
            raise ValueError("Phone number cannot be empty")
        if self._policy.require_e164 and not clean.startswith("+"):
            raise ValueError(f"Phone number '{phone_number}' must start with '+' (E.164 format)")
        if self._policy.allowed_prefixes:
            if not any(clean.startswith(prefix) for prefix in self._policy.allowed_prefixes):
                prefixes = self._policy.allowed_prefixes
                raise ValueError(
                    f"Destination '{phone_number}' not in allowed prefixes: {prefixes}"
                )

    async def initiate_call(
        self,
        to_number: str,
        objective: str,
        *,
        from_number: str | None = None,
        idempotency_key: str | None = None,
    ) -> CallRecord:
        """Initiate an outbound telephone call with the designated objective."""
        self._validate_number(to_number)
        caller_id = from_number or self._default_caller_id

        record = await self._provider.initiate_call(
            to_number=to_number,
            from_number=caller_id,
            objective=objective,
            idempotency_key=idempotency_key,
        )
        self._call_history[record.id] = record

        # Automatically record outcome into long-term episodic memory if memory_service is present
        if self._memory_service and record.summary:
            await self._record_call_memory(record)

        return record

    async def _record_call_memory(self, record: CallRecord) -> None:
        """Persist summary and extracted knowledge into episodic memory."""
        if not self._memory_service or not record.summary:
            return
        now = datetime.now(UTC)
        provenance = Provenance(
            source_type="telephony_call",
            source_uri=f"tel:{record.to_number}",
            detail=f"Outbound call ID: {record.id}, duration: {record.duration_seconds}s",
            observed_at=now,
        )
        content = (
            f"Phone call to {record.to_number} regarding '{record.objective}'. "
            f"Summary: {record.summary.summary_text}"
        )
        try:
            await self._memory_service.create(
                memory_type="episodic",
                content=content,
                provenance=provenance,
                subject_key=f"phone:{record.to_number}",
                confidence=0.95,
                importance=0.85,
                dedupe_key=f"mem_call_{record.id}",
                attributes={
                    "call_id": record.id,
                    "to_number": record.to_number,
                    "duration_seconds": record.duration_seconds,
                    "extracted_data": record.extracted_data,
                },
            )
            logger.info("Recorded episodic memory for phone call %s", record.id)
        except Exception:
            logger.warning("Failed to record memory for call %s", record.id, exc_info=True)

    async def get_call(self, call_id: str) -> CallRecord | None:
        """Retrieve call record by ID."""
        if call_id in self._call_history:
            return self._call_history[call_id]
        try:
            record = await self._provider.get_call_status(call_id)
            self._call_history[record.id] = record
            return record
        except Exception:
            return None

    async def list_calls(self, limit: int = 50) -> list[CallRecord]:
        """List call history, newest first."""
        calls = list(self._call_history.values())
        return sorted(calls, key=lambda c: c.started_at or "", reverse=True)[:limit]

    async def terminate_call(self, call_id: str) -> CallRecord:
        """Terminate an active call."""
        record = await self._provider.terminate_call(call_id)
        record.status = CallStatus.COMPLETED
        self._call_history[record.id] = record
        return record
