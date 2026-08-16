"""Tests for Interactive Chat, ReAct Reasoner, and Voice Directives (YouTube, Spotify, etc.)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.src.ceo_os_api.main import app
from ceo_agent.agent import CeoAIAgent
from ceo_agent.llm import DeterministicCeoEngine


@pytest.mark.asyncio
async def test_interactive_chat_voice_youtube_command() -> None:
    """Verify that 'Jarvis open youtube' runs tool and responds with spoken confirmation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "message": "Jarvis, open YouTube",
            "voice_mode": True,
        }
        resp = await client.post("/api/v1/chat/interactive", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "SUCCESS"
        assert "thought" in data
        assert "final_answer" in data
        assert "YouTube" in data["final_answer"] or "sir" in data["final_answer"]
        assert len(data["tool_calls"]) > 0
        assert any(
            "youtube" in t["name"].lower() or "browser" in t["name"].lower()
            for t in data["tool_calls"]
        )


@pytest.mark.asyncio
async def test_interactive_chat_spotify_command() -> None:
    """Verify that 'open spotify' runs Spotify tool and confirms."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "message": "Jarvis, open Spotify and play music",
            "voice_mode": True,
        }
        resp = await client.post("/api/v1/chat/interactive", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "SUCCESS"
        assert len(data["tool_calls"]) > 0
        assert any(
            "spotify" in t["name"].lower() or "media" in t["name"].lower()
            for t in data["tool_calls"]
        )


@pytest.mark.asyncio
async def test_interactive_chat_system_stats_command() -> None:
    """Verify that 'check system stats' queries macOS metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "message": "Jarvis, check CPU and system stats",
            "voice_mode": False,
        }
        resp = await client.post("/api/v1/chat/interactive", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert data["status"] == "SUCCESS"
        assert len(data["tool_calls"]) > 0
        assert any(
            "stats" in t["name"].lower() or "macos" in t["name"].lower() for t in data["tool_calls"]
        )


@pytest.mark.asyncio
async def test_ceo_agent_standalone_reasoning_loop() -> None:
    """Verify CeoAIAgent ReAct multi-turn trajectory with tool extraction."""
    agent = CeoAIAgent(llm=DeterministicCeoEngine())
    res = await agent.run(task_id="test-101", objective="Jarvis, open YouTube")

    assert res.status == "SUCCESS"
    assert "YouTube" in res.final_answer or "sir" in res.final_answer
    assert res.trajectory is not None
    assert len(res.trajectory.steps) >= 1
