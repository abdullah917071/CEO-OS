from __future__ import annotations

import ast
import asyncio
import json
import operator
import shlex
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from core.contracts import CapabilitySpec, RiskLevel, ToolResult


class TimeTool:
    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec("time.now", "Return the current UTC time", {}, RiskLevel.READ)

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del arguments
        del idempotency_key
        value = datetime.now(UTC).isoformat()
        return ToolResult({"utc": value}, [f"Clock read at {value}"])


_OPERATORS: dict[type[ast.AST], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _evaluate(node: ast.AST) -> int | float:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return cast(
            int | float, _OPERATORS[type(node.op)](_evaluate(node.left), _evaluate(node.right))
        )
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return cast(int | float, _OPERATORS[type(node.op)](_evaluate(node.operand)))
    raise ValueError("Expression contains unsupported syntax")


class CalculatorTool:
    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "calculator.evaluate",
            "Evaluate basic arithmetic without executing code",
            {
                "type": "object",
                "required": ["expression"],
                "properties": {"expression": {"type": "string"}},
            },
            RiskLevel.READ,
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        expression = str(arguments["expression"])
        if len(expression) > 200:
            raise ValueError("Expression is too long")
        result = _evaluate(ast.parse(expression, mode="eval"))
        return ToolResult({"expression": expression, "result": result}, [f"Evaluated {expression}"])


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, raw_path: str) -> Path:
        candidate = (self.root / raw_path).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise PermissionError("Path escapes the configured workspace")
        return candidate


class MakeDirectoryTool:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "files.mkdir",
            "Create a directory inside the task workspace",
            {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}},
            RiskLevel.HARMLESS_WRITE,
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        path = self.workspace.resolve(str(arguments["path"]))
        path.mkdir(parents=True, exist_ok=True)
        return ToolResult({"path": str(path)}, [f"Directory exists: {path}"])


class WriteFileTool:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "files.write",
            "Write UTF-8 text inside the task workspace",
            {
                "type": "object",
                "required": ["path", "content"],
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            },
            RiskLevel.HARMLESS_WRITE,
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        path = self.workspace.resolve(str(arguments["path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        content = str(arguments["content"])
        path.write_text(content, encoding="utf-8")
        return ToolResult(
            {"path": str(path), "bytes": len(content.encode())}, [f"Wrote file: {path}"]
        )


class ReadFileTool:
    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "files.read",
            "Read UTF-8 text inside the task workspace",
            {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}},
            RiskLevel.READ,
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        path = self.workspace.resolve(str(arguments["path"]))
        content = path.read_text(encoding="utf-8")
        return ToolResult({"path": str(path), "content": content}, [f"Read file: {path}"])


class NotesTool:
    def __init__(self, workspace: Workspace) -> None:
        self.path = workspace.resolve(".ceo-os/notes.json")

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "notes.add",
            "Append a note to the local notes store",
            {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}},
            RiskLevel.HARMLESS_WRITE,
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        notes = json.loads(self.path.read_text()) if self.path.exists() else []
        if idempotency_key and any(
            note.get("idempotency_key") == idempotency_key for note in notes
        ):
            existing = next(
                note for note in notes if note.get("idempotency_key") == idempotency_key
            )
            return ToolResult({"note": existing, "count": len(notes)}, ["Note already stored"])
        note = {
            "text": str(arguments["text"]),
            "created_at": datetime.now(UTC).isoformat(),
            "idempotency_key": idempotency_key,
        }
        notes.append(note)
        self.path.write_text(json.dumps(notes, indent=2), encoding="utf-8")
        return ToolResult({"note": note, "count": len(notes)}, [f"Stored note #{len(notes)}"])


class ShellTool:
    ALLOWED = {"pwd", "ls", "rg", "git"}
    ALLOWED_GIT = {"status", "diff", "log", "show"}

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    @property
    def spec(self) -> CapabilitySpec:
        return CapabilitySpec(
            "shell.execute",
            "Run an allowlisted read-only command in the workspace",
            {
                "type": "object",
                "required": ["command"],
                "properties": {"command": {"type": "string"}},
            },
            RiskLevel.READ,
        )

    async def execute(
        self, arguments: dict[str, Any], *, idempotency_key: str | None = None
    ) -> ToolResult:
        del idempotency_key
        parts = shlex.split(str(arguments["command"]))
        if not parts or parts[0] not in self.ALLOWED:
            raise PermissionError("Command is not allowlisted")
        if parts[0] == "git" and (len(parts) < 2 or parts[1] not in self.ALLOWED_GIT):
            raise PermissionError("Git subcommand is not read-only or allowlisted")
        process = await asyncio.create_subprocess_exec(
            *parts,
            cwd=self.workspace.root,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
        except TimeoutError:
            process.kill()
            await process.wait()
            raise TimeoutError("Command exceeded 10 seconds") from None
        output = stdout.decode(errors="replace")[:20_000]
        error = stderr.decode(errors="replace")[:20_000]
        return ToolResult(
            {"exit_code": process.returncode, "stdout": output, "stderr": error},
            [f"Command exited with code {process.returncode}"],
        )


def built_in_tools(workspace_root: Path) -> list[Any]:
    workspace = Workspace(workspace_root)
    return [
        TimeTool(),
        CalculatorTool(),
        MakeDirectoryTool(workspace),
        WriteFileTool(workspace),
        ReadFileTool(workspace),
        NotesTool(workspace),
        ShellTool(workspace),
    ]
