"""XML and JSON parser for CEO OS ReAct reasoning outputs."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from ceo_agent.contracts import CeoToolCall

logger = logging.getLogger(__name__)

THOUGHT_REGEX = re.compile(r"<thought>(.*?)</thought>", re.DOTALL | re.IGNORECASE)
TOOL_CALL_REGEX = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL | re.IGNORECASE)


class CeoToolParser:
    """Extracts scratchpad reasoning and structured tool calls from model completions."""

    @staticmethod
    def extract_thought(text: str) -> str:
        """Extract thought block from model output."""
        matches = THOUGHT_REGEX.findall(text)
        if matches:
            return "\n".join(m.strip() for m in matches)
        return ""

    @staticmethod
    def extract_tool_calls(text: str) -> list[CeoToolCall]:
        """Extract JSON tool calls inside <tool_call> tags."""
        matches = TOOL_CALL_REGEX.findall(text)
        calls: list[CeoToolCall] = []

        for raw_match in matches:
            raw_match = raw_match.strip()
            # Clean markdown codeblocks if model wrapped inside
            if raw_match.startswith("```json"):
                raw_match = raw_match[7:]
            elif raw_match.startswith("```"):
                raw_match = raw_match[3:]
            if raw_match.endswith("```"):
                raw_match = raw_match[:-3]
            raw_match = raw_match.strip()

            try:
                parsed: Any = json.loads(raw_match)
                if isinstance(parsed, dict) and "name" in parsed:
                    calls.append(
                        CeoToolCall(
                            name=str(parsed["name"]),
                            arguments=parsed.get("arguments", {}),
                            call_id=str(parsed.get("call_id", f"call_{len(calls)}")),
                        )
                    )
                elif isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict) and "name" in item:
                            calls.append(
                                CeoToolCall(
                                    name=str(item["name"]),
                                    arguments=item.get("arguments", {}),
                                    call_id=str(item.get("call_id", f"call_{len(calls)}")),
                                )
                            )
            except Exception as exc:
                logger.warning(
                    "Failed to parse tool call JSON: %s (error: %s)",
                    raw_match[:200],
                    exc,
                )

        return calls

    @staticmethod
    def clean_final_answer(text: str) -> str:
        """Strip internal reasoning and tool call tags from the final user response."""
        cleaned = THOUGHT_REGEX.sub("", text)
        cleaned = TOOL_CALL_REGEX.sub("", cleaned)
        return cleaned.strip()


# Backwards compatibility alias
HermesToolParser = CeoToolParser
