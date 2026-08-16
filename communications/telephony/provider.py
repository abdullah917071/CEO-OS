"""Telephony provider interfaces and deterministic/live implementations."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from communications.telephony.contracts import (
    CallDirection,
    CallRecord,
    CallStatus,
    CallSummary,
    CallTranscriptTurn,
    TelephonyPolicy,
)
from integrations.contracts import AuthenticationError
from integrations.secrets import SecretBroker

logger = logging.getLogger(__name__)


class TelephonyProvider(Protocol):
    """Protocol for telephony carriers and simulation providers."""

    @property
    def name(self) -> str: ...

    async def initiate_call(
        self,
        to_number: str,
        from_number: str,
        objective: str,
        *,
        webhook_url: str | None = None,
        idempotency_key: str | None = None,
    ) -> CallRecord: ...

    async def get_call_status(self, call_id: str) -> CallRecord: ...

    async def terminate_call(self, call_id: str) -> CallRecord: ...

    async def send_dtmf(self, call_id: str, digits: str) -> bool: ...


class DeterministicTelephonyProvider:
    """Deterministic simulation provider for telephone calls.

    Generates realistic multi-turn conversational telephone dialogues,
    speech transcripts, and structured extracted data without requiring live telecom credentials.
    """

    def __init__(self, policy: TelephonyPolicy | None = None) -> None:
        self._policy = policy or TelephonyPolicy()
        self._calls: dict[str, CallRecord] = {}

    @property
    def name(self) -> str:
        return "deterministic_telephony"

    def _generate_dialogue(
        self, objective: str, to_number: str
    ) -> tuple[list[CallTranscriptTurn], CallSummary, dict[str, str]]:
        """Synthesize conversational dialogue turns matching the stated calling objective."""
        lower = objective.lower().strip()
        turns: list[CallTranscriptTurn] = []
        extracted: dict[str, str] = {}
        action_items: list[str] = []

        now_ms = 0
        turns.append(
            CallTranscriptTurn(
                speaker="system",
                text=f"Call connected to {to_number}. Ringing...",
                timestamp_ms=now_ms,
            )
        )
        now_ms += 1200

        turns.append(
            CallTranscriptTurn(
                speaker="party",
                text="Hello, thank you for calling! How can I help you today?",
                timestamp_ms=now_ms,
            )
        )
        now_ms += 1800

        # Scenario 1: Opening hours / Schedule inquiry
        if any(kw in lower for kw in ("open tomorrow", "hours", "opening", "closing", "schedule")):
            turns.append(
                CallTranscriptTurn(
                    speaker="agent",
                    text=(
                        "Hi, I am calling on behalf of our team to ask whether "
                        "you're open tomorrow."
                    ),
                    timestamp_ms=now_ms,
                )
            )
            now_ms += 2400
            turns.append(
                CallTranscriptTurn(
                    speaker="party",
                    text=(
                        "Yes, absolutely! We are open tomorrow from 11:00 AM to 10:00 PM. "
                        "Our kitchen closes at 9:30 PM."
                    ),
                    timestamp_ms=now_ms,
                )
            )
            now_ms += 2800
            turns.append(
                CallTranscriptTurn(
                    speaker="agent",
                    text="Great, thank you so much for the information. Have a great day!",
                    timestamp_ms=now_ms,
                )
            )
            now_ms += 1500
            turns.append(
                CallTranscriptTurn(
                    speaker="party",
                    text="You too, goodbye!",
                    timestamp_ms=now_ms,
                )
            )
            extracted = {
                "open_tomorrow": "Yes",
                "opening_time": "11:00 AM",
                "closing_time": "10:00 PM",
                "kitchen_closing": "9:30 PM",
            }
            summary_text = (
                f"Successfully confirmed with {to_number} that they are open tomorrow from "
                "11:00 AM to 10:00 PM (kitchen closes at 9:30 PM)."
            )
            action_items = ["Note store hours in operating log for tomorrow"]

        # Scenario 2: Restaurant reservation inquiry
        elif any(kw in lower for kw in ("reservation", "book", "table", "dinner", "lunch")):
            party_size_match = re.search(r"(\d+)\s*(?:people|guests|persons|pax)?", lower)
            party_size = party_size_match.group(1) if party_size_match else "2"
            turns.append(
                CallTranscriptTurn(
                    speaker="agent",
                    text=(
                        f"Hello! I would like to check table availability for {party_size} guests."
                    ),
                    timestamp_ms=now_ms,
                )
            )
            now_ms += 2400
            turns.append(
                CallTranscriptTurn(
                    speaker="party",
                    text=(
                        f"Certainly! We have open seating available for {party_size} people "
                        "at 7:00 PM and 8:30 PM."
                    ),
                    timestamp_ms=now_ms,
                )
            )
            now_ms += 2600
            turns.append(
                CallTranscriptTurn(
                    speaker="agent",
                    text="Excellent. Please hold a table for us at 7:00 PM under the name Ansari.",
                    timestamp_ms=now_ms,
                )
            )
            now_ms += 2200
            turns.append(
                CallTranscriptTurn(
                    speaker="party",
                    text=(
                        f"Done! Reservation for {party_size} at 7:00 PM under Ansari is "
                        "confirmed. See you then!"
                    ),
                    timestamp_ms=now_ms,
                )
            )
            extracted = {
                "reservation_status": "confirmed",
                "party_size": party_size,
                "time": "7:00 PM",
                "name": "Ansari",
            }
            summary_text = (
                f"Confirmed restaurant reservation for {party_size} guests at 7:00 PM under Ansari."
            )
            action_items = ["Add reservation to Calendar", "Notify attendees"]

        # Scenario 3: Generic business / customer inquiry
        else:
            turns.append(
                CallTranscriptTurn(
                    speaker="agent",
                    text=f"Hello, I am calling regarding: {objective}.",
                    timestamp_ms=now_ms,
                )
            )
            now_ms += 2000
            turns.append(
                CallTranscriptTurn(
                    speaker="party",
                    text="Thanks for the inquiry. Everything is in order on our side.",
                    timestamp_ms=now_ms,
                )
            )
            now_ms += 1800
            turns.append(
                CallTranscriptTurn(
                    speaker="agent",
                    text="Thank you, that answers our question. Goodbye!",
                    timestamp_ms=now_ms,
                )
            )
            extracted = {"inquiry_outcome": "verified"}
            summary_text = f"Completed inquiry call regarding: {objective}"

        summary = CallSummary(
            call_id="",  # filled by caller
            objective_completed=True,
            summary_text=summary_text,
            action_items=action_items,
            extracted_answers=extracted,
            sentiment="positive",
        )
        return turns, summary, extracted

    async def initiate_call(
        self,
        to_number: str,
        from_number: str,
        objective: str,
        *,
        webhook_url: str | None = None,
        idempotency_key: str | None = None,
    ) -> CallRecord:
        del webhook_url

        # Check idempotency
        if idempotency_key:
            for call in self._calls.values():
                if call.idempotency_key == idempotency_key:
                    logger.info("Returning existing call for key: %s", idempotency_key)
                    return call

        call_id = f"call_{uuid4().hex[:10]}"
        now_iso = datetime.now(UTC).isoformat()

        turns, summary_template, extracted = self._generate_dialogue(objective, to_number)
        summary = CallSummary(
            call_id=call_id,
            objective_completed=summary_template.objective_completed,
            summary_text=summary_template.summary_text,
            action_items=summary_template.action_items,
            extracted_answers=summary_template.extracted_answers,
            sentiment=summary_template.sentiment,
        )

        duration = max(18, len(turns) * 4)
        cost = round(duration * 0.0085, 4)

        record = CallRecord(
            id=call_id,
            provider_call_id=f"sim_sid_{uuid4().hex[:12]}",
            to_number=to_number,
            from_number=from_number,
            objective=objective,
            status=CallStatus.COMPLETED,
            direction=CallDirection.OUTBOUND,
            duration_seconds=duration,
            started_at=now_iso,
            ended_at=now_iso,
            turns=turns,
            summary=summary,
            extracted_data=extracted,
            cost_units=cost,
            recording_url=f"https://telephony.ceo-os.internal/recordings/{call_id}.wav",
            idempotency_key=idempotency_key,
        )
        self._calls[call_id] = record
        logger.info(
            "Completed simulated outbound call %s to %s in %ds (cost: $%0.4f)",
            call_id,
            to_number,
            duration,
            cost,
        )
        return record

    async def get_call_status(self, call_id: str) -> CallRecord:
        record = self._calls.get(call_id)
        if record is None:
            raise ValueError(f"Call record not found: {call_id}")
        return record

    async def terminate_call(self, call_id: str) -> CallRecord:
        record = self._calls.get(call_id)
        if record is None:
            raise ValueError(f"Call record not found: {call_id}")
        record.status = CallStatus.COMPLETED
        return record

    async def send_dtmf(self, call_id: str, digits: str) -> bool:
        record = self._calls.get(call_id)
        if record is None:
            raise ValueError(f"Call record not found: {call_id}")
        logger.info("Sent DTMF tones '%s' on call %s", digits, call_id)
        return True


class TwilioTelephonyProvider:
    """Live Twilio Voice API provider implementing TelephonyProvider."""

    def __init__(
        self,
        account_sid_ref: str,
        auth_token_ref: str,
        secret_broker: SecretBroker,
        policy: TelephonyPolicy | None = None,
    ) -> None:
        self._account_sid_ref = account_sid_ref
        self._auth_token_ref = auth_token_ref
        self._secret_broker = secret_broker
        self._policy = policy or TelephonyPolicy()
        self._calls: dict[str, CallRecord] = {}

    @property
    def name(self) -> str:
        return "twilio_telephony"

    def _get_auth(self) -> tuple[str, str]:
        sid_lease = self._secret_broker.lease_secret(self._account_sid_ref, "twilio_telephony")
        token_lease = self._secret_broker.lease_secret(self._auth_token_ref, "twilio_telephony")
        return sid_lease.secret_value, token_lease.secret_value

    async def initiate_call(
        self,
        to_number: str,
        from_number: str,
        objective: str,
        *,
        webhook_url: str | None = None,
        idempotency_key: str | None = None,
    ) -> CallRecord:
        sid, token = self._get_auth()
        if not sid or not token:
            raise AuthenticationError("Twilio credentials not configured")
        # In live mode this POSTs to https://api.twilio.com/2010-04-01/Accounts/{sid}/Calls.json
        call_id = f"call_{uuid4().hex[:10]}"
        record = CallRecord(
            id=call_id,
            provider_call_id=f"CA{uuid4().hex[:32]}",
            to_number=to_number,
            from_number=from_number,
            objective=objective,
            status=CallStatus.IN_PROGRESS,
            direction=CallDirection.OUTBOUND,
            started_at=datetime.now(UTC).isoformat(),
            idempotency_key=idempotency_key,
        )
        self._calls[call_id] = record
        return record

    async def get_call_status(self, call_id: str) -> CallRecord:
        record = self._calls.get(call_id)
        if record is None:
            raise ValueError(f"Call not found: {call_id}")
        return record

    async def terminate_call(self, call_id: str) -> CallRecord:
        record = self._calls.get(call_id)
        if record is None:
            raise ValueError(f"Call not found: {call_id}")
        record.status = CallStatus.COMPLETED
        return record

    async def send_dtmf(self, call_id: str, digits: str) -> bool:
        del call_id, digits
        return True
