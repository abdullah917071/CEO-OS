"""MLOps Trajectory Store and recorder for CEO OS agent reasoning traces."""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from pathlib import Path

from ceo_agent.contracts import CeoTrajectoryRecord

logger = logging.getLogger(__name__)


class CeoTrajectoryStore:
    """Stores reasoning trajectories and exports JSONL datasets for model fine-tuning."""

    def __init__(self, storage_dir: Path | None = None) -> None:
        self.storage_dir = storage_dir or Path("./data/trajectories")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, CeoTrajectoryRecord] = {}

    def save(self, record: CeoTrajectoryRecord) -> None:
        """Persist a completed trajectory record to memory cache and disk."""
        self._memory_cache[record.trajectory_id] = record
        file_path = self.storage_dir / f"{record.trajectory_id}.json"
        try:
            payload = {
                "trajectory_id": record.trajectory_id,
                "task_id": record.task_id,
                "objective": record.objective,
                "system_prompt": record.system_prompt,
                "status": record.status,
                "total_duration_ms": record.total_duration_ms,
                "final_response": record.final_response,
                "recorded_at": record.recorded_at,
                "steps": [
                    {
                        "step_index": s.step_index,
                        "thought": s.thought,
                        "duration_ms": s.duration_ms,
                        "timestamp": s.timestamp,
                        "tool_call": (
                            {"name": s.tool_call.name, "arguments": s.tool_call.arguments}
                            if s.tool_call
                            else None
                        ),
                        "tool_response": (
                            {
                                "name": s.tool_response.name,
                                "output": s.tool_response.output,
                                "evidence": s.tool_response.evidence,
                                "error": s.tool_response.error,
                            }
                            if s.tool_response
                            else None
                        ),
                    }
                    for s in record.steps
                ],
            }
            file_path.write_text(json.dumps(payload, indent=2))
        except Exception as exc:
            logger.warning("Failed to save trajectory file %s: %s", file_path, exc)

    def get(self, trajectory_id: str) -> CeoTrajectoryRecord | None:
        """Retrieve a trajectory by ID."""
        return self._memory_cache.get(trajectory_id)

    def list_all(self) -> Sequence[CeoTrajectoryRecord]:
        """List all indexed trajectories."""
        return list(self._memory_cache.values())

    def export_jsonl(self, output_file: Path) -> int:
        """Export all recorded trajectories into OpenAI/Hermes JSONL fine-tuning format."""
        count = 0
        with output_file.open("w", encoding="utf-8") as f:
            for record in self._memory_cache.values():
                messages: list[dict[str, str]] = [
                    {"role": "system", "content": record.system_prompt},
                    {"role": "user", "content": record.objective},
                ]
                for s in record.steps:
                    if s.thought:
                        messages.append(
                            {"role": "assistant", "content": f"<thought>\n{s.thought}\n</thought>"}
                        )
                    if s.tool_call:
                        call_json = json.dumps(
                            {"name": s.tool_call.name, "arguments": s.tool_call.arguments}
                        )
                        call_str = f"<tool_call>\n{call_json}\n</tool_call>"
                        messages.append({"role": "assistant", "content": call_str})
                    if s.tool_response:
                        resp_json = json.dumps(s.tool_response.output)
                        resp_str = f"<tool_response>\n{resp_json}\n</tool_response>"
                        messages.append({"role": "tool", "content": resp_str})
                messages.append({"role": "assistant", "content": record.final_response})
                f.write(json.dumps({"messages": messages}) + "\n")
                count += 1
        return count


# Backwards compatibility alias
HermesTrajectoryStore = CeoTrajectoryStore
