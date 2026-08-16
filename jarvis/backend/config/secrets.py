"""Secure credential storage and automatic secret redaction for Jarvis."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Patterns to automatically redact from logs and output
REDACT_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]+KEY-----.*?-----END [A-Z ]+KEY-----", re.DOTALL),
    re.compile(r'"private_key"\s*:\s*"[^"]+"'),
    re.compile(r'"private_key_id"\s*:\s*"[^"]+"'),
    re.compile(r"ya29\.[a-zA-Z0-9_\-]+"),  # Google OAuth access tokens
    re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]+"),
]


def redact_secrets(text: str) -> str:
    """Sanitize strings to prevent secret leakage in logs or exceptions."""
    sanitized = text
    for pattern in REDACT_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
    return sanitized


class JarvisSecretsManager:
    """Manages local storage of Google Cloud service account JSON with 0600 file permissions."""

    def __init__(self, secret_path: Path) -> None:
        self.secret_path = secret_path
        self._cached_service_account: dict[str, Any] | None = None

    def store_service_account_json(self, raw_json_or_dict: str | dict[str, Any]) -> dict[str, str]:
        """Validate, extract metadata, and write service account JSON with 0600 permissions."""
        if isinstance(raw_json_or_dict, str):
            try:
                data = json.loads(raw_json_or_dict)
            except Exception as exc:
                raise ValueError(f"Invalid JSON format: {exc}") from exc
        else:
            data = raw_json_or_dict

        # Validate mandatory service account fields
        required_fields = ["project_id", "client_email", "private_key", "token_uri"]
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            raise ValueError(f"Service account JSON missing required fields: {', '.join(missing)}")

        if not data["private_key"].startswith("-----BEGIN PRIVATE KEY-----"):
            raise ValueError("Invalid RSA private key structure in service account JSON")

        self.secret_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to disk and enforce 0600 permissions (owner read/write only)
        self.secret_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            os.chmod(self.secret_path, 0o600)
        except Exception as exc:
            logger.warning("Could not set 0600 file permissions on %s: %s", self.secret_path, exc)

        self._cached_service_account = data

        return {
            "status": "STORED",
            "project_id": data["project_id"],
            "client_email": data["client_email"],
            "token_uri": data.get("token_uri", "https://oauth2.googleapis.com/token"),
        }

    def load_service_account(self) -> dict[str, Any] | None:
        """Load stored service account JSON."""
        if self._cached_service_account:
            return self._cached_service_account

        if not self.secret_path.exists():
            # Check secondary fallback path in workspace
            fallback = Path("./data/secrets/jarvis_service_account.json")
            if fallback.exists():
                try:
                    raw_data = json.loads(fallback.read_text(encoding="utf-8"))
                    if isinstance(raw_data, dict):
                        self._cached_service_account = raw_data
                        return raw_data
                except Exception as exc:
                    logger.warning("Failed reading fallback service account: %s", exc)
            return None

        try:
            raw_data = json.loads(self.secret_path.read_text(encoding="utf-8"))
            if isinstance(raw_data, dict):
                self._cached_service_account = raw_data
                return raw_data
            return None
        except Exception as exc:
            logger.error("Failed to load service account: %s", redact_secrets(str(exc)))
            return None

    def delete_service_account(self) -> bool:
        """Securely remove stored credentials."""
        self._cached_service_account = None
        if self.secret_path.exists():
            try:
                self.secret_path.unlink()
                return True
            except Exception as exc:
                logger.error("Failed deleting service account file: %s", exc)
                return False
        return False

    def get_public_metadata(self) -> dict[str, Any]:
        """Return safe, non-sensitive credential status without exposing private keys."""
        sa = self.load_service_account()
        if not sa:
            return {
                "configured": False,
                "project_id": None,
                "client_email": None,
                "has_private_key": False,
            }
        return {
            "configured": True,
            "project_id": sa.get("project_id"),
            "client_email": sa.get("client_email"),
            "has_private_key": bool(sa.get("private_key")),
        }
