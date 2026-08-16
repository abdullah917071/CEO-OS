"""Secret broker and credential vault for secure secret management and reference isolation."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from integrations.contracts import AuthenticationError, SecretLease, SecretReference

logger = logging.getLogger(__name__)


class SecretVault:
    """Internal secure storage for raw secret values.

    Never exposes raw secrets in string representations or logs.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[SecretReference, str]] = {}

    def store(
        self,
        name: str,
        secret_value: str,
        *,
        description: str = "",
        expires_at: datetime | None = None,
        tags: list[str] | None = None,
        credential_id: str | None = None,
    ) -> SecretReference:
        if not secret_value:
            raise ValueError("Secret value cannot be empty")
        cid = credential_id or f"cred_{uuid.uuid4().hex[:12]}"
        now = datetime.now(UTC)
        ref = SecretReference(
            credential_id=cid,
            name=name,
            description=description,
            created_at=now,
            expires_at=expires_at,
            tags=list(tags or []),
        )
        self._store[cid] = (ref, secret_value)
        return ref

    def get_reference(self, credential_id: str) -> SecretReference | None:
        entry = self._store.get(credential_id)
        if entry is None:
            return None
        return entry[0]

    def get_secret(self, credential_id: str) -> str | None:
        entry = self._store.get(credential_id)
        if entry is None:
            return None
        ref, value = entry
        if ref.expires_at is not None and datetime.now(UTC) > ref.expires_at:
            return None
        return value

    def delete(self, credential_id: str) -> bool:
        return self._store.pop(credential_id, None) is not None

    def list_references(self) -> list[SecretReference]:
        now = datetime.now(UTC)
        refs: list[SecretReference] = []
        for ref, _ in self._store.values():
            if ref.expires_at is None or ref.expires_at > now:
                refs.append(ref)
        return sorted(refs, key=lambda r: r.name)

    def all_raw_values(self) -> list[str]:
        """Return all active secret values strictly for redaction pattern compilation."""
        return [val for _, val in self._store.values() if len(val) >= 4]

    def __repr__(self) -> str:
        return f"<SecretVault entries={len(self._store)}>"


class SecretBroker:
    """Brokers secret access through opaque references and enforces log redaction.

    Ensures agents and LLMs interact with credential IDs rather than plain secrets.
    """

    def __init__(self, vault: SecretVault | None = None) -> None:
        self._vault = vault or SecretVault()
        self._leases: list[SecretLease] = []

    @property
    def vault(self) -> SecretVault:
        return self._vault

    def register_secret(
        self,
        name: str,
        secret_value: str,
        *,
        description: str = "",
        expires_at: datetime | None = None,
        tags: list[str] | None = None,
        credential_id: str | None = None,
    ) -> SecretReference:
        """Register a new secret and return its opaque reference."""
        ref = self._vault.store(
            name,
            secret_value,
            description=description,
            expires_at=expires_at,
            tags=tags,
            credential_id=credential_id,
        )
        logger.info("Registered secret credential reference %s for %s", ref.credential_id, name)
        return ref

    def get_reference(self, credential_id: str) -> SecretReference | None:
        """Look up reference metadata without exposing the secret value."""
        return self._vault.get_reference(credential_id)

    def list_references(self) -> list[SecretReference]:
        """List all active secret references."""
        return self._vault.list_references()

    def lease_secret(self, credential_id: str, requester: str) -> SecretLease:
        """Lease a secret value to an authorized requester component."""
        ref = self._vault.get_reference(credential_id)
        if ref is None:
            raise AuthenticationError(f"Credential not found: {credential_id}")
        val = self._vault.get_secret(credential_id)
        if val is None:
            raise AuthenticationError(f"Credential has expired or is invalid: {credential_id}")
        now = datetime.now(UTC)
        lease = SecretLease(
            credential_id=credential_id,
            secret_value=val,
            leased_at=now,
            lease_expires_at=ref.expires_at,
        )
        logger.debug("Leased credential %s to requester %s", credential_id, requester)
        return lease

    def revoke_secret(self, credential_id: str) -> bool:
        """Revoke a secret from the vault."""
        removed = self._vault.delete(credential_id)
        if removed:
            logger.info("Revoked credential %s", credential_id)
        return removed

    def mask_secrets(self, text: str) -> str:
        """Replace any raw secret values in *text* with redacted markers."""
        if not text:
            return text
        result = text
        for raw_val in self._vault.all_raw_values():
            if raw_val in result:
                result = result.replace(raw_val, "[REDACTED_SECRET]")
        return result

    def sanitize_payload(self, payload: Any) -> Any:
        """Recursively sanitize dicts, lists, and strings against raw secret values."""
        if isinstance(payload, str):
            return self.mask_secrets(payload)
        if isinstance(payload, dict):
            sanitized: dict[str, Any] = {}
            for k, v in payload.items():
                sec_keys = ("secret", "token", "password", "api_key")
                if any(sec_key in str(k).lower() for sec_key in sec_keys):
                    if isinstance(v, str) and not v.startswith("cred_"):
                        sanitized[k] = "[REDACTED_SECRET]"
                    else:
                        sanitized[k] = self.sanitize_payload(v)
                else:
                    sanitized[k] = self.sanitize_payload(v)
            return sanitized
        if isinstance(payload, list):
            return [self.sanitize_payload(item) for item in payload]
        return payload
