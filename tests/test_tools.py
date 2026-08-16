from pathlib import Path

import pytest

from tools.builtin import CalculatorTool, NotesTool, ShellTool, Workspace, WriteFileTool


@pytest.mark.asyncio
async def test_calculator_rejects_code_execution() -> None:
    tool = CalculatorTool()
    with pytest.raises(ValueError, match="unsupported"):
        await tool.execute({"expression": "__import__('os').getcwd()"})


@pytest.mark.asyncio
async def test_files_cannot_escape_workspace(tmp_path: Path) -> None:
    tool = WriteFileTool(Workspace(tmp_path))
    with pytest.raises(PermissionError, match="escapes"):
        await tool.execute({"path": "../outside.txt", "content": "no"})


@pytest.mark.asyncio
async def test_shell_rejects_non_allowlisted_command(tmp_path: Path) -> None:
    tool = ShellTool(Workspace(tmp_path))
    with pytest.raises(PermissionError, match="allowlisted"):
        await tool.execute({"command": "rm -rf anything"})


@pytest.mark.asyncio
async def test_notes_tool_deduplicates_retried_effect(tmp_path: Path) -> None:
    tool = NotesTool(Workspace(tmp_path))
    first = await tool.execute({"text": "one note"}, idempotency_key="stable-operation")
    second = await tool.execute({"text": "one note"}, idempotency_key="stable-operation")
    assert first.output["count"] == 1
    assert second.output["count"] == 1
    assert second.evidence == ["Note already stored"]
