"""Hermes Prompt Formatter: generates branded executive Hermes system prompts and tool schemas."""

from __future__ import annotations

import json
from typing import Any

from core.contracts import CapabilitySpec


class HermesPromptFormatter:
    """Formats prompts in standard Nous Hermes 2/3 function calling and scratchpad format."""

    @staticmethod
    def format_tool_schema(capabilities: list[CapabilitySpec]) -> str:
        """Format capability specifications into Hermes JSON tools array."""
        tools_list: list[dict[str, Any]] = []
        for cap in capabilities:
            tools_list.append(
                {
                    "type": "function",
                    "function": {
                        "name": cap.name,
                        "description": cap.description,
                        "parameters": cap.input_schema,
                    },
                }
            )
        return json.dumps(tools_list, indent=2)

    @classmethod
    def build_system_prompt(
        cls,
        capabilities: list[CapabilitySpec],
        *,
        persona_role: str = "Chief Executive Officer & Autonomous Operations Leader",
        memory_context: list[str] | None = None,
        rules: list[str] | None = None,
    ) -> str:
        """Generate the complete branded Hermes system prompt."""
        tools_json = cls.format_tool_schema(capabilities)
        mem_block = ""
        if memory_context:
            mem_block = "\n## 🧠 Long-Term Memory Context:\n" + "\n".join(
                f"- {m}" for m in memory_context
            )

        rules_block = ""
        if rules:
            rules_block = "\n## 🚨 Critical Operating Rules:\n" + "\n".join(f"- {r}" for r in rules)

        return f"""You are the **CEO OS Autonomous AI Agent**, powered by the Hermes 3 engine.
Role: {persona_role}

You have access to enterprise capabilities and specialist tools.
You solve objectives through scratchpad reasoning, tool calling, and continuous reflection.

# Tool Calling Format
To call a tool, output a `<thought>` tag with reasoning, followed by a `<tool_call>` tag:

<thought>
I need to examine the spend before deciding which resources to rightsize.
</thought>
<tool_call>
{{"name": "production.cost.overview", "arguments": {{}}}}
</tool_call>

When a tool completes, the environment returns the result inside `<tool_response>` tags.

# Available Capabilities:
<tools>
{tools_json}
</tools>
{mem_block}
{rules_block}

Always verify evidence before claiming success. Never hallucinate nonexistent tool outputs.
"""
