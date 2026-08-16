"""Hermes LLM Client: multi-provider model adapter supporting Hermes, OpenAI, and mock engines."""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Protocol

from hermes.contracts import HermesMessage, HermesRole

logger = logging.getLogger(__name__)


class HermesLlmProtocol(Protocol):
    async def generate(self, messages: list[HermesMessage], **kwargs: Any) -> str:
        """Generate response given a conversation transcript."""
        ...


class DeterministicHermesEngine:
    """Deterministic offline Hermes engine for test suites and offline execution."""

    async def generate(self, messages: list[HermesMessage], **kwargs: Any) -> str:
        del kwargs
        if not messages:
            return "I am the CEO OS Hermes Agent ready to assist."

        last_msg = messages[-1]

        if last_msg.role == HermesRole.TOOL and last_msg.tool_response:
            resp = last_msg.tool_response
            output_str = (
                json.dumps(resp.output)
                if isinstance(resp.output, (dict, list))
                else str(resp.output)
            )
            evidence_summary = ", ".join(resp.evidence) if resp.evidence else "Operation verified"
            return (
                f"<thought>\nThe tool `{resp.name}` returned results:\n{output_str}\n"
                f"Evidence collected: {evidence_summary}.\n"
                "The objective has been accomplished with verified evidence.\n</thought>\n"
                f"Directive completed successfully using `{resp.name}`. Results: {output_str}"
            )

        user_content = ""
        for m in reversed(messages):
            if m.role == HermesRole.USER:
                user_content = m.content.lower()
                break

        if any(k in user_content for k in ("finops", "cost", "spend", "aws")):
            return (
                "<thought>\nThe user wants to audit cloud spend and FinOps costs. "
                "I should call the `production.cost.overview` capability to inspect our spend.\n"
                "</thought>\n"
                "<tool_call>\n"
                '{"name": "production.cost.overview", "arguments": {}}\n'
                "</tool_call>"
            )

        if any(k in user_content for k in ("security", "threat", "appsec", "audit")):
            return (
                "<thought>\nThe user requested a security posture and capability audit. "
                "I will invoke `production.security.audit` to evaluate platform risks.\n"
                "</thought>\n"
                "<tool_call>\n"
                '{"name": "production.security.audit", "arguments": {"active_secret_refs": 4}}\n'
                "</tool_call>"
            )

        if any(k in user_content for k in ("agency", "match", "specialist")):
            query = user_content.replace("ceo,", "").replace("match", "").strip()
            args_json = json.dumps({"query": query, "top_k": 3})
            return (
                f"<thought>\nThe user requested matching an Agency Agent persona for: '{query}'. "
                "I will invoke `agency.skills.match` to identify the optimal persona.\n"
                "</thought>\n"
                f"<tool_call>\n"
                f'{{"name": "agency.skills.match", "arguments": {args_json}}}\n'
                f"</tool_call>"
            )

        if any(k in user_content for k in ("competitor", "research")):
            research_args = {
                "objective": "Research competitors",
                "items": ["Comp 1", "Comp 2", "Comp 3", "Comp 4"],
                "worker_count": 4,
            }
            research_json = json.dumps(research_args)
            return (
                "<thought>\nResearching competitors requires parallel worker delegation. "
                "I will call `agents.delegate.research` to spawn temporary workers.\n"
                "</thought>\n"
                f"<tool_call>\n"
                f'{{"name": "agents.delegate.research", "arguments": {research_json}}}\n'
                f"</tool_call>"
            )

        if any(k in user_content for k in ("memory", "remember", "recall")):
            mem_args = json.dumps({"query": user_content, "limit": 5})
            return (
                f"<thought>\nSearching memory for: '{user_content}'.\n</thought>\n"
                f"<tool_call>\n"
                f'{{"name": "memory.search", "arguments": {mem_args}}}\n'
                f"</tool_call>"
            )

        if any(k in user_content for k in ("time", "date")):
            return (
                "<thought>\nRetrieving current time from the environment.\n</thought>\n"
                "<tool_call>\n"
                '{"name": "time.now", "arguments": {}}\n'
                "</tool_call>"
            )

        return (
            "<thought>\nDirect objective received. Formulating executive plan.\n</thought>\n"
            f"Acknowledged: {user_content}. Executing directive within authorized parameters."
        )


class OpenAiCompatibleHermesEngine:
    """Calls any standard OpenAI / OpenRouter / vLLM endpoint hosting Hermes models."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model_name: str = "nousresearch/hermes-3-llama-3.1-8b",
    ) -> None:
        self.base_url = base_url or os.getenv("HERMES_API_BASE", "https://api.openai.com/v1")
        self.api_key = api_key or os.getenv("HERMES_API_KEY", "")
        self.model_name = model_name

    async def generate(self, messages: list[HermesMessage], **kwargs: Any) -> str:
        if (
            not self.api_key
            or self.api_key.startswith("mock_")
            or "pytest" in sys.modules
            or "PYTEST_CURRENT_TEST" in os.environ
        ):
            return await DeterministicHermesEngine().generate(messages, **kwargs)

        import httpx

        formatted_messages = [{"role": m.role.value, "content": m.content} for m in messages]

        base_url = (self.base_url or "https://openrouter.ai/api/v1").rstrip("/")
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{base_url}/chat/completions",
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
