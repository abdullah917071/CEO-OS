"""Data contracts and schemas for Google Ecosystem integrations."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GmailMessage:
    """Represents an email message in Gmail."""

    id: str
    thread_id: str
    sender: str
    recipient: str
    subject: str
    snippet: str
    body: str
    labels: list[str] = field(default_factory=list)
    received_at: str = ""


@dataclass(frozen=True)
class GmailDraft:
    """Represents an email draft in Gmail."""

    draft_id: str
    recipient: str
    subject: str
    body: str


@dataclass(frozen=True)
class GmailSendResult:
    """Result of sending an email through Gmail."""

    message_id: str
    thread_id: str
    recipient: str
    status: str = "sent"


@dataclass(frozen=True)
class CalendarEvent:
    """Represents a calendar event in Google Calendar."""

    id: str
    summary: str
    description: str
    location: str
    start_time: str
    end_time: str
    attendees: list[str] = field(default_factory=list)
    status: str = "confirmed"


@dataclass(frozen=True)
class CalendarFreeBusySlot:
    """Represents a free/busy time slot."""

    start_time: str
    end_time: str
    busy: bool


@dataclass(frozen=True)
class GoogleContact:
    """Represents a person or contact in Google Contacts."""

    resource_name: str
    name: str
    email: str
    phone: str = ""
    organization: str = ""
    job_title: str = ""


@dataclass(frozen=True)
class DriveFile:
    """Represents a file or folder in Google Drive."""

    id: str
    name: str
    mime_type: str
    size_bytes: int = 0
    created_at: str = ""
    modified_at: str = ""
    web_view_link: str = ""
    content: str | None = None


@dataclass(frozen=True)
class PlaceSearchResult:
    """Represents a location or business from Google Places."""

    place_id: str
    name: str
    formatted_address: str
    phone_number: str = ""
    rating: float = 0.0
    open_now: bool = True
    types: list[str] = field(default_factory=list)
    latitude: float = 0.0
    longitude: float = 0.0


@dataclass(frozen=True)
class AnalyticsReport:
    """Represents an analytics metrics query report."""

    property_id: str
    start_date: str
    end_date: str
    metrics: dict[str, float] = field(default_factory=dict)
    rows: list[dict[str, str | float]] = field(default_factory=list)


@dataclass(frozen=True)
class YouTubeVideo:
    """Represents a YouTube video."""

    video_id: str
    title: str
    description: str
    channel_title: str
    published_at: str
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0


@dataclass(frozen=True)
class YouTubeChannelMetrics:
    """Represents aggregate metrics for a YouTube channel."""

    channel_id: str
    channel_title: str
    subscriber_count: int = 0
    total_views: int = 0
    video_count: int = 0
