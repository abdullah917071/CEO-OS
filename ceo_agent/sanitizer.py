"""Execution summary sanitizer: formats safe, structured metadata without leaking internal raw scratchpads."""

from __future__ import annotations

import re
from typing import Any

from ceo_agent.contracts import CeoTrajectoryStep


def sanitize_thought_text(raw_thought: str, max_chars: int = 300) -> str:
    """Strip sensitive markers, internal prompt directives, and truncate unbounded scratchpads."""
    if not raw_thought:
        return "Analyzing objective and determining next operational action."

    # Remove internal XML artifacts if present
    cleaned = re.sub(
        r"</?(?:thought|tool_call|tool_response|system|context)[^>]*>", "", raw_thought
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) > max_chars:
        return cleaned[:max_chars].rstrip() + "..."
    return cleaned


def create_safe_execution_summary(
    objective: str,
    steps: list[CeoTrajectoryStep],
    final_answer: str,
    status: str,
    confidence: float = 0.90,
) -> dict[str, Any]:
    """Build structured, audit-grade execution summary."""
    step_summaries: list[dict[str, Any]] = []

    for step in steps:
        tool_name = step.tool_call.name if step.tool_call else "none"
        args_keys = list(step.tool_call.arguments.keys()) if step.tool_call else []
        has_error = bool(step.tool_response and step.tool_response.error)
        output_keys = list(step.tool_response.output.keys()) if step.tool_response else []

        step_summaries.append(
            {
                "turn": step.turn_index,
                "step": step.step_index,
                "capability": tool_name,
                "parameters_provided": args_keys,
                "status": "ERROR" if has_error else "SUCCESS",
                "output_fields": output_keys,
                "duration_ms": step.duration_ms,
            }
        )

    return {
        "intent": objective,
        "status": status,
        "capabilities_executed": [
            s["capability"] for s in step_summaries if s["capability"] != "none"
        ],
        "steps_count": len(steps),
        "step_details": step_summaries,
        "decision": final_answer[:500] if final_answer else "Execution finished.",
        "confidence": confidence,
    }
