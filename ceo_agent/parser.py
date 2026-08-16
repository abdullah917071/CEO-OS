"""Robust parser for CEO OS ReAct reasoning outputs with JSON and XML fallbacks."""

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
        """Extract thought block from model output with unclosed tag fallback."""
        matches = THOUGHT_REGEX.findall(text)
        if matches:
            return "\n".join(m.strip() for m in matches)

        # Fallback for unclosed <thought> block
        if "<thought>" in text.lower() and "</thought>" not in text.lower():
            start = text.lower().find("<thought>") + len("<thought>")
            end = text.lower().find("<tool_call>") if "<tool_call>" in text.lower() else len(text)
            return text[start:end].strip()

        return ""

    @staticmethod
    def extract_tool_calls(text: str) -> list[CeoToolCall]:
        """Extract tool calls from <tool_call> tags or top-level JSON objects."""
        calls: list[CeoToolCall] = []

        # 1. Standard <tool_call> tags
        matches = TOOL_CALL_REGEX.findall(text)

        # Fallback for unclosed <tool_call> block
        if not matches and "<tool_call>" in text.lower() and "</tool_call>" not in text.lower():
            start = text.lower().find("<tool_call>") + len("<tool_call>")
            matches = [text[start:].strip()]

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
                logger.debug(
                    "Failed to parse tool call JSON: %s (error: %s)",
                    raw_match[:200],
                    exc,
                )

        # 2. If no tag-based tool call found, try parsing pure JSON block with "name" and "arguments"
        if not calls and text.strip().startswith("{") and text.strip().endswith("}"):
            try:
                parsed = json.loads(text.strip())
                if (
                    isinstance(parsed, dict)
                    and "name" in parsed
                    and ("arguments" in parsed or "parameters" in parsed)
                ):
                    calls.append(
                        CeoToolCall(
                            name=str(parsed["name"]),
                            arguments=parsed.get("arguments") or parsed.get("parameters") or {},
                            call_id=str(parsed.get("call_id", "call_0")),
                        )
                    )
            except Exception:
                pass

        return calls

    @staticmethod
    def clean_final_answer(text: str) -> str:
        """Strip internal reasoning and tool call tags from the final user response."""
        cleaned = THOUGHT_REGEX.sub("", text)
        cleaned = TOOL_CALL_REGEX.sub("", cleaned)
        # Strip trailing unclosed tags if any
        cleaned = re.sub(
            r"<thought>.*?(?:<tool_call>|$)", "", cleaned, flags=re.DOTALL | re.IGNORECASE
        )
        cleaned = re.sub(r"<tool_call>.*$", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(
            r"</?(?:thought|tool_call|tool_response)>", "", cleaned, flags=re.IGNORECASE
        )
        return cleaned.strip()


# Backwards compatibility alias
HermesToolParser = CeoToolParser
