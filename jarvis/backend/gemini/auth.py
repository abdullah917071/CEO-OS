"""Google Cloud Service Account authentication and OAuth access token manager for Gemini Live."""

from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from jarvis.backend.config.secrets import JarvisSecretsManager, redact_secrets

logger = logging.getLogger(__name__)


def _b64url_encode(data: bytes) -> str:
    """Base64url encode without padding."""
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


@dataclass(slots=True)
class GoogleToken:
    access_token: str
    expires_at: float  # Epoch timestamp in seconds


class GeminiAuthManager:
    """Manages Google Cloud service-account credential validation and OAuth token refresh."""

    def __init__(self, secrets_manager: JarvisSecretsManager) -> None:
        self.secrets_manager = secrets_manager
        self._cached_token: GoogleToken | None = None

    def validate_service_account(self, data: dict[str, Any]) -> dict[str, Any]:
        """Validate structure and extract safe metadata."""
        required = ["project_id", "client_email", "private_key", "token_uri"]
        missing = [k for k in required if not data.get(k)]
        if missing:
            raise ValueError(f"Service account missing required fields: {', '.join(missing)}")

        if not str(data["private_key"]).startswith("-----BEGIN PRIVATE KEY-----"):
            raise ValueError("Invalid RSA private key format in service account")

        return {
            "valid": True,
            "project_id": data["project_id"],
            "client_email": data["client_email"],
            "token_uri": data.get("token_uri", "https://oauth2.googleapis.com/token"),
        }

    def _create_signed_jwt(self, sa: dict[str, Any], scope: str) -> str:
        """Sign a JWT assertion with the service account's RSA private key."""
        now = int(time.time())
        header = {"alg": "RS256", "typ": "JWT"}
        payload = {
            "iss": sa["client_email"],
            "scope": scope,
            "aud": sa.get("token_uri", "https://oauth2.googleapis.com/token"),
            "exp": now + 3600,
            "iat": now,
        }

        header_b64 = _b64url_encode(json.dumps(header).encode("utf-8"))
        payload_b64 = _b64url_encode(json.dumps(payload).encode("utf-8"))
        signing_input = f"{header_b64}.{payload_b64}".encode()

        # Load RSA private key
        key_bytes = sa["private_key"].encode("utf-8")
        private_key = load_pem_private_key(key_bytes, password=None)

        signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        sig_b64 = _b64url_encode(signature)

        return f"{header_b64}.{payload_b64}.{sig_b64}"

    async def obtain_access_token(
        self,
        scope: str = "https://www.googleapis.com/auth/cloud-platform",
        force_refresh: bool = False,
    ) -> str:
        """Obtain or refresh Google OAuth2 access token."""
        now = time.time()
        # Return cached token if valid for at least 5 more minutes
        if self._cached_token and not force_refresh:
            if self._cached_token.expires_at > now + 300:
                return self._cached_token.access_token

        sa = self.secrets_manager.load_service_account()
        if not sa:
            raise ValueError(
                "No Google Cloud service account configured. "
                "Please upload service_account.json in settings."
            )

        signed_jwt = self._create_signed_jwt(sa, scope)
        token_uri = sa.get("token_uri", "https://oauth2.googleapis.com/token")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                token_uri,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion": signed_jwt,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code != 200:
                err_msg = f"Failed obtaining OAuth token ({resp.status_code}): {resp.text}"
                logger.error("%s", redact_secrets(err_msg))
                raise RuntimeError(redact_secrets(err_msg))

            data = resp.json()
            access_token = data["access_token"]
            expires_in = int(data.get("expires_in", 3600))

            self._cached_token = GoogleToken(
                access_token=access_token,
                expires_at=now + expires_in,
            )
            return access_token

    async def test_vertex_connection(
        self,
        project_id: str | None = None,
        location: str = "us-central1",
    ) -> dict[str, Any]:
        """Test authentication and verify Vertex AI endpoint accessibility."""
        sa = self.secrets_manager.load_service_account()
        if not sa:
            return {
                "success": False,
                "error": "No service account JSON configured",
                "checks": {
                    "service_account": False,
                    "project": False,
                    "vertex_ai": False,
                },
            }

        target_project = project_id or sa.get("project_id", "")
        try:
            token = await self.obtain_access_token(force_refresh=True)
            # Test Vertex AI endpoint
            base = f"https://{location}-aiplatform.googleapis.com/v1"
            url = f"{base}/projects/{target_project}/locations/{location}/publishers/google/models"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    url,
                    headers={"Authorization": f"Bearer {token}"},
                )
                status_ok = resp.status_code in (200, 404, 403)  # Verified network reachability
                is_authed = resp.status_code == 200

                msg = (
                    "Vertex AI connected successfully!"
                    if is_authed
                    else f"Auth OK, but HTTP {resp.status_code} for {target_project}."
                )

                return {
                    "success": is_authed,
                    "status_code": resp.status_code,
                    "project_id": target_project,
                    "location": location,
                    "checks": {
                        "service_account_valid": True,
                        "token_exchange_success": True,
                        "vertex_endpoint_reachable": status_ok,
                        "project_accessible": is_authed,
                    },
                    "message": msg,
                }
        except Exception as exc:
            err = redact_secrets(str(exc))
            return {
                "success": False,
                "error": err,
                "checks": {
                    "service_account_valid": True,
                    "token_exchange_success": False,
                    "vertex_endpoint_reachable": False,
                },
            }
