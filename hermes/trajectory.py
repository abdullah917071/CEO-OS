"""Hermes Trajectory Store: records and exports agent trajectories for MLOps fine-tuning."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from hermes.contracts import HermesTrajectoryRecord


class HermesTrajectoryStore:
    """Stores and exports full Hermes execution trajectories."""

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        self._storage_dir = Path(storage_dir) if storage_dir else Path("data/hermes/trajectories")
        self._trajectories: dict[str, HermesTrajectoryRecord] = {}

    def record(self, record: HermesTrajectoryRecord) -> None:
        """Save trajectory in-memory and write JSON record."""
        self._trajectories[record.trajectory_id] = record
        try:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            file_path = self._storage_dir / f"{record.trajectory_id}.json"
            file_path.write_text(json.dumps(asdict(record), indent=2), encoding="utf-8")
        except Exception:
            pass

    def get(self, trajectory_id: str) -> HermesTrajectoryRecord | None:
        """Retrieve a recorded trajectory."""
        return self._trajectories.get(trajectory_id)

    def list_all(self) -> list[HermesTrajectoryRecord]:
        """List all recorded trajectories."""
        return list(self._trajectories.values())

    def export_jsonl(self, output_path: Path | str | None = None) -> str:
        """Export all recorded trajectories to a JSONL dataset for Hermes fine-tuning."""
        lines = []
        for traj in self._trajectories.values():
            conversations: list[dict[str, str]] = [
                {"from": "system", "value": traj.system_prompt},
                {"from": "human", "value": traj.objective},
            ]
            entry: dict[str, Any] = {
                "trajectory_id": traj.trajectory_id,
                "task_id": traj.task_id,
                "conversations": conversations,
            }
            for step in traj.steps:
                thought_str = f"<thought>\n{step.thought}\n</thought>\n" if step.thought else ""
                call_str = ""
                if step.tool_call:
                    call_dict = {
                        "name": step.tool_call.name,
                        "arguments": step.tool_call.arguments,
                    }
                    call_str = f"<tool_call>\n{json.dumps(call_dict)}\n</tool_call>"
                conversations.append(
                    {
                        "from": "gpt",
                        "value": f"{thought_str}{call_str}".strip(),
                    }
                )

                if step.tool_response:
                    conversations.append(
                        {
                            "from": "tool",
                            "value": (
                                f"<tool_response>\n{json.dumps(step.tool_response.output)}\n"
                                "</tool_response>"
                            ),
                        }
                    )

            conversations.append({"from": "gpt", "value": traj.final_response})
            lines.append(json.dumps(entry))

        content = "\n".join(lines)
        if output_path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
        return content

    def count(self) -> int:
        return len(self._trajectories)
