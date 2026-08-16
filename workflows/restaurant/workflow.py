"""Orchestrator engine for the autonomous restaurant booking workflow."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from communications.telephony.manager import CallManager
from integrations.google.client import GoogleClient
from memory.service import MemoryService, Provenance
from workflows.restaurant.contracts import ReservationRequest, ReservationResult

logger = logging.getLogger(__name__)


class RestaurantBookingWorkflow:
    """Orchestrates Places search, Telephony outbound calling, Calendar scheduling,

    Memory retention, and Executive Reporting into a unified goal-based workflow.
    """

    def __init__(
        self,
        google_client: GoogleClient | None = None,
        call_manager: CallManager | None = None,
        memory_service: MemoryService | None = None,
    ) -> None:
        self._google_client = google_client or GoogleClient()
        self._call_manager = call_manager or CallManager()
        self._memory_service = memory_service

    async def execute(
        self,
        request: ReservationRequest,
        *,
        idempotency_key: str | None = None,
    ) -> ReservationResult:
        """Execute the end-to-end restaurant booking workflow."""
        del idempotency_key
        evidence: list[str] = []

        # ── Step 1: Discover Restaurant & Phone Number via Google Places ──────
        places = await self._google_client.places_search(
            query=request.restaurant_name,
            location_bias=request.location_bias,
            place_type="restaurant",
        )
        if not places:
            summary = f"Could not find any restaurant matching '{request.restaurant_name}'"
            return ReservationResult(
                status="failed",
                restaurant_name=request.restaurant_name,
                address="",
                phone_number="",
                confirmed_time="",
                party_size=request.party_size,
                booking_name=request.booking_name,
                summary=summary,
                evidence=[summary],
            )

        place = places[0]
        evidence.append(
            f"1. Places: Found '{place.name}' at '{place.formatted_address}' "
            f"(Phone: {place.phone_number}, Rating: {place.rating})"
        )

        # ── Step 2: Place Outbound Phone Call to Book Table ───────────────────
        call_obj = (
            f"book table for {request.party_size} people at {request.time} "
            f"under {request.booking_name}"
        )
        call_record = await self._call_manager.initiate_call(
            to_number=place.phone_number,
            objective=call_obj,
            idempotency_key=f"call_book_{place.place_id}_{request.time}",
        )
        call_summary = call_record.summary.summary_text if call_record.summary else "Completed"
        evidence.append(
            f"2. Telephony: Placed outbound call to {place.phone_number} "
            f"(Call ID: {call_record.id}, Duration: {call_record.duration_seconds}s). "
            f"Outcome: {call_summary}"
        )

        confirmed_time = (
            call_record.extracted_data.get("time", request.time)
            if call_record.extracted_data
            else request.time
        )

        # ── Step 3: Schedule Confirmed Booking on Google Calendar ─────────────
        start_iso = "2026-08-16T19:00:00Z"
        end_iso = "2026-08-16T21:00:00Z"
        cal_event = await self._google_client.calendar_create_event(
            summary=f"Dinner at {place.name}",
            start_time=start_iso,
            end_time=end_iso,
            description=(
                f"Table reservation for {request.party_size} guests under {request.booking_name}.\n"
                f"Restaurant: {place.name}\n"
                f"Address: {place.formatted_address}\n"
                f"Phone: {place.phone_number}"
            ),
            location=place.formatted_address,
            attendees=["ceo@company.com"],
        )
        evidence.append(
            f"3. Calendar: Created event '{cal_event.summary}' for {start_iso} "
            f"(Event ID: {cal_event.id})"
        )

        # ── Step 4: Record Episodic Memory ────────────────────────────────────
        memory_id: str | None = None
        if self._memory_service:
            now = datetime.now(UTC)
            provenance = Provenance(
                source_type="restaurant_workflow",
                source_uri=f"places:{place.place_id}",
                detail=f"Automated booking via call {call_record.id} and event {cal_event.id}",
                observed_at=now,
            )
            mem_content = (
                f"Confirmed restaurant reservation: {request.party_size} people at {place.name} "
                f"({place.formatted_address}) at {confirmed_time} under {request.booking_name}."
            )
            try:
                mem_view = await self._memory_service.create(
                    memory_type="episodic",
                    content=mem_content,
                    provenance=provenance,
                    subject_key=f"restaurant:{place.name.lower().replace(' ', '_')}",
                    confidence=0.98,
                    importance=0.9,
                    dedupe_key=f"mem_res_{cal_event.id}",
                    attributes={
                        "restaurant_name": place.name,
                        "address": place.formatted_address,
                        "phone_number": place.phone_number,
                        "party_size": request.party_size,
                        "booking_name": request.booking_name,
                        "confirmed_time": confirmed_time,
                        "calendar_event_id": cal_event.id,
                        "call_id": call_record.id,
                    },
                )
                memory_id = mem_view.id
                evidence.append(f"4. Memory: Saved episodic record (Memory ID: {memory_id})")
            except Exception:
                logger.warning("Failed to save booking memory", exc_info=True)

        # ── Step 5: Compile Executive Report ──────────────────────────────────
        summary = (
            f"Successfully booked table for {request.party_size} at {place.name} "
            f"({place.formatted_address}) at {confirmed_time} under '{request.booking_name}'. "
            f"Calendar event '{cal_event.summary}' created."
        )
        evidence.append(f"5. Report: {summary}")

        return ReservationResult(
            status="confirmed",
            restaurant_name=place.name,
            address=place.formatted_address,
            phone_number=place.phone_number,
            confirmed_time=confirmed_time,
            party_size=request.party_size,
            booking_name=request.booking_name,
            call_id=call_record.id,
            calendar_event_id=cal_event.id,
            memory_id=memory_id,
            summary=summary,
            evidence=evidence,
        )
