"""Hermes Tool Parser: extracts thoughts, scratchpad reasoning, and tool calls."""

from __future__ import annotations

import json
import logging
import re

from hermes.contracts import HermesToolCall

logger = logging.getLogger(__name__)


class HermesToolParser:
    """Parses Hermes 2/3 XML tags and JSON function call structures."""

    @staticmethod
    def extract_thought(text: str) -> str:
        """Extract scratchpad reasoning inside <thought> or <scratchpad> tags."""
        match = re.search(
            r"<(?:thought|scratchpad)>(.*?)</(?:thought|scratchpad)>",
            text,
            re.DOTALL | re.I,
        )
        if match:
            return match.group(1).strip()
        tool_match = re.search(r"<tool_call>", text, re.I)
        if tool_match:
            preamble = text[: tool_match.start()].strip()
            if preamble:
                return preamble
        return ""

    @staticmethod
    def extract_tool_calls(text: str) -> list[HermesToolCall]:
        """Extract all <tool_call> blocks from text."""
        calls: list[HermesToolCall] = []

        xml_matches = re.finditer(r"<tool_call>\s*(.*?)\s*</tool_call>", text, re.DOTALL | re.I)
        for m in xml_matches:
            raw_json = m.group(1).strip()
            raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json)
            raw_json = re.sub(r"\s*```$", "", raw_json)
            try:
                data = json.loads(raw_json)
                if isinstance(data, dict) and "name" in data:
                    args = data.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {"raw": args}
                    calls.append(
                        HermesToolCall(
                            name=data["name"],
                            arguments=args if isinstance(args, dict) else {},
                        )
                    )
            except Exception as exc:
                logger.warning("Failed to parse tool call JSON: %s (error: %s)", raw_json, exc)

        if calls:
            return calls

        fence_match = re.search(r"```(?:json)?\s*(\{\s*\"name\"\s*:.*?)\s*```", text, re.DOTALL)
        if fence_match:
            try:
                data = json.loads(fence_match.group(1).strip())
                if isinstance(data, dict) and "name" in data:
                    args = data.get("arguments", {})
                    calls.append(
                        HermesToolCall(
                            name=data["name"],
                            arguments=args if isinstance(args, dict) else {},
                        )
                    )
            except Exception:
                pass

        return calls

    @staticmethod
    def strip_tool_tags(text: str) -> str:
        """Remove <thought> and <tool_call> blocks to return clean final response text."""
        cleaned = re.sub(
            r"<(?:thought|scratchpad)>.*?</(?:thought|scratchpad)>",
            "",
            text,
            flags=re.DOTALL | re.I,
        )
        cleaned = re.sub(r"<tool_call>.*?</tool_call>", "", cleaned, flags=re.DOTALL | re.I)
        return cleaned.strip()
