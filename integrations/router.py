"""Capability router: domain classification and context-aware tool routing."""

from __future__ import annotations

import re

from core.contracts import CapabilitySpec

# Domain keywords map for classifier
_DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "system": (
        "time",
        "date",
        "clock",
        "system",
        "platform",
        "host",
        "hostname",
        "python",
        "status",
    ),
    "files": (
        "file",
        "folder",
        "directory",
        "mkdir",
        "write",
        "read",
        "readme",
        "path",
        "disk",
        "save",
        "document",
    ),
    "calc": (
        "calculate",
        "compute",
        "calc",
        "math",
        "evaluate",
        "plus",
        "minus",
        "multiply",
        "divide",
        "%",
        "+",
        "-",
        "*",
        "/",
    ),
    "memory": (
        "remember",
        "note",
        "memory",
        "recall",
        "decide",
        "decision",
        "search memory",
        "episode",
        "what did",
    ),
    "agents": (
        "agent",
        "delegate",
        "researcher",
        "worker",
        "competitor",
        "parallel",
        "hire",
        "assignment",
    ),
    "computer": (
        "computer",
        "app",
        "application",
        "focus",
        "type",
        "window",
        "launch",
        "chrome",
        "safari",
        "textedit",
    ),
    "browser": (
        "browser",
        "browse",
        "visit",
        "url",
        "http",
        "https",
        "web",
        "dom",
        "click",
        "extract",
        "download",
    ),
    "vision": (
        "vision",
        "screen",
        "screenshot",
        "window",
        "ui",
        "capture",
        "display",
        "visual",
    ),
    "voice": (
        "voice",
        "speak",
        "speech",
        "listen",
        "mic",
        "microphone",
        "transcript",
        "talk",
        "audio",
    ),
    "integrations": (
        "integration",
        "mcp",
        "weather",
        "server",
        "service",
        "external",
        "plugin",
        "api",
        "google",
        "gmail",
        "calendar",
        "contacts",
        "places",
        "restaurant",
        "analytics",
        "youtube",
        "email",
        "emails",
        "inbox",
        "mail",
        "call",
        "calls",
        "phone",
        "telephony",
        "dial",
        "book",
        "reserve",
        "reservation",
        "table",
        "meta",
        "facebook",
        "instagram",
        "ads",
        "campaign",
        "campaigns",
        "adset",
        "creative",
        "creatives",
        "roas",
        "cpc",
        "cpm",
        "ctr",
        "marketing",
        "profit",
        "diagnose",
        "attribution",
        "funnel",
        "cac",
        "cpa",
        "margin",
        "cogs",
        "bounce",
        "sms",
        "whatsapp",
        "followup",
        "followups",
        "notification",
        "notifications",
        "cadence",
        "messaging",
        "finance",
        "invoice",
        "invoices",
        "receivables",
        "subscription",
        "subscriptions",
        "afford",
        "pipeline",
        "inventory",
        "runway",
        "overview",
        "deal",
        "deals",
        "briefing",
        "happening",
        "what's happening",
        "business",
        "executive",
        "status",
        "skill",
        "skills",
        "procedure",
        "skill_library",
        "openapi",
        "swagger",
        "ingest",
        "api_builder",
        "auto_builder",
        "api_docs",
        "proactive",
        "triggers",
        "trigger",
        "goals",
        "goal",
        "milestone",
        "milestones",
        "proactively",
        "anomalies",
        "production",
        "hardening",
        "security_audit",
        "finops",
        "cost",
        "costs",
        "confidence",
        "resilience",
        "fleet",
        "performance",
        "agency",
        "persona",
        "personas",
        "agency_agents",
        "specialist_skill",
        "hermes",
        "hermes_agent",
        "ceo_agent",
        "react",
        "scratchpad",
        "trajectory",
        "trajectories",
        "self_evolution",
        "gstack",
        "office_hours",
        "ceo_review",
        "eng_review",
        "staff_review",
        "garry_tan",
    ),
}

# Domain prefix mappings for capabilities
_CAPABILITY_DOMAIN_PREFIXES: dict[str, str] = {
    "time.": "system",
    "system_info.": "system",
    "files.": "files",
    "shell.": "files",
    "google.drive.": "files",
    "calculator.": "calc",
    "memory.": "memory",
    "notes.": "memory",
    "agents.": "agents",
    "computer.": "computer",
    "browser.": "browser",
    "vision.": "vision",
    "voice.": "voice",
    "google.": "integrations",
    "telephony.": "integrations",
    "workflow.": "integrations",
    "meta.": "integrations",
    "marketing.": "integrations",
    "comms.": "integrations",
    "business.": "integrations",
    "skills.": "integrations",
    "developer.": "integrations",
    "proactive.": "integrations",
    "production.": "integrations",
    "agency.": "integrations",
    "ceo.agent.": "integrations",
    "ceo.": "integrations",
    "hermes.": "integrations",
    "gstack.": "integrations",
}


class CapabilityRouter:
    """Classifies user requests into capability domains and filters tool sets for planners."""

    def __init__(self, default_domains: set[str] | None = None) -> None:
        self._default_domains = default_domains or {"system", "files", "calc", "memory"}

    def classify_domains(self, query: str) -> set[str]:
        """Determine relevant capability domains for a given user query."""
        lower = query.lower().strip()
        matched: set[str] = set()

        for domain, keywords in _DOMAIN_KEYWORDS.items():
            for kw in keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", lower, re.I):
                    matched.add(domain)
                    break

        # Always include default domains if no specific domain matched
        if not matched:
            return set(self._default_domains)
        return matched

    def domain_for_capability(self, spec: CapabilitySpec) -> str:
        """Infer the domain for a given capability specification."""
        name = spec.name.lower()
        source = spec.source.lower()

        if source.startswith("mcp:") or source.startswith("integration:"):
            for prefix, domain in _CAPABILITY_DOMAIN_PREFIXES.items():
                if name.startswith(prefix):
                    return domain
            return "integrations"

        for prefix, domain in _CAPABILITY_DOMAIN_PREFIXES.items():
            if name.startswith(prefix):
                return domain

        # Fallback based on name keywords
        for domain, keywords in _DOMAIN_KEYWORDS.items():
            if any(kw in name for kw in keywords):
                return domain

        return "custom"

    def route(
        self,
        query: str,
        capabilities: list[CapabilitySpec],
        *,
        include_defaults: bool = True,
        max_capabilities: int = 50,
    ) -> list[CapabilitySpec]:
        """Return the subset of capabilities relevant to the query."""
        active_domains = self.classify_domains(query)
        if include_defaults:
            active_domains.update(self._default_domains)

        selected: list[CapabilitySpec] = []
        for spec in capabilities:
            domain = self.domain_for_capability(spec)
            if domain in active_domains:
                selected.append(spec)

        # If filtering produced empty result, return all capabilities up to max limit
        if not selected:
            selected = capabilities[:max_capabilities]

        return sorted(selected[:max_capabilities], key=lambda item: item.name)
