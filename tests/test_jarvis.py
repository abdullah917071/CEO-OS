"""Comprehensive test suite for Jarvis macOS Voice Assistant powered by Gemini Live."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.src.ceo_os_api.main import app
from jarvis.backend.agent.manager import JarvisAgentManager
from jarvis.backend.agent.state import JarvisState
from jarvis.backend.audio.playback import AudioPlaybackManager
from jarvis.backend.audio.processing import AudioProcessor
from jarvis.backend.config.database import JarvisDatabase
from jarvis.backend.config.secrets import JarvisSecretsManager, redact_secrets
from jarvis.backend.config.settings import GeminiConfig, JarvisSettings, WakeWordConfig
from jarvis.backend.gemini.auth import GeminiAuthManager
from jarvis.backend.tools.permissions import PermissionLevel, ToolPermissionManager
from jarvis.backend.tools.registry import JarvisToolRegistry

# Short mock RSA private key structure for testing
MOCK_KEY = (
    "-----BEGIN PRIVATE KEY-----\n"
    "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC4gUIbM0FdCpn2\n"
    "Wr/EhHeLO23LLLsABIIvhbk2QnyGKH3gKAn83lceM0m6GqaDKd/VdV5wGWR6aW4K\n"
    "RtT+2bIQ4soYHVFMPOo5+xtEBogZwXjVIBTO3Pc3D0CfmI6KZGjHZ1eUCoC/WzUb\n"
    "AxCFUrJEsLjpEZ2pJEwR1m0H0voQM2jFAwBjRLrCVni7EIzWwWWdrx/kjy14huwC\n"
    "R/JHXNsuic5EQyn95h2kWFiOQSS8C64a/HEpd7KlCNaa3r3HMztUu99lP7z/9OKj\n"
    "KQtQN6JdAw0e7v16t79BMwMbgJsXkP83VsM4trjm7uWqIxszPJN/2VACBr4YLoB7\n"
    "0OWAT+KpAgMBAAECggEAAR0KlJZxGQok1rdCfAGepRD1PyokcMIWNQo2DW1GShr5\n"
    "c35aXRPMa8q8caqSga0hhCzCpqOIlzKGrvoxc95FdFOiC5Y1tOOTOElbJ0Rw0tL3\n"
    "kzWv2nW76jGl3rCxf4VOmpF1llef4ke/IMwab+uJVt/IJePs0yX8bYkhPFBaIPnj\n"
    "0aUpwNymeTJ1W/1B1Vxq2ZGTdWSRiVEhu8Mwd287BN2LPR3thnnpUtY5DUDGg6y9\n"
    "tqLGytrVgXS7FbMIQ4yd4uOUrFepGg+hrhG+muwW4wzQqNGu1/07oklTBlct6BHV\n"
    "YZ4GTnwZk0c1B5ienUkhjUwFecIPgVLIZfKsR1/MQQKBgQDnTSL2OUA1dugkzi37\n"
    "RnfTWF3/rNMVVfwnGQB4+RMJQfCZLJJakr1/rc5w9fwMKwzwQXKIe1I2jSu4VyVb\n"
    "LSMvG7kn3oSWYTod7h9fP8vNCv7tabVbmT3aalTKtio2uWHRWXZvUPazrwoXUnW6\n"
    "e3dF2ZP4sPfXMVe5PhhVIHC7UQKBgQDMNOSi6A6o/nLSgLarDgV4Y3amjILbCnvZ\n"
    "Xny59DBIUJAT+iGrO5/YtHxiRTS9p87qRKudL9g5jyJZ3BVSsMt6QcUvUruCttoB\n"
    "a/GcGQiZW0VdHORozvqfkU/ww7Vh8PZABb6353yqB8/kzQ/ztlE4qNABsc2uBBqZ\n"
    "dVdTLQKr2QKBgQCe4Sxnx3Gkh/Xz+jA5jvEWGngO/M7NtA+NZ64carK5xDKZdLVf\n"
    "Q7apMmFA1Kb6UMQFcF9VAqi5UgU7DZlaZMnrPPbVPRMEHOsHzh58ldzPDoOH3vm1\n"
    "XrDPDAUMbU7X4kUfwX0J/6pGSLD8ziaSHucR8t+ijyTfC0S/uLiMGMl20QKBgCIe\n"
    "fE0TxM9LpFezldHCx/szczGkrIB4ofTRqrlPKXoLq+cKlfGMRsrobRfmREej8BiI\n"
    "XLwosFH9rlmhQhbM31KQBqg/hID0mDxAkt/n9t3YuCA0oZ05Z/qdRuQNbxLsNdjA\n"
    "nPsRPG0UXRH3iUDJJ4z197swwBLhMKiPSIXnMVkRAoGAOpc4nl0TwHcaPcZ/n6tq\n"
    "m4n5hXpgRihQsAK/lhQOTFOhq0C56a0kswcdgpzd3Ca1Bl9u0MC2shh/MLlgA7mV\n"
    "3wfRMuK7/D4w89kiOm9E6FB705ntMN1KQ10oGUPcxg/2yI0Q4uXDYIFId8u3l23Z\n"
    "2pedBMJ93ZkAoLc3L1qC9TM=\n"
    "-----END PRIVATE KEY-----\n"
)

SAMPLE_SA = {
    "type": "service_account",
    "project_id": "test-project-123",
    "private_key_id": "test-key-id",
    "private_key": MOCK_KEY,
    "client_email": "test-sa@test-project-123.iam.gserviceaccount.com",
    "client_id": "123456789",
    "token_uri": "https://oauth2.googleapis.com/token",
}


@pytest.fixture
def temp_jarvis_env(tmp_path: Path):
    db_path = tmp_path / "jarvis_test.sqlite3"
    sa_path = tmp_path / "service_account.json"
    settings = JarvisSettings(
        app_data_dir=tmp_path,
        database_path=db_path,
        service_account_path=sa_path,
        gemini=GeminiConfig(project_id="test-project-123", inactivity_timeout_seconds=2),
        wakeword=WakeWordConfig(wake_word="Jarvis", model_name="jarvis.onnx"),
    )
    secrets_mgr = JarvisSecretsManager(sa_path)
    secrets_mgr.store_service_account_json(SAMPLE_SA)
    return {"settings": settings, "secrets": secrets_mgr, "db_path": db_path, "sa_path": sa_path}


def test_secrets_manager_and_redaction(temp_jarvis_env):
    secrets = temp_jarvis_env["secrets"]
    sa = secrets.load_service_account()
    assert sa is not None
    assert sa["project_id"] == "test-project-123"
    assert sa["client_email"] == "test-sa@test-project-123.iam.gserviceaccount.com"

    # Verify public metadata does not reveal private key
    meta = secrets.get_public_metadata()
    assert meta["configured"] is True
    assert meta["project_id"] == "test-project-123"
    assert "private_key" not in meta

    # Test redaction
    log_text = f"Connecting with private_key: {sa['private_key']} and Bearer ya29.testtoken123"
    redacted = redact_secrets(log_text)
    assert "[REDACTED_SECRET]" in redacted
    assert "BEGIN PRIVATE KEY" not in redacted
    assert "ya29.testtoken123" not in redacted


def test_auth_manager_jwt_signing(temp_jarvis_env):
    auth_mgr = GeminiAuthManager(temp_jarvis_env["secrets"])
    sa = temp_jarvis_env["secrets"].load_service_account()
    jwt_token = auth_mgr._create_signed_jwt(sa, "https://www.googleapis.com/auth/cloud-platform")

    parts = jwt_token.split(".")
    assert len(parts) == 3  # Header, Payload, Signature


def test_audio_processing_and_barge_in():
    proc = AudioProcessor()
    # Test silence
    silence = b"\x00" * 3200
    rms_silence = proc.calculate_rms(silence)
    assert rms_silence == 0
    assert not proc.is_speech(silence)

    # Test playback manager barge-in
    playback = AudioPlaybackManager()
    playback.enqueue_chunk(b"\x01\x02" * 100, generation_id=0)
    playback.enqueue_chunk(b"\x01\x02" * 100, generation_id=0)

    # Trigger interruption
    new_gen = playback.interrupt_and_flush()
    assert new_gen == 1
    assert playback._queue.empty()


@pytest.mark.asyncio
async def test_tool_registry_and_permissions(temp_jarvis_env):
    db = JarvisDatabase(temp_jarvis_env["db_path"])
    perms = ToolPermissionManager(db)
    registry = JarvisToolRegistry(perms)

    # Verify declarations format
    declarations = registry.get_gemini_declarations()
    assert len(declarations) >= 10
    tool_names = [d["name"] for d in declarations]
    assert "open_application" in tool_names
    assert "get_system_stats" in tool_names

    # Test system stats execution
    stats = await registry.execute_tool("get_system_stats", {})
    assert stats["status"] == "SUCCESS"
    assert "system" in stats

    # Test permission DENY
    perms.set_permission("get_system_stats", PermissionLevel.DENY)
    denied = await registry.execute_tool("get_system_stats", {})
    assert denied["status"] == "DENIED"


@pytest.mark.asyncio
async def test_jarvis_agent_manager_lifecycle(temp_jarvis_env):
    mgr = JarvisAgentManager(settings=temp_jarvis_env["settings"])

    # 1. Start agent in IDLE_WAKE_WORD state
    mgr.start()
    assert mgr.state == JarvisState.IDLE_WAKE_WORD
    # Cost guardrail invariant: no active Gemini session when idle
    assert mgr.active_session is None

    # 2. Trigger test wake word detection
    mgr.wakeword_manager.detector.trigger_test_detection()
    res = mgr.wakeword_manager.process_audio_frame(b"\x00" * 3200, is_speech=True)
    assert res is not None
    assert res.detected is True

    # 3. Simulate manual session activation
    with patch("jarvis.backend.gemini.live.GeminiLiveSocket.connect", new_callable=AsyncMock):
        await mgr.activate_session(trigger_source="test")
        assert mgr.state == JarvisState.ACTIVE
        assert mgr.active_session is not None

        # 4. End session and return to IDLE_WAKE_WORD
        await mgr.end_session(reason="test_complete")
        assert mgr.state == JarvisState.IDLE_WAKE_WORD
        assert mgr.active_session is None

    mgr.stop()
    assert mgr.state == JarvisState.STARTING


@pytest.mark.asyncio
async def test_jarvis_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Status
        resp = await client.get("/api/jarvis/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "state" in data
        assert "wake_word" in data

        # Wake word test
        resp = await client.post("/api/jarvis/wakeword/test")
        assert resp.status_code == 200
        w_data = resp.json()
        assert w_data["detected"] is True

        # Tools list
        resp = await client.get("/api/jarvis/tools")
        assert resp.status_code == 200
        t_data = resp.json()
        assert len(t_data["tools"]) > 0

        # Tool execution test
        resp = await client.post(
            "/api/jarvis/tools/test",
            json={"name": "get_system_stats", "arguments": {}},
        )
        assert resp.status_code == 200
        res_data = resp.json()
        assert res_data["result"]["status"] == "SUCCESS"

        # Usage
        resp = await client.get("/api/jarvis/usage")
        assert resp.status_code == 200

        # Logs
        resp = await client.get("/api/jarvis/logs")
        assert resp.status_code == 200
