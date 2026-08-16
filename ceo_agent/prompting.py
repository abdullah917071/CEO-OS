"""Prompt formatter for the CEO OS Executive AI Agent."""

from __future__ import annotations

import json
from typing import Any

from ceo_agent.contracts import CeoMessage
from core.contracts import CapabilitySpec

DEFAULT_CEO_SYSTEM_PROMPT = """You are the CEO OS Autonomous Executive AI Agent, \
operating as the deterministic central intelligence of the user's executive operating system.

You solve complex directives through rigorous scratchpad reasoning, \
typed enterprise capability tool calling, and continuous self-reflection.

### EXECUTION RULES:
1. Wrap internal reasoning, hypotheses, and decomposition inside `<thought>` ... `</thought>` tags.
2. Formulate tool calls inside `<tool_call>` ... `</tool_call>` tags using valid JSON formatted with `"name"` and `"arguments"`.
   Example:
   <tool_call>
   {"name": "agents.delegate.research", "arguments": {"objective": "Competitor pricing research", "items": ["Competitor A", "Competitor B"]}}
   </tool_call>
3. Always verify evidence before claiming success. Never hallucinate nonexistent tool outputs.
4. When a tool completes, the environment returns the result inside `<tool_response>` tags.
5. Provide concise, high-assurance executive summaries with verifiable outcomes.
"""


class CeoPromptFormatter:
    """Formats executive prompt contexts and tool specifications for the CEO OS reasoning loop."""

    def __init__(self, system_prompt: str = DEFAULT_CEO_SYSTEM_PROMPT) -> None:
        self.system_prompt = system_prompt

    def format_system_prompt(self, capabilities: list[CapabilitySpec] | None = None) -> str:
        """Compose the complete system prompt with available capability definitions."""
        prompt = self.system_prompt.strip()
        if capabilities:
            tools_spec: list[dict[str, Any]] = []
            for cap in capabilities:
                risk_val = (
                    cap.risk.value
                    if hasattr(cap.risk, "value")
                    else str(getattr(cap, "risk_level", "R0"))
                )
                schema_val = getattr(cap, "input_schema", getattr(cap, "schema", {}))
                tools_spec.append(
                    {
                        "name": cap.name,
                        "description": cap.description,
                        "risk_level": risk_val,
                        "schema": schema_val,
                    }
                )
            tools_json = json.dumps(tools_spec, indent=2)
            prompt += f"\n\n### AVAILABLE ENTERPRISE CAPABILITIES:\n```json\n{tools_json}\n```"
        return prompt

    def format_history(self, messages: list[CeoMessage]) -> list[dict[str, str]]:
        """Format CEO messages into standard conversation roles."""
        result: list[dict[str, str]] = []
        for msg in messages:
            content = msg.content
            if msg.thought:
                content = f"<thought>\n{msg.thought}\n</thought>\n" + content
            result.append({"role": msg.role.value, "content": content})
        return result


# Backwards compatibility alias
HermesPromptFormatter = CeoPromptFormatter
