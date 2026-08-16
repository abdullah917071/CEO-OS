"""Safe, canonical JSON serialization utility for tool outputs and trajectory logging."""

from __future__ import annotations

import base64
import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID


def safe_json_serialize(obj: Any) -> Any:
    """Recursively convert any Python object into JSON-serializable primitives."""
    if obj is None or isinstance(obj, (int, float, str, bool)):
        return obj

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    if isinstance(obj, UUID):
        return str(obj)

    if isinstance(obj, Path):
        return str(obj)

    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            return (
                f"<binary: {len(obj)} bytes, b64={base64.b64encode(obj[:64]).decode('ascii')}...>"
            )

    if isinstance(obj, Enum):
        return obj.value

    if is_dataclass(obj) and not isinstance(obj, type):
        return safe_json_serialize(asdict(obj))

    # Pydantic v2 support
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        return safe_json_serialize(obj.model_dump())

    # Pydantic v1 support
    if hasattr(obj, "dict") and callable(obj.dict):
        return safe_json_serialize(obj.dict())

    if isinstance(obj, dict):
        return {str(k): safe_json_serialize(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set, frozenset)):
        return [safe_json_serialize(item) for item in obj]

    if isinstance(obj, BaseException):
        return f"{type(obj).__name__}: {str(obj)}"

    # Fallback to string representation
    return str(obj)


def safe_json_dumps(obj: Any, **kwargs: Any) -> str:
    """Serialize any object to a JSON string without risk of TypeError crashes."""
    sanitized = safe_json_serialize(obj)
    return json.dumps(sanitized, **kwargs)
