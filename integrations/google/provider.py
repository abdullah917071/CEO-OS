"""Google Ecosystem integration provider and capability tools."""

from __future__ import annotations

import dataclasses
from typing import Any

from core.contracts import CapabilitySpec, RiskLevel, Tool, ToolResult
from integrations.contracts import (
    IntegrationManifest,
    IntegrationType,
    OAuthProfile,
)
from integrations.google.client import GoogleClient
from integrations.native import NativeIntegrationProvider
from integrations.secrets import SecretBroker

# ── Gmail Capability Tools ──────────────────────────────────────────────────


class GmailSearchTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.gmail.search",
            description="Search Gmail messages by query, sender, subject, or label",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query filter"},
                    "max_results": {"type": "integer", "description": "Max results to return"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        query = str(arguments.get("query", ""))
        max_results = int(arguments.get("max_results", 10))
        messages = await self._client.gmail_search(query, max_results)
        return ToolResult(
            output={"messages": [dataclasses.asdict(m) for m in messages]},
            evidence=[f"Searched Gmail for '{query}': found {len(messages)} message(s)"],
        )


class GmailReadTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.gmail.read",
            description="Read the complete body and headers of a Gmail message",
            input_schema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "Gmail message ID"},
                },
                "required": ["message_id"],
            },
            risk=RiskLevel.READ,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        message_id = str(arguments.get("message_id", ""))
        msg = await self._client.gmail_get(message_id)
        return ToolResult(
            output=dataclasses.asdict(msg),
            evidence=[f"Read Gmail message {message_id} with subject '{msg.subject}'"],
        )


class GmailDraftTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.gmail.draft",
            description="Create an email draft in Gmail",
            input_schema={
                "type": "object",
                "properties": {
                    "recipient": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body content"},
                },
                "required": ["recipient", "subject", "body"],
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        recipient = str(arguments.get("recipient", ""))
        subject = str(arguments.get("subject", ""))
        body = str(arguments.get("body", ""))
        draft = await self._client.gmail_create_draft(recipient, subject, body)
        return ToolResult(
            output=dataclasses.asdict(draft),
            evidence=[f"Created email draft {draft.draft_id} to {recipient}"],
        )


class GmailSendTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.gmail.send",
            description="Send an email through Gmail",
            input_schema={
                "type": "object",
                "properties": {
                    "recipient": {"type": "string", "description": "Recipient email address"},
                    "subject": {"type": "string", "description": "Email subject line"},
                    "body": {"type": "string", "description": "Email body content"},
                },
                "required": ["recipient", "subject", "body"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        recipient = str(arguments.get("recipient", ""))
        subject = str(arguments.get("subject", ""))
        body = str(arguments.get("body", ""))
        result = await self._client.gmail_send(
            recipient, subject, body, idempotency_key=idempotency_key
        )
        return ToolResult(
            output=dataclasses.asdict(result),
            evidence=[f"Sent email to {recipient} with subject '{subject}'"],
        )


# ── Google Calendar Capability Tools ─────────────────────────────────────────


class CalendarListTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.calendar.list",
            description="List upcoming events from Google Calendar",
            input_schema={
                "type": "object",
                "properties": {
                    "time_min": {"type": "string", "description": "Start timestamp filter"},
                    "time_max": {"type": "string", "description": "End timestamp filter"},
                    "max_results": {"type": "integer", "description": "Max events"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        time_min = str(arguments.get("time_min", ""))
        time_max = str(arguments.get("time_max", ""))
        max_results = int(arguments.get("max_results", 10))
        events = await self._client.calendar_list_events(time_min, time_max, max_results)
        return ToolResult(
            output={"events": [dataclasses.asdict(e) for e in events]},
            evidence=[f"Retrieved {len(events)} calendar event(s) from Google Calendar"],
        )


class CalendarCreateEventTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.calendar.create_event",
            description="Create a new event on Google Calendar",
            input_schema={
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Event title/summary"},
                    "start_time": {"type": "string", "description": "ISO start datetime"},
                    "end_time": {"type": "string", "description": "ISO end datetime"},
                    "description": {"type": "string", "description": "Event notes/agenda"},
                    "location": {"type": "string", "description": "Location or Meet URL"},
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Attendee emails",
                    },
                },
                "required": ["summary", "start_time", "end_time"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        summary = str(arguments.get("summary", ""))
        start_time = str(arguments.get("start_time", ""))
        end_time = str(arguments.get("end_time", ""))
        description = str(arguments.get("description", ""))
        location = str(arguments.get("location", ""))
        attendees = arguments.get("attendees")
        event = await self._client.calendar_create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
            attendees=attendees,
        )
        return ToolResult(
            output=dataclasses.asdict(event),
            evidence=[f"Created calendar event '{summary}' on {start_time} (id: {event.id})"],
        )


class CalendarUpdateEventTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.calendar.update_event",
            description="Update an existing Google Calendar event",
            input_schema={
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "Event ID to update"},
                    "summary": {"type": "string", "description": "New title"},
                    "start_time": {"type": "string", "description": "New start time"},
                    "end_time": {"type": "string", "description": "New end time"},
                    "location": {"type": "string", "description": "New location"},
                },
                "required": ["event_id"],
            },
            risk=RiskLevel.EXTERNAL_COMMUNICATION,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        event_id = str(arguments.get("event_id", ""))
        summary = arguments.get("summary")
        start_time = arguments.get("start_time")
        end_time = arguments.get("end_time")
        location = arguments.get("location")
        updated = await self._client.calendar_update_event(
            event_id=event_id,
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            location=location,
        )
        return ToolResult(
            output=dataclasses.asdict(updated),
            evidence=[f"Updated calendar event {event_id}: summary='{updated.summary}'"],
        )


class CalendarFreeBusyTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.calendar.freebusy",
            description="Query free/busy slots across a date range",
            input_schema={
                "type": "object",
                "properties": {
                    "time_min": {"type": "string", "description": "Start ISO datetime"},
                    "time_max": {"type": "string", "description": "End ISO datetime"},
                },
                "required": ["time_min", "time_max"],
            },
            risk=RiskLevel.READ,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        time_min = str(arguments.get("time_min", ""))
        time_max = str(arguments.get("time_max", ""))
        slots = await self._client.calendar_freebusy(time_min, time_max)
        return ToolResult(
            output={"busy_slots": [dataclasses.asdict(s) for s in slots]},
            evidence=[f"Found {len(slots)} busy time slot(s) between {time_min} and {time_max}"],
        )


# ── Google Contacts Capability Tools ─────────────────────────────────────────


class ContactsSearchTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.contacts.search",
            description="Search Google Contacts for people, email addresses, or phone numbers",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Contact name, email, or org"},
                },
                "required": ["query"],
            },
            risk=RiskLevel.READ,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        query = str(arguments.get("query", ""))
        contacts = await self._client.contacts_search(query)
        return ToolResult(
            output={"contacts": [dataclasses.asdict(c) for c in contacts]},
            evidence=[f"Searched Google Contacts for '{query}': found {len(contacts)} result(s)"],
        )


# ── Google Drive Capability Tools ────────────────────────────────────────────


class DriveSearchTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.drive.search",
            description="Search Google Drive files and documents",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "File search query"},
                    "max_results": {"type": "integer", "description": "Max files"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        query = str(arguments.get("query", ""))
        max_results = int(arguments.get("max_results", 10))
        files = await self._client.drive_search(query, max_results)
        return ToolResult(
            output={"files": [dataclasses.asdict(f) for f in files]},
            evidence=[f"Searched Google Drive for '{query}': found {len(files)} file(s)"],
        )


class DriveReadTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.drive.read",
            description="Read file content and metadata from Google Drive",
            input_schema={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "Drive file ID"},
                },
                "required": ["file_id"],
            },
            risk=RiskLevel.READ,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        file_id = str(arguments.get("file_id", ""))
        drive_file = await self._client.drive_read(file_id)
        return ToolResult(
            output=dataclasses.asdict(drive_file),
            evidence=[f"Read Google Drive file '{drive_file.name}' (id: {file_id})"],
        )


class DriveCreateTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.drive.create",
            description="Create a new text or document file in Google Drive",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "File name"},
                    "mime_type": {"type": "string", "description": "MIME type"},
                    "content": {"type": "string", "description": "File content"},
                },
                "required": ["name", "content"],
            },
            risk=RiskLevel.HARMLESS_WRITE,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        name = str(arguments.get("name", ""))
        mime_type = str(arguments.get("mime_type", "text/plain"))
        content = str(arguments.get("content", ""))
        created = await self._client.drive_create(name, mime_type, content)
        return ToolResult(
            output=dataclasses.asdict(created),
            evidence=[f"Created Google Drive file '{name}' (id: {created.id})"],
        )


# ── Google Places / Maps Capability Tools ────────────────────────────────────


class PlacesSearchTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.places.search",
            description="Search Google Places for locations, restaurants, or businesses",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Place name or keywords"},
                    "location_bias": {"type": "string", "description": "City or area"},
                    "place_type": {"type": "string", "description": "Place category filter"},
                },
                "required": ["query"],
            },
            risk=RiskLevel.READ,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        query = str(arguments.get("query", ""))
        location_bias = str(arguments.get("location_bias", "San Francisco"))
        place_type = str(arguments.get("place_type", ""))
        places = await self._client.places_search(query, location_bias, place_type)
        return ToolResult(
            output={"places": [dataclasses.asdict(p) for p in places]},
            evidence=[
                f"Searched Google Places for '{query}' in '{location_bias}': "
                f"found {len(places)} place(s)"
            ],
        )


class PlacesDetailsTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.places.details",
            description="Get detailed place information including phone number and hours",
            input_schema={
                "type": "object",
                "properties": {
                    "place_id": {"type": "string", "description": "Google Place ID"},
                },
                "required": ["place_id"],
            },
            risk=RiskLevel.READ,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        place_id = str(arguments.get("place_id", ""))
        details = await self._client.places_details(place_id)
        return ToolResult(
            output=dataclasses.asdict(details),
            evidence=[f"Retrieved details for '{details.name}', phone: {details.phone_number}"],
        )


# ── Google Analytics Capability Tools ────────────────────────────────────────


class AnalyticsReportTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.analytics.report",
            description="Query active users, sessions, pageviews, and conversion metrics from GA4",
            input_schema={
                "type": "object",
                "properties": {
                    "property_id": {"type": "string", "description": "GA4 property ID"},
                    "start_date": {"type": "string", "description": "Start date"},
                    "end_date": {"type": "string", "description": "End date"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        property_id = str(arguments.get("property_id", "properties/123456"))
        start_date = str(arguments.get("start_date", "7daysAgo"))
        end_date = str(arguments.get("end_date", "today"))
        report = await self._client.analytics_report(property_id, start_date, end_date)
        return ToolResult(
            output=dataclasses.asdict(report),
            evidence=[
                f"Retrieved GA4 report for {property_id} ({start_date} to {end_date}): "
                f"{int(report.metrics.get('active_users', 0))} active users, "
                f"{int(report.metrics.get('conversions', 0))} conversions"
            ],
        )


# ── YouTube Capability Tools ─────────────────────────────────────────────────


class YouTubeSearchTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.youtube.search",
            description="Search YouTube videos and channels for views and engagement",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Video search query"},
                    "max_results": {"type": "integer", "description": "Max results"},
                },
                "required": ["query"],
            },
            risk=RiskLevel.READ,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        query = str(arguments.get("query", ""))
        max_results = int(arguments.get("max_results", 5))
        videos = await self._client.youtube_search(query, max_results)
        return ToolResult(
            output={"videos": [dataclasses.asdict(v) for v in videos]},
            evidence=[f"Searched YouTube for '{query}': found {len(videos)} video(s)"],
        )


class YouTubeMetricsTool:
    def __init__(self, client: GoogleClient) -> None:
        self._client = client

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            name="google.youtube.metrics",
            description="Get YouTube channel subscriber count, total views, and video counts",
            input_schema={
                "type": "object",
                "properties": {
                    "channel_id": {"type": "string", "description": "YouTube channel ID"},
                },
            },
            risk=RiskLevel.READ,
            source="integration:google",
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        channel_id = str(arguments.get("channel_id", "UC_ceo_os_official"))
        metrics = await self._client.youtube_channel_metrics(channel_id)
        return ToolResult(
            output=dataclasses.asdict(metrics),
            evidence=[
                f"Retrieved YouTube metrics for '{metrics.channel_title}': "
                f"{metrics.subscriber_count} subscribers, {metrics.total_views} views"
            ],
        )


# ── Google Ecosystem Integration Provider ────────────────────────────────────


class GoogleEcosystemIntegration(NativeIntegrationProvider):
    """Native integration provider for the Google Ecosystem."""

    def __init__(
        self,
        token_ref: str | None = None,
        api_key_ref: str | None = None,
        secret_broker: SecretBroker | None = None,
        requests_per_minute: int = 120,
    ) -> None:
        super().__init__(secret_broker=secret_broker)
        self._token_ref = token_ref
        self._api_key_ref = api_key_ref
        self._requests_per_minute = requests_per_minute
        self._burst_limit = 30
        self._client = GoogleClient(
            token_ref=token_ref,
            api_key_ref=api_key_ref,
            secret_broker=secret_broker,
        )

    def manifest(self) -> IntegrationManifest:
        oauth_prof = (
            OAuthProfile(
                provider_name="google",
                client_id_ref="cred_google_client_id",
                client_secret_ref="cred_google_client_secret",
                authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
                token_url="https://oauth2.googleapis.com/token",
                scopes=[
                    "https://www.googleapis.com/auth/gmail.modify",
                    "https://www.googleapis.com/auth/calendar",
                    "https://www.googleapis.com/auth/contacts.readonly",
                    "https://www.googleapis.com/auth/drive",
                    "https://www.googleapis.com/auth/analytics.readonly",
                    "https://www.googleapis.com/auth/youtube.readonly",
                ],
            )
            if self._secret_broker
            else None
        )
        return IntegrationManifest(
            name="google_ecosystem",
            version="1.0.0",
            description=(
                "Google Ecosystem Integration: Gmail, Calendar, Contacts, Drive, "
                "Places, Analytics, YouTube"
            ),
            integration_type=IntegrationType.NATIVE,
            domain="integrations",
            risk_ceiling=RiskLevel.EXTERNAL_COMMUNICATION,
            enabled=True,
            oauth_profile=oauth_prof,
            required_credentials=[self._token_ref] if self._token_ref else [],
            rate_limits={
                "requests_per_minute": self._requests_per_minute,
                "burst_limit": self._burst_limit,
            },
        )

    def build_tools(self) -> list[Tool]:
        return [
            # Gmail
            GmailSearchTool(self._client),
            GmailReadTool(self._client),
            GmailDraftTool(self._client),
            GmailSendTool(self._client),
            # Calendar
            CalendarListTool(self._client),
            CalendarCreateEventTool(self._client),
            CalendarUpdateEventTool(self._client),
            CalendarFreeBusyTool(self._client),
            # Contacts
            ContactsSearchTool(self._client),
            # Drive
            DriveSearchTool(self._client),
            DriveReadTool(self._client),
            DriveCreateTool(self._client),
            # Places / Maps
            PlacesSearchTool(self._client),
            PlacesDetailsTool(self._client),
            # Analytics
            AnalyticsReportTool(self._client),
            # YouTube
            YouTubeSearchTool(self._client),
            YouTubeMetricsTool(self._client),
        ]
