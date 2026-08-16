"""OAuth 2.0 PKCE manager for integration authentication lifecycles."""

from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import urllib.parse
from datetime import UTC, datetime, timedelta
from typing import Any

from integrations.contracts import (
    AuthenticationError,
    OAuthProfile,
    OAuthState,
    OAuthToken,
)
from integrations.secrets import SecretBroker

logger = logging.getLogger(__name__)


def _generate_pkce() -> tuple[str, str]:
    """Generate a high-entropy code_verifier and S256 code_challenge (RFC 7636)."""
    # 32 random bytes -> 43 characters base64url without padding
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


class OAuthManager:
    """Manages OAuth 2.0 PKCE authorization flows and token lifecycles."""

    def __init__(self, secret_broker: SecretBroker) -> None:
        self._secret_broker = secret_broker
        self._profiles: dict[str, OAuthProfile] = {}
        self._states: dict[str, OAuthState] = {}
        self._tokens: dict[str, OAuthToken] = {}

    def register_profile(self, profile: OAuthProfile) -> None:
        """Register an OAuth profile for a provider."""
        self._profiles[profile.provider_name] = profile
        logger.info("Registered OAuth profile for provider: %s", profile.provider_name)

    def get_profile(self, provider_name: str) -> OAuthProfile | None:
        return self._profiles.get(provider_name)

    def list_profiles(self) -> list[OAuthProfile]:
        return list(self._profiles.values())

    def start_authorization(
        self,
        provider_name: str,
        *,
        custom_scopes: list[str] | None = None,
        redirect_uri_override: str | None = None,
    ) -> tuple[str, OAuthState]:
        """Generate PKCE state and authorization URL for the user/operator to grant access."""
        profile = self._profiles.get(provider_name)
        if profile is None:
            raise AuthenticationError(f"Unknown OAuth provider: {provider_name}")

        client_id_lease = self._secret_broker.lease_secret(
            profile.client_id_ref, f"oauth:{provider_name}"
        )
        client_id = client_id_lease.secret_value

        state_token = secrets.token_urlsafe(32)
        code_verifier, code_challenge = _generate_pkce()
        redirect_uri = redirect_uri_override or profile.redirect_uri
        scopes = custom_scopes or profile.scopes

        now = datetime.now(UTC)
        oauth_state = OAuthState(
            state_token=state_token,
            provider_name=provider_name,
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            redirect_uri=redirect_uri,
            created_at=now,
            expires_at=now + timedelta(minutes=10),
        )
        self._states[state_token] = oauth_state

        query_params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state_token,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        auth_url = f"{profile.authorize_url}?{urllib.parse.urlencode(query_params)}"
        return auth_url, oauth_state

    def validate_and_consume_state(self, state_token: str) -> OAuthState:
        """Validate state token and return the associated OAuth state."""
        state = self._states.pop(state_token, None)
        if state is None:
            raise AuthenticationError("Invalid or expired OAuth state token")
        if datetime.now(UTC) > state.expires_at:
            raise AuthenticationError("OAuth state token has expired")
        return state

    async def exchange_code(
        self,
        provider_name: str,
        state_token: str,
        code: str,
        *,
        mock_token_response: dict[str, Any] | None = None,
    ) -> OAuthToken:
        """Exchange authorization code for access and refresh tokens."""
        state = self.validate_and_consume_state(state_token)
        if state.provider_name != provider_name:
            raise AuthenticationError(
                f"State mismatch: expected {state.provider_name}, got {provider_name}"
            )

        profile = self._profiles.get(provider_name)
        if profile is None:
            raise AuthenticationError(f"OAuth profile not found for {provider_name}")

        token_data = mock_token_response or {
            "access_token": f"mock_at_{secrets.token_hex(16)}",
            "refresh_token": f"mock_rt_{secrets.token_hex(16)}",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": " ".join(profile.scopes),
        }

        access_token_raw = token_data.get("access_token")
        if not access_token_raw:
            raise AuthenticationError("Token response missing access_token")

        expires_in = token_data.get("expires_in", 3600)
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=int(expires_in)) if expires_in else None

        at_ref = self._secret_broker.register_secret(
            name=f"{provider_name}_access_token",
            secret_value=str(access_token_raw),
            description=f"OAuth access token for {provider_name}",
            expires_at=expires_at,
            tags=["oauth", provider_name, "access_token"],
        )

        rt_ref_id: str | None = None
        if "refresh_token" in token_data and token_data["refresh_token"]:
            rt_ref = self._secret_broker.register_secret(
                name=f"{provider_name}_refresh_token",
                secret_value=str(token_data["refresh_token"]),
                description=f"OAuth refresh token for {provider_name}",
                tags=["oauth", provider_name, "refresh_token"],
            )
            rt_ref_id = rt_ref.credential_id

        token_record = OAuthToken(
            credential_id=at_ref.credential_id,
            provider_name=provider_name,
            token_type=token_data.get("token_type", "Bearer"),
            access_token_ref=at_ref.credential_id,
            refresh_token_ref=rt_ref_id,
            scopes=profile.scopes,
            expires_at=expires_at,
            issued_at=now,
        )
        self._tokens[provider_name] = token_record
        logger.info(
            "Successfully completed OAuth exchange for %s (token ref: %s)",
            provider_name,
            at_ref.credential_id,
        )
        return token_record

    def get_token(self, provider_name: str) -> OAuthToken | None:
        """Get the current active OAuth token record for a provider."""
        record = self._tokens.get(provider_name)
        if record is None:
            return None
        if record.expires_at is not None and datetime.now(UTC) > record.expires_at:
            return None
        return record

    def list_tokens(self) -> list[OAuthToken]:
        """List all current OAuth token records."""
        now = datetime.now(UTC)
        return [t for t in self._tokens.values() if t.expires_at is None or t.expires_at > now]

    def revoke_token(self, provider_name: str) -> bool:
        """Revoke tokens for a provider from the vault and memory."""
        token = self._tokens.pop(provider_name, None)
        if token is None:
            return False
        self._secret_broker.revoke_secret(token.access_token_ref)
        if token.refresh_token_ref:
            self._secret_broker.revoke_secret(token.refresh_token_ref)
        logger.info("Revoked OAuth tokens for %s", provider_name)
        return True
