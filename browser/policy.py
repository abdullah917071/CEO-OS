from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

SESSION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
ALLOWED_LOCATOR_KINDS = {"role", "label", "placeholder", "text", "test_id", "css"}


class BrowserPolicyError(PermissionError):
    pass


def normalized_origin(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        raise BrowserPolicyError("Only HTTP and HTTPS browser URLs are allowed")
    if parsed.username is not None or parsed.password is not None:
        raise BrowserPolicyError("Credentials are not allowed in browser URLs")
    if parsed.fragment:
        raise BrowserPolicyError("URL fragments are not accepted by browser navigation")
    if not parsed.hostname:
        raise BrowserPolicyError("Browser URL must contain a hostname")
    try:
        port = parsed.port
    except ValueError as exc:
        raise BrowserPolicyError("Browser URL contains an invalid port") from exc
    default_port = 80 if parsed.scheme == "http" else 443
    port_suffix = f":{port}" if port is not None and port != default_port else ""
    return f"{parsed.scheme}://{parsed.hostname.lower()}{port_suffix}"


@dataclass(frozen=True, slots=True)
class BrowserPolicy:
    allowed_origins: frozenset[str]
    upload_root: Path
    download_root: Path
    effects_enabled: bool = False
    persistent_profiles_enabled: bool = False

    def validate_session_name(self, value: str) -> str:
        if not SESSION_PATTERN.fullmatch(value):
            raise BrowserPolicyError("Session name must match [a-z0-9][a-z0-9_-]{0,63}")
        return value

    def authorize_url(self, url: str) -> str:
        origin = normalized_origin(url)
        if origin not in self.allowed_origins:
            raise BrowserPolicyError(f"Browser origin is not allowlisted: {origin}")
        return url

    def authorize_request_url(self, url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme in {"data", "blob"}:
            return
        self.authorize_url(url)

    def authorize_effect(self) -> None:
        if not self.effects_enabled:
            raise BrowserPolicyError("Browser effects are disabled")

    def authorize_persistence(self, requested: bool) -> None:
        if requested and not self.persistent_profiles_enabled:
            raise BrowserPolicyError("Persistent browser profiles are disabled")

    def resolve_upload(self, raw_path: str) -> Path:
        return self._resolve_existing(self.upload_root, raw_path, "Upload")

    def resolve_download(self, filename: str) -> Path:
        if not filename or Path(filename).name != filename or filename in {".", ".."}:
            raise BrowserPolicyError("Download filename is invalid")
        root = self.download_root.resolve()
        root.mkdir(parents=True, exist_ok=True)
        candidate = (root / filename).resolve()
        if candidate.parent != root:
            raise BrowserPolicyError("Download path escapes the configured root")
        return candidate

    @staticmethod
    def _resolve_existing(root_value: Path, raw_path: str, label: str) -> Path:
        root = root_value.resolve()
        candidate = (root / raw_path).resolve()
        if candidate != root and root not in candidate.parents:
            raise BrowserPolicyError(f"{label} path escapes the configured root")
        if not candidate.is_file():
            raise BrowserPolicyError(f"{label} file does not exist")
        return candidate


def parse_allowed_origins(raw_origins: str) -> frozenset[str]:
    origins: set[str] = set()
    for raw in raw_origins.split(","):
        value = raw.strip()
        if value:
            origins.add(normalized_origin(value))
    return frozenset(origins)
