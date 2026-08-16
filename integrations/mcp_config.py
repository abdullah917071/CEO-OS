"""Load MCP server configurations from a JSON file or environment variable."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from core.contracts import RiskLevel
from integrations.mcp_adapter import McpServerConfig

logger = logging.getLogger(__name__)


def load_mcp_configs(
    json_path: Path | None = None,
    env_json: str | None = None,
) -> list[McpServerConfig]:
    """Parse MCP server definitions from a JSON config file or raw JSON string.

    Expected JSON format::

        [
            {
                "name": "my-server",
                "command": "python",
                "args": ["path/to/server.py"],
                "risk_ceiling": "R1",
                "enabled": true,
                "timeout_seconds": 30
            }
        ]

    Returns an empty list when no configuration is provided (safe default).
    """
    raw: str | None = None
    if json_path is not None and json_path.exists():
        raw = json_path.read_text(encoding="utf-8")
    elif env_json:
        raw = env_json

    if not raw or not raw.strip():
        return []

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Invalid JSON in MCP server config")
        return []

    if not isinstance(data, list):
        logger.error("MCP server config must be a JSON array")
        return []

    configs: list[McpServerConfig] = []
    for entry in data:
        if not isinstance(entry, dict) or "name" not in entry or "command" not in entry:
            logger.warning("Skipping invalid MCP server entry: %s", entry)
            continue
        risk_str = entry.get("risk_ceiling", "R1")
        try:
            risk = RiskLevel(risk_str)
        except ValueError:
            logger.warning(
                "Unknown risk level %s for %s, defaulting to R1", risk_str, entry["name"]
            )
            risk = RiskLevel.HARMLESS_WRITE
        configs.append(
            McpServerConfig(
                name=entry["name"],
                command=entry["command"],
                args=entry.get("args", []),
                env=entry.get("env"),
                domain=entry.get("domain", "integrations"),
                risk_ceiling=risk,
                enabled=entry.get("enabled", True),
                timeout_seconds=entry.get("timeout_seconds", 30),
            )
        )

    return configs
