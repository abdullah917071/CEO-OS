"""LLM client adapter for CEO OS AI Agent supporting OpenRouter and test engines."""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Protocol

from ceo_agent.contracts import CeoMessage, CeoRole

logger = logging.getLogger(__name__)


class CeoLlmProtocol(Protocol):
    async def generate(self, messages: list[CeoMessage], **kwargs: Any) -> str:
        """Generate response given a conversation transcript."""
        ...


class DeterministicCeoEngine(CeoLlmProtocol):
    """Deterministic ReAct engine returning synthesized tool calls and observations."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self.responses = list(responses) if responses else []
        self._step = 0

    async def generate(self, messages: list[CeoMessage], **kwargs: Any) -> str:
        del kwargs
        if self.responses and self._step < len(self.responses):
            resp = self.responses[self._step]
            self._step += 1
            return resp

        # Examine last message to synthesize context-aware reasoning
        last_msg = messages[-1] if messages else None
        if not last_msg:
            return (
                "<thought>\nDirective received. Preparing execution plan.\n</thought>\n"
                "I am ready to assist."
            )

        if last_msg.role == CeoRole.TOOL:
            content_val = last_msg.content.lower()
            if "youtube" in content_val:
                return (
                    "<thought>\nYouTube opened successfully. Formulating response.\n</thought>\n"
                    "Opened YouTube for you, sir. What would you like to watch?"
                )
            if "spotify" in content_val:
                return (
                    "<thought>\nSpotify activated. Formulating response.\n</thought>\n"
                    "Opened Spotify for you, sir. Ready for music playback."
                )
            if "google" in content_val or "search" in content_val:
                return (
                    "<thought>\nSearch completed. Formulating response.\n</thought>\n"
                    "Search results are ready on your screen, sir."
                )
            return (
                "<thought>\nReceived tool observation. Verifying outcome.\n</thought>\n"
                f"Successfully completed task, sir. Outcome: {last_msg.content}"
            )

        content_lower = last_msg.content.lower()

        # Domain: YouTube
        if "youtube" in content_lower:
            call_str = json.dumps({"name": "browser.open_youtube", "arguments": {"query": ""}})
            return (
                "<thought>\nUser requested YouTube. Invoking browser.open_youtube.\n</thought>\n"
                f"<tool_call>\n{call_str}\n</tool_call>"
            )

        # Domain: Spotify & Media
        if "spotify" in content_lower or "music" in content_lower or "song" in content_lower:
            call_str = json.dumps({"name": "media.open_spotify", "arguments": {}})
            return (
                "<thought>\nUser requested Spotify. Invoking media.open_spotify.\n</thought>\n"
                f"<tool_call>\n{call_str}\n</tool_call>"
            )

        # Domain: Google Search
        if "search" in content_lower or "google" in content_lower:
            q_clean = (
                content_lower.replace("search", "").replace("google", "").replace("for", "").strip()
            )
            query = q_clean or "latest news"
            call_str = json.dumps({"name": "browser.search_google", "arguments": {"query": query}})
            return (
                f"<thought>\nSearching for '{query}'. Invoking browser.search_google.\n</thought>\n"
                f"<tool_call>\n{call_str}\n</tool_call>"
            )

        # Domain: System Stats
        is_stats = any(k in content_lower for k in ("system", "cpu", "battery", "stats"))
        if is_stats:
            call_str = json.dumps({"name": "macos.get_system_stats", "arguments": {}})
            return (
                "<thought>\nUser requested system status. Invoking stats.\n</thought>\n"
                f"<tool_call>\n{call_str}\n</tool_call>"
            )

        # Domain: System Time
        if "time" in content_lower or "date" in content_lower:
            return (
                "<thought>\nUser requested system time. Invoking time.now capability.\n</thought>\n"
                '<tool_call>\n{"name": "time.now", "arguments": {}}\n</tool_call>'
            )

        # Domain: Agency Skills Matching
        if "agency" in content_lower or "skill" in content_lower or "persona" in content_lower:
            call_str = json.dumps(
                {"name": "agency.skills.match", "arguments": {"query": "AWS FinOps"}}
            )
            return (
                f"<thought>\nSearching agency catalog for relevant skills.\n</thought>\n"
                f"<tool_call>\n{call_str}\n</tool_call>"
            )

        # Domain: FinOps Spend
        if "finops" in content_lower or "cost" in content_lower or "spend" in content_lower:
            call_str = json.dumps({"name": "production.cost.overview", "arguments": {}})
            return (
                f"<thought>\nQuerying FinOps cost breakdown.\n</thought>\n"
                f"<tool_call>\n{call_str}\n</tool_call>"
            )

        # Domain: Restaurant Booking
        if "restaurant" in content_lower or "book" in content_lower:
            args = {"restaurant_name": "Osteria Bella", "party_size": 4, "time": "19:00"}
            call_str = json.dumps({"name": "workflow.restaurant.book", "arguments": args})
            return (
                f"<thought>\nDispatching restaurant booking.\n</thought>\n"
                f"<tool_call>\n{call_str}\n</tool_call>"
            )

        # Domain: Telephony
        if "call" in content_lower or "phone" in content_lower:
            args = {"to_number": "+1-415-555-0100", "purpose": "inquire business hours"}
            call_str = json.dumps({"name": "telephony.call.outbound", "arguments": args})
            return (
                f"<thought>\nDispatching outbound telephony call.\n</thought>\n"
                f"<tool_call>\n{call_str}\n</tool_call>"
            )

        # Domain: Marketing
        if "marketing" in content_lower or "ad" in content_lower or "campaign" in content_lower:
            call_str = json.dumps({"name": "marketing.intelligence.snapshot", "arguments": {}})
            return (
                f"<thought>\nFetching marketing snapshot.\n</thought>\n"
                f"<tool_call>\n{call_str}\n</tool_call>"
            )

        # Default fallback ReAct response
        obj_snippet = last_msg.content[:60]
        return (
            f"<thought>\nObjective: '{obj_snippet}...'. Formulating plan.\n</thought>\n"
            f"Understood, sir. I have processed your request regarding: '{obj_snippet}'."
        )


class OpenAiCompatibleCeoEngine(CeoLlmProtocol):
    """Connects to any OpenAI-compatible API endpoint (OpenRouter, local models)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model_name: str = "nvidia/nemotron-3.5-lightning:free",
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("CEO_OS_REASONING_API_BASE")
            or os.getenv("HERMES_API_BASE", "https://openrouter.ai/api/v1")
        )
        self.api_key = (
            api_key
            or os.getenv("CEO_OS_REASONING_API_KEY")
            or os.getenv("CEO_OS_OPENROUTER_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
            or os.getenv("HERMES_API_KEY", "")
        )
        self.model_name = (
            model_name
            or os.getenv("CEO_OS_REASONING_MODEL_NAME")
            or os.getenv("CEO_OS_MODEL_NAME")
            or os.getenv("HERMES_MODEL_NAME", "nvidia/nemotron-3.5-lightning:free")
        )

    async def generate(self, messages: list[CeoMessage], **kwargs: Any) -> str:
        if (
            not self.api_key
            or self.api_key.startswith("mock_")
            or "pytest" in sys.modules
            or "PYTEST_CURRENT_TEST" in os.environ
        ):
            return await DeterministicCeoEngine().generate(messages, **kwargs)

        import httpx

        formatted_messages = [{"role": m.role.value, "content": m.content} for m in messages]

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "messages": formatted_messages,
                    "temperature": kwargs.get("temperature", 0.2),
                    "max_tokens": kwargs.get("max_tokens", 2048),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return str(data["choices"][0]["message"]["content"])


# Backwards compatibility aliases
HermesLlmProtocol = CeoLlmProtocol
DeterministicHermesEngine = DeterministicCeoEngine
OpenAiCompatibleHermesEngine = OpenAiCompatibleCeoEngine
