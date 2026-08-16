from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

PROTOCOL_VERSION = 1
MAX_RESPONSE_BYTES = 2_000_000


class ComputerHelperError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class ComputerTransport(Protocol):
    @property
    def supported(self) -> bool: ...

    async def request(self, action: str, **arguments: Any) -> dict[str, Any]: ...


class MacHelperClient:
    def __init__(self, executable: Path, timeout_seconds: float = 12) -> None:
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    @property
    def supported(self) -> bool:
        return sys.platform == "darwin" and self.executable.is_file()

    async def request(self, action: str, **arguments: Any) -> dict[str, Any]:
        if not self.supported:
            raise ComputerHelperError("unsupported_environment", "macOS helper is unavailable")
        request_id = str(uuid4())
        payload = json.dumps(
            {"id": request_id, "version": PROTOCOL_VERSION, "action": action, **arguments},
            separators=(",", ":"),
        ).encode()
        process = await asyncio.create_subprocess_exec(
            str(self.executable),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(payload), timeout=self.timeout_seconds
            )
        except TimeoutError:
            process.kill()
            await process.wait()
            raise ComputerHelperError("helper_timeout", "macOS helper timed out") from None
        if len(stdout) > MAX_RESPONSE_BYTES:
            raise ComputerHelperError("response_too_large", "macOS helper response exceeds limit")
        try:
            response = json.loads(stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ComputerHelperError(
                "invalid_response", "macOS helper returned invalid JSON"
            ) from exc
        if not isinstance(response, dict):
            raise ComputerHelperError("invalid_response", "macOS helper response is not an object")
        if response.get("id") != request_id or response.get("version") != PROTOCOL_VERSION:
            raise ComputerHelperError(
                "protocol_mismatch", "macOS helper response does not match request"
            )
        if process.returncode != 0 or response.get("ok") is not True:
            error = response.get("error", {})
            code = str(error.get("code", "helper_failed"))
            message = str(error.get("message", stderr.decode(errors="replace")[:500]))
            raise ComputerHelperError(code, message)
        result = response.get("result")
        if not isinstance(result, dict):
            raise ComputerHelperError("invalid_response", "macOS helper result is not an object")
        return result
