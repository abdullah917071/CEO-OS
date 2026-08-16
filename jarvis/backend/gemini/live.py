"""Gemini Live Bidirectional WebSocket client for Vertex AI."""

from __future__ import annotations

import base64
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import websockets

from jarvis.backend.config.secrets import redact_secrets
from jarvis.backend.config.settings import GeminiConfig
from jarvis.backend.gemini.auth import GeminiAuthManager

logger = logging.getLogger(__name__)


class GeminiLiveSocket:
    """Manages low-level WebSocket connection to Vertex AI / Gemini Live service."""

    def __init__(
        self,
        auth_manager: GeminiAuthManager,
        config: GeminiConfig,
    ) -> None:
        self.auth_manager = auth_manager
        self.config = config
        self._ws: Any = None
        self._is_connected: bool = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected and self._ws is not None

    async def connect(self, tool_declarations: list[dict[str, Any]] | None = None) -> None:
        """Establish authenticated WebSocket connection and send setup handshake."""
        token = await self.auth_manager.obtain_access_token()
        sa = self.auth_manager.secrets_manager.load_service_account()
        project = self.config.project_id or (sa.get("project_id") if sa else "")
        location = self.config.location

        if token.startswith("api_key:"):
            # Google AI Studio Gemini Live WebSocket URL
            api_key = token.split("api_key:", 1)[1]
            ws_url = (
                f"wss://generativelanguage.googleapis.com/ws/"
                f"google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={api_key}"
            )
            headers = {"Content-Type": "application/json"}
            model_resource = f"models/{self.config.model_name}"
        else:
            # Vertex AI BidiGenerateContent WebSocket URL
            ws_url = (
                f"wss://{location}-aiplatform.googleapis.com/ws/"
                f"google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent"
            )
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            model_resource = (
                f"projects/{project}/locations/{location}/publishers/google/models/"
                f"{self.config.model_name}"
            )

        try:
            self._ws = await websockets.connect(
                ws_url,
                additional_headers=headers,
                max_size=10 * 1024 * 1024,  # 10MB message size limit
                ping_interval=20,
                ping_timeout=20,
            )
            self._is_connected = True

            # Send Setup Handshake
            setup_dict: dict[str, Any] = {
                "model": model_resource,
                "generationConfig": {
                    "temperature": self.config.temperature,
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": self.config.voice_name,
                            }
                        }
                    },
                },
                "systemInstruction": {"parts": [{"text": self.config.system_instruction}]},
            }

            if tool_declarations:
                setup_dict["tools"] = [{"functionDeclarations": tool_declarations}]

            setup_payload: dict[str, Any] = {"setup": setup_dict}
            await self._ws.send(json.dumps(setup_payload))
            logger.info("Sent Gemini Live setup handshake for model %s", self.config.model_name)

        except Exception as exc:
            self._is_connected = False
            self._ws = None
            err = redact_secrets(str(exc))
            logger.error("Failed connecting Gemini Live WebSocket: %s", err)
            raise ConnectionError(f"Gemini Live connection failed: {err}") from exc

    async def send_audio_chunk(self, pcm16_bytes: bytes, sample_rate: int = 16000) -> None:
        """Stream PCM16 microphone chunk to Gemini Live."""
        if not self._ws or not self._is_connected:
            return

        b64_data = base64.b64encode(pcm16_bytes).decode("utf-8")
        payload = {
            "realtimeInput": {
                "mediaChunks": [
                    {
                        "mimeType": f"audio/pcm;rate={sample_rate}",
                        "data": b64_data,
                    }
                ]
            }
        }
        try:
            await self._ws.send(json.dumps(payload))
        except Exception as exc:
            logger.warning("Error sending audio chunk to Gemini: %s", exc)

    async def send_tool_response(
        self, function_name: str, response: dict[str, Any], call_id: str | None = None
    ) -> None:
        """Send function execution result back to Gemini Live."""
        if not self._ws or not self._is_connected:
            return

        fn_resp: dict[str, Any] = {
            "name": function_name,
            "response": response,
        }
        if call_id:
            fn_resp["id"] = call_id

        payload = {"toolResponse": {"functionResponses": [fn_resp]}}
        try:
            await self._ws.send(json.dumps(payload))
            logger.info("Sent tool response to Gemini: %s", function_name)
        except Exception as exc:
            logger.error("Failed sending tool response: %s", exc)

    async def receive_messages(self) -> AsyncIterator[dict[str, Any]]:
        """Yield parsed JSON messages received from Gemini Live."""
        if not self._ws:
            return

        try:
            async for raw in self._ws:
                if isinstance(raw, bytes):
                    raw_text = raw.decode("utf-8")
                else:
                    raw_text = raw

                try:
                    data = json.loads(raw_text)
                    yield data
                except Exception as exc:
                    logger.warning("Failed parsing message from Gemini Live: %s", exc)
        except websockets.ConnectionClosed:
            logger.info("Gemini Live WebSocket connection closed normally")
        except Exception as exc:
            logger.error("Gemini Live receive loop error: %s", exc)
        finally:
            self._is_connected = False

    async def close(self) -> None:
        """Cleanly terminate WebSocket connection."""
        self._is_connected = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
            logger.info("Closed Gemini Live WebSocket connection")
