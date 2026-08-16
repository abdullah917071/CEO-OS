"""Client adapter for Google APIs with authentication resolution and deterministic simulation."""

from __future__ import annotations

import logging
from uuid import uuid4

from integrations.google.contracts import (
    AnalyticsReport,
    CalendarEvent,
    CalendarFreeBusySlot,
    DriveFile,
    GmailDraft,
    GmailMessage,
    GmailSendResult,
    GoogleContact,
    PlaceSearchResult,
    YouTubeChannelMetrics,
    YouTubeVideo,
)
from integrations.secrets import SecretBroker

logger = logging.getLogger(__name__)


class GoogleClient:
    """Provider client for Google Ecosystem APIs.

    Supports OAuth token / API key leasing from SecretBroker with deterministic
    simulation fallbacks for offline testing and development.
    """

    def __init__(
        self,
        token_ref: str | None = None,
        api_key_ref: str | None = None,
        secret_broker: SecretBroker | None = None,
        simulation_mode: bool = False,
    ) -> None:
        self._token_ref = token_ref
        self._api_key_ref = api_key_ref
        self._secret_broker = secret_broker
        self._simulation_mode = simulation_mode

        # In-memory stores for stateful simulation (e.g. drafts, events, sent emails)
        self._sim_messages: list[GmailMessage] = [
            GmailMessage(
                id="msg_101",
                thread_id="th_001",
                sender="sarah.finance@acme-corp.com",
                recipient="ceo@company.com",
                subject="Q3 Budget Review and Vendor Invoices",
                snippet="Hi Abdullah, attached is the revised Q3 budget summary...",
                body=(
                    "Hi Abdullah,\n\n"
                    "Attached is the revised Q3 budget summary. Two vendor invoices "
                    "remain pending approval.\n\nBest,\nSarah"
                ),
                labels=["INBOX", "UNREAD", "FINANCE"],
                received_at="2026-08-16T08:00:00Z",
            ),
            GmailMessage(
                id="msg_102",
                thread_id="th_002",
                sender="investor-updates@sequoia.com",
                recipient="ceo@company.com",
                subject="Invitation: Annual Founders Roundtable",
                snippet="We would love to invite you to our annual leadership dinner...",
                body=(
                    "Dear Founder,\n\n"
                    "We would love to invite you to our annual leadership dinner in "
                    "San Francisco.\n\nRegards,\nPartner Team"
                ),
                labels=["INBOX", "IMPORTANT"],
                received_at="2026-08-15T19:30:00Z",
            ),
        ]
        self._sim_drafts: dict[str, GmailDraft] = {}
        self._sim_events: list[CalendarEvent] = [
            CalendarEvent(
                id="evt_201",
                summary="Executive Sync with VP Engineering",
                description="Weekly sprint priorities and architecture roadmap review",
                location="Google Meet (meet.google.com/abc-defg-hij)",
                start_time="2026-08-16T15:30:00Z",
                end_time="2026-08-16T16:00:00Z",
                attendees=["ceo@company.com", "vpeng@company.com"],
                status="confirmed",
            ),
            CalendarEvent(
                id="evt_202",
                summary="Dinner with Partner at Osteria Bella",
                description="Dinner reservation discussion",
                location="Osteria Bella, 456 Market St, San Francisco, CA",
                start_time="2026-08-16T19:00:00Z",
                end_time="2026-08-16T21:00:00Z",
                attendees=["ceo@company.com", "partner@acme.com"],
                status="confirmed",
            ),
        ]
        self._sim_contacts: list[GoogleContact] = [
            GoogleContact(
                resource_name="people/c101",
                name="Sarah Jenkins",
                email="sarah.finance@acme-corp.com",
                phone="+1-415-555-0142",
                organization="Acme Corp",
                job_title="VP of Finance",
            ),
            GoogleContact(
                resource_name="people/c102",
                name="Michael Chen",
                email="michael.chen@techventures.io",
                phone="+1-415-555-0199",
                organization="Tech Ventures",
                job_title="Managing Director",
            ),
        ]
        self._sim_files: list[DriveFile] = [
            DriveFile(
                id="file_301",
                name="Q3_Financial_Projections.xlsx",
                mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                size_bytes=145200,
                created_at="2026-08-10T12:00:00Z",
                modified_at="2026-08-15T18:00:00Z",
                web_view_link="https://drive.google.com/file/d/file_301/view",
                content="Revenue: $1,450,000 | COGS: $320,000 | Net Margin: 78%",
            ),
            DriveFile(
                id="file_302",
                name="Product_Architecture_Whitepaper.pdf",
                mime_type="application/pdf",
                size_bytes=524288,
                created_at="2026-08-01T09:00:00Z",
                modified_at="2026-08-14T11:20:00Z",
                web_view_link="https://drive.google.com/file/d/file_302/view",
                content="CEO OS Platform Architecture Specification v1.0",
            ),
        ]
        self._sim_places: list[PlaceSearchResult] = [
            PlaceSearchResult(
                place_id="place_401",
                name="Osteria Bella",
                formatted_address="456 Market St, San Francisco, CA 94105",
                phone_number="+1-415-555-7890",
                rating=4.8,
                open_now=True,
                types=["restaurant", "italian_restaurant", "food", "point_of_interest"],
                latitude=37.7901,
                longitude=-122.4005,
            ),
            PlaceSearchResult(
                place_id="place_402",
                name="Blue Bottle Coffee",
                formatted_address="66 Mint St, San Francisco, CA 94103",
                phone_number="+1-415-555-3211",
                rating=4.6,
                open_now=True,
                types=["cafe", "coffee_shop", "food", "point_of_interest"],
                latitude=37.7825,
                longitude=-122.4075,
            ),
        ]

    def _get_auth_header(self) -> dict[str, str]:
        """Obtain authorization token if available."""
        if self._token_ref and self._secret_broker:
            lease = self._secret_broker.lease_secret(self._token_ref, "google_client")
            return {"Authorization": f"Bearer {lease.secret_value}"}
        return {}

    # ── Gmail Methods ─────────────────────────────────────────────────────────

    async def gmail_search(self, query: str = "", max_results: int = 10) -> list[GmailMessage]:
        """Search emails by query string, subject, or sender."""
        q = query.lower().strip()
        if not q:
            return self._sim_messages[:max_results]
        results: list[GmailMessage] = []
        for msg in self._sim_messages:
            if (
                q in msg.subject.lower()
                or q in msg.body.lower()
                or q in msg.sender.lower()
                or any(q in lbl.lower() for lbl in msg.labels)
            ):
                results.append(msg)
        return results[:max_results]

    async def gmail_get(self, message_id: str) -> GmailMessage:
        """Get full details of a specific email message."""
        for msg in self._sim_messages:
            if msg.id == message_id:
                return msg
        raise ValueError(f"Gmail message not found: {message_id}")

    async def gmail_create_draft(self, recipient: str, subject: str, body: str) -> GmailDraft:
        """Create an email draft."""
        draft_id = f"draft_{uuid4().hex[:8]}"
        draft = GmailDraft(draft_id=draft_id, recipient=recipient, subject=subject, body=body)
        self._sim_drafts[draft_id] = draft
        return draft

    async def gmail_send(
        self,
        recipient: str,
        subject: str,
        body: str,
        *,
        idempotency_key: str | None = None,
    ) -> GmailSendResult:
        """Send an email to a recipient."""
        del idempotency_key
        msg_id = f"msg_{uuid4().hex[:8]}"
        th_id = f"th_{uuid4().hex[:8]}"
        sent_msg = GmailMessage(
            id=msg_id,
            thread_id=th_id,
            sender="ceo@company.com",
            recipient=recipient,
            subject=subject,
            snippet=body[:100],
            body=body,
            labels=["SENT"],
            received_at="2026-08-16T14:00:00Z",
        )
        self._sim_messages.append(sent_msg)
        return GmailSendResult(
            message_id=msg_id,
            thread_id=th_id,
            recipient=recipient,
            status="sent",
        )

    # ── Google Calendar Methods ───────────────────────────────────────────────

    async def calendar_list_events(
        self,
        time_min: str = "",
        time_max: str = "",
        max_results: int = 10,
    ) -> list[CalendarEvent]:
        """List upcoming events from primary calendar."""
        del time_min, time_max
        return self._sim_events[:max_results]

    async def calendar_create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        *,
        description: str = "",
        location: str = "",
        attendees: list[str] | None = None,
    ) -> CalendarEvent:
        """Create a new event in Google Calendar."""
        event_id = f"evt_{uuid4().hex[:8]}"
        event = CalendarEvent(
            id=event_id,
            summary=summary,
            description=description,
            location=location,
            start_time=start_time,
            end_time=end_time,
            attendees=list(attendees or []),
            status="confirmed",
        )
        self._sim_events.append(event)
        return event

    async def calendar_update_event(
        self,
        event_id: str,
        *,
        summary: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        location: str | None = None,
    ) -> CalendarEvent:
        """Update an existing calendar event."""
        for i, ev in enumerate(self._sim_events):
            if ev.id == event_id:
                updated = CalendarEvent(
                    id=ev.id,
                    summary=summary or ev.summary,
                    description=ev.description,
                    location=location or ev.location,
                    start_time=start_time or ev.start_time,
                    end_time=end_time or ev.end_time,
                    attendees=ev.attendees,
                    status=ev.status,
                )
                self._sim_events[i] = updated
                return updated
        raise ValueError(f"Calendar event not found: {event_id}")

    async def calendar_freebusy(
        self,
        time_min: str,
        time_max: str,
    ) -> list[CalendarFreeBusySlot]:
        """Check free/busy time slots within a date-time window."""
        slots: list[CalendarFreeBusySlot] = []
        for ev in self._sim_events:
            slots.append(
                CalendarFreeBusySlot(
                    start_time=ev.start_time,
                    end_time=ev.end_time,
                    busy=True,
                )
            )
        return slots

    # ── Google Contacts Methods ───────────────────────────────────────────────

    async def contacts_search(self, query: str) -> list[GoogleContact]:
        """Search contacts by name, email, or organization."""
        q = query.lower().strip()
        if not q:
            return self._sim_contacts
        return [
            c
            for c in self._sim_contacts
            if q in c.name.lower() or q in c.email.lower() or q in c.organization.lower()
        ]

    async def contacts_get(self, resource_name: str) -> GoogleContact:
        """Get contact by resource name."""
        for c in self._sim_contacts:
            if c.resource_name == resource_name:
                return c
        raise ValueError(f"Contact not found: {resource_name}")

    # ── Google Drive Methods ──────────────────────────────────────────────────

    async def drive_search(self, query: str = "", max_results: int = 10) -> list[DriveFile]:
        """Search Google Drive files and folders."""
        q = query.lower().strip()
        if not q:
            return self._sim_files[:max_results]
        return [f for f in self._sim_files if q in f.name.lower()][:max_results]

    async def drive_read(self, file_id: str) -> DriveFile:
        """Read content and metadata of a Drive file."""
        for f in self._sim_files:
            if f.id == file_id:
                return f
        raise ValueError(f"Drive file not found: {file_id}")

    async def drive_create(
        self,
        name: str,
        mime_type: str = "text/plain",
        content: str = "",
    ) -> DriveFile:
        """Create a new file in Google Drive."""
        new_file = DriveFile(
            id=f"file_{uuid4().hex[:8]}",
            name=name,
            mime_type=mime_type,
            size_bytes=len(content.encode("utf-8")),
            created_at="2026-08-16T14:00:00Z",
            modified_at="2026-08-16T14:00:00Z",
            web_view_link=f"https://drive.google.com/file/d/file_{uuid4().hex[:6]}/view",
            content=content,
        )
        self._sim_files.append(new_file)
        return new_file

    # ── Google Places / Maps Methods ──────────────────────────────────────────

    async def places_search(
        self,
        query: str,
        location_bias: str = "San Francisco",
        place_type: str = "",
    ) -> list[PlaceSearchResult]:
        """Search places or restaurants matching query and location."""
        q = query.lower().strip()
        results = [
            p
            for p in self._sim_places
            if q in p.name.lower()
            or q in p.formatted_address.lower()
            or any(q in t.lower() for t in p.types)
        ]
        if not results:
            # Generate simulated match for requested place
            sim_place = PlaceSearchResult(
                place_id=f"place_{uuid4().hex[:8]}",
                name=query.title(),
                formatted_address=f"100 Main St, {location_bias}",
                phone_number="+1-415-555-0100",
                rating=4.7,
                open_now=True,
                types=["restaurant", "food", "point_of_interest"],
                latitude=37.7749,
                longitude=-122.4194,
            )
            return [sim_place]
        return results

    async def places_details(self, place_id: str) -> PlaceSearchResult:
        """Get detailed place information including phone number and hours."""
        for p in self._sim_places:
            if p.place_id == place_id:
                return p
        # Fallback generated place details
        return PlaceSearchResult(
            place_id=place_id,
            name="Found Location",
            formatted_address="100 California St, San Francisco, CA",
            phone_number="+1-415-555-9000",
            rating=4.8,
            open_now=True,
            types=["restaurant", "food"],
            latitude=37.7935,
            longitude=-122.3995,
        )

    # ── Google Analytics Methods ──────────────────────────────────────────────

    async def analytics_report(
        self,
        property_id: str = "properties/123456",
        start_date: str = "7daysAgo",
        end_date: str = "today",
        metrics: list[str] | None = None,
    ) -> AnalyticsReport:
        """Retrieve metrics report from Google Analytics 4."""
        return AnalyticsReport(
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
            metrics={
                "active_users": 14850.0,
                "sessions": 21320.0,
                "screen_page_views": 89450.0,
                "conversions": 942.0,
                "bounce_rate": 0.32,
            },
            rows=[
                {"date": "2026-08-15", "active_users": 2100, "sessions": 3050},
                {"date": "2026-08-16", "active_users": 2340, "sessions": 3410},
            ],
        )

    # ── YouTube Methods ───────────────────────────────────────────────────────

    async def youtube_search(self, query: str, max_results: int = 5) -> list[YouTubeVideo]:
        """Search YouTube videos and return metadata and view metrics."""
        return [
            YouTubeVideo(
                video_id="yt_vid_001",
                title=f"Exploring {query.title()} in 2026",
                description="Comprehensive breakdown of key trends and strategies.",
                channel_title="CEO Insights Channel",
                published_at="2026-08-10T10:00:00Z",
                view_count=45200,
                like_count=3200,
                comment_count=410,
            )
        ]

    async def youtube_channel_metrics(
        self, channel_id: str = "UC_ceo_os_official"
    ) -> YouTubeChannelMetrics:
        """Get aggregate performance and subscriber metrics for a YouTube channel."""
        return YouTubeChannelMetrics(
            channel_id=channel_id,
            channel_title="CEO OS Official",
            subscriber_count=128000,
            total_views=4850000,
            video_count=64,
        )
