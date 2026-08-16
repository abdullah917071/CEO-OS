"""Google Ecosystem integration package."""

from integrations.google.client import GoogleClient
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
from integrations.google.provider import GoogleEcosystemIntegration

__all__ = [
    "AnalyticsReport",
    "CalendarEvent",
    "CalendarFreeBusySlot",
    "DriveFile",
    "GmailDraft",
    "GmailMessage",
    "GmailSendResult",
    "GoogleClient",
    "GoogleContact",
    "GoogleEcosystemIntegration",
    "PlaceSearchResult",
    "YouTubeChannelMetrics",
    "YouTubeVideo",
]
