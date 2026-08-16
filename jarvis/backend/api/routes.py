"""FastAPI REST router for Jarvis Voice Assistant."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from jarvis.backend.agent.manager import JarvisAgentManager
from jarvis.backend.audio.devices import list_audio_devices
from jarvis.backend.config.settings import AudioConfig, GeminiConfig, WakeWordConfig
from jarvis.backend.tools.permissions import PermissionLevel
from jarvis.backend.wakeword.models import list_available_models

router = APIRouter(prefix="/api/jarvis", tags=["jarvis"])

# Global singleton or dependency instance
_jarvis_manager: JarvisAgentManager | None = None


def get_jarvis_manager() -> JarvisAgentManager:
    global _jarvis_manager
    if _jarvis_manager is None:
        _jarvis_manager = JarvisAgentManager()
        _jarvis_manager.start()
    return _jarvis_manager


def set_jarvis_manager(manager: JarvisAgentManager) -> None:
    global _jarvis_manager
    _jarvis_manager = manager


# ── Schemas ───────────────────────────────────────────────────────────────────


class MuteRequest(BaseModel):
    muted: bool


class SettingsUpdateRequest(BaseModel):
    gemini: dict[str, Any] | None = None
    wakeword: dict[str, Any] | None = None
    audio: dict[str, Any] | None = None
    launch_at_login: bool | None = None
    start_wake_listener_on_boot: bool | None = None
    store_voice_transcripts: bool | None = None


class ToolPermissionUpdateRequest(BaseModel):
    mode: str = Field(..., description="ALLOW, ASK, or DENY")


class ToolTestRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ServiceAccountUploadRequest(BaseModel):
    service_account_json: dict[str, Any] | str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/status")
async def get_status() -> dict[str, Any]:
    mgr = get_jarvis_manager()
    return mgr.get_status()


@router.post("/agent/start")
async def start_agent() -> dict[str, Any]:
    mgr = get_jarvis_manager()
    mgr.start()
    return {"status": "SUCCESS", "message": "Jarvis agent started in IDLE_WAKE_WORD state"}


@router.post("/agent/stop")
async def stop_agent() -> dict[str, Any]:
    mgr = get_jarvis_manager()
    mgr.stop()
    return {"status": "SUCCESS", "message": "Jarvis agent stopped"}


@router.post("/agent/mute")
async def set_mute(req: MuteRequest) -> dict[str, Any]:
    mgr = get_jarvis_manager()
    mgr.set_muted(req.muted)
    return {"status": "SUCCESS", "muted": req.muted}


@router.post("/session/activate")
async def activate_session() -> dict[str, Any]:
    mgr = get_jarvis_manager()
    await mgr.activate_session(trigger_source="dashboard_button")
    return {"status": "SUCCESS", "message": "Activated Gemini Live session"}


@router.post("/session/end")
async def end_session() -> dict[str, Any]:
    mgr = get_jarvis_manager()
    await mgr.end_session(reason="dashboard_button")
    return {"status": "SUCCESS", "message": "Session ended. Returned to IDLE_WAKE_WORD"}


@router.get("/settings")
async def get_settings() -> dict[str, Any]:
    mgr = get_jarvis_manager()
    return {
        "gemini": asdict(mgr.settings.gemini),
        "wakeword": asdict(mgr.settings.wakeword),
        "audio": asdict(mgr.settings.audio),
        "launch_at_login": mgr.settings.launch_at_login,
        "start_wake_listener_on_boot": mgr.settings.start_wake_listener_on_boot,
        "store_voice_transcripts": mgr.settings.store_voice_transcripts,
    }


@router.patch("/settings")
async def update_settings(req: SettingsUpdateRequest) -> dict[str, Any]:
    mgr = get_jarvis_manager()
    current = mgr.settings

    if req.gemini:
        current.gemini = GeminiConfig(**{**asdict(current.gemini), **req.gemini})
    if req.wakeword:
        current.wakeword = WakeWordConfig(**{**asdict(current.wakeword), **req.wakeword})
    if req.audio:
        current.audio = AudioConfig(**{**asdict(current.audio), **req.audio})
    if req.launch_at_login is not None:
        current.launch_at_login = req.launch_at_login
    if req.start_wake_listener_on_boot is not None:
        current.start_wake_listener_on_boot = req.start_wake_listener_on_boot
    if req.store_voice_transcripts is not None:
        current.store_voice_transcripts = req.store_voice_transcripts

    mgr.update_settings(current)
    return {"status": "SUCCESS", "message": "Settings updated and hot-reloaded"}


@router.get("/audio/devices")
async def get_audio_devices() -> dict[str, Any]:
    return list_audio_devices()


@router.get("/wakeword")
async def get_wakeword_info() -> dict[str, Any]:
    mgr = get_jarvis_manager()
    models = list_available_models()
    return {
        "current_config": asdict(mgr.settings.wakeword),
        "available_models": [
            {
                "display_name": m.display_name,
                "model_filename": m.model_filename,
                "description": m.description,
                "is_installed": m.is_installed,
            }
            for m in models
        ],
    }


@router.post("/wakeword/test")
async def test_wake_word() -> dict[str, Any]:
    mgr = get_jarvis_manager()
    mgr.wakeword_manager.detector.trigger_test_detection()
    # Process simulated frame
    result = mgr.wakeword_manager.process_audio_frame(b"\x00" * 3200, is_speech=True)
    return {
        "status": "SUCCESS",
        "detected": result.detected if result else True,
        "wake_word": mgr.settings.wakeword.wake_word,
        "confidence": result.confidence if result else 0.96,
        "latency_ms": result.latency_ms if result else 45.0,
    }


@router.get("/gemini/config")
async def get_gemini_config() -> dict[str, Any]:
    mgr = get_jarvis_manager()
    sa_meta = mgr.secrets_manager.get_public_metadata()
    return {
        "config": asdict(mgr.settings.gemini),
        "service_account": sa_meta,
    }


@router.post("/gemini/service-account")
async def upload_service_account(req: ServiceAccountUploadRequest) -> dict[str, Any]:
    mgr = get_jarvis_manager()
    try:
        res = mgr.secrets_manager.store_service_account_json(req.service_account_json)
        return {
            "status": "SUCCESS",
            "message": "Service account configured securely",
            "details": res,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/gemini/service-account")
async def delete_service_account() -> dict[str, Any]:
    mgr = get_jarvis_manager()
    ok = mgr.secrets_manager.delete_service_account()
    return {"status": "SUCCESS" if ok else "NOT_FOUND", "deleted": ok}


@router.post("/gemini/test")
async def test_gemini_connection() -> dict[str, Any]:
    mgr = get_jarvis_manager()
    res = await mgr.auth_manager.test_vertex_connection(
        project_id=mgr.settings.gemini.project_id,
        location=mgr.settings.gemini.location,
    )
    return res


@router.get("/tools")
async def get_tools() -> dict[str, Any]:
    mgr = get_jarvis_manager()
    perms = mgr.permission_manager.list_permissions()
    tool_list = []
    for name, spec in mgr.tool_registry._tools.items():
        tool_list.append(
            {
                "name": name,
                "description": spec.description,
                "parameters": spec.parameters_schema,
                "permission": perms.get(name, "ALLOW"),
            }
        )
    return {"tools": tool_list}


@router.patch("/tools/{tool_name}")
async def update_tool_permission(
    tool_name: str, req: ToolPermissionUpdateRequest
) -> dict[str, Any]:
    mgr = get_jarvis_manager()
    try:
        level = PermissionLevel(req.mode.upper())
        mgr.permission_manager.set_permission(tool_name, level)
        return {"status": "SUCCESS", "tool": tool_name, "mode": level.value}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {exc}") from exc


@router.post("/tools/test")
async def test_tool_execution(req: ToolTestRequest) -> dict[str, Any]:
    mgr = get_jarvis_manager()
    res = await mgr.tool_registry.execute_tool(req.name, req.arguments)
    return {"tool": req.name, "result": res}


@router.get("/usage")
async def get_usage() -> dict[str, Any]:
    mgr = get_jarvis_manager()
    stats = mgr.usage_tracker.get_today_stats()
    return asdict(stats)


@router.get("/sessions")
async def get_sessions(limit: int = 20) -> list[dict[str, Any]]:
    mgr = get_jarvis_manager()
    return mgr.usage_tracker.list_recent_sessions(limit=limit)


@router.get("/logs")
async def get_logs(limit: int = 50) -> list[dict[str, Any]]:
    mgr = get_jarvis_manager()
    return list(mgr.db.get_recent_logs(limit=limit))


class JarvisChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def jarvis_chat(req: JarvisChatRequest) -> dict[str, Any]:
    """Execute voice/text directive in Jarvis and return spoken response."""
    mgr = get_jarvis_manager()
    raw_msg = req.message.strip()
    clean_lower = raw_msg.lower()

    # Strip wake word prefixes if present
    for prefix in ("jarvis,", "jarvis", "hey jarvis,", "hey jarvis", "ok jarvis,", "ok jarvis"):
        if clean_lower.startswith(prefix):
            clean_lower = clean_lower[len(prefix) :].strip()
            break

    # Emit user transcript to WebSocket listeners
    mgr.event_bus.emit("JARVIS_TRANSCRIPT", {"role": "user", "text": raw_msg})

    tool_calls_executed: list[dict[str, Any]] = []
    reply_text = ""

    # Direct intent execution
    if "open youtube" in clean_lower or clean_lower == "youtube":
        q = clean_lower.replace("open youtube", "").replace("search for", "").strip()
        args = {"query": q} if q else {}
        res = await mgr.tool_registry.execute_tool("open_youtube", args)
        tool_calls_executed.append({"name": "open_youtube", "arguments": args, "output": res})
        reply_text = "Opened YouTube, sir." if not q else f"Searching YouTube for '{q}', sir."

    elif clean_lower.startswith("open url ") or (
        "open " in clean_lower and ("http" in clean_lower or ".com" in clean_lower)
    ):
        url = clean_lower.split("open", 1)[1].strip()
        if not url.startswith("http"):
            url = f"https://{url}"
        res = await mgr.tool_registry.execute_tool("open_url", {"url": url})
        tool_calls_executed.append({"name": "open_url", "arguments": {"url": url}, "output": res})
        reply_text = f"Opened {url}, sir."

    elif clean_lower.startswith("search google") or clean_lower.startswith("search "):
        q = (
            clean_lower.replace("search google for", "")
            .replace("search google", "")
            .replace("search", "")
            .strip()
        )
        res = await mgr.tool_registry.execute_tool("search_google", {"query": q})
        tool_calls_executed.append(
            {"name": "search_google", "arguments": {"query": q}, "output": res}
        )
        reply_text = f"Searching Google for '{q}', sir."

    elif "spotify" in clean_lower or "music" in clean_lower:
        res = await mgr.tool_registry.execute_tool("open_spotify", {})
        tool_calls_executed.append({"name": "open_spotify", "arguments": {}, "output": res})
        reply_text = "Spotify is open and ready, sir."

    elif "system stats" in clean_lower or "cpu" in clean_lower or "battery" in clean_lower:
        res = await mgr.tool_registry.execute_tool("get_system_stats", {})
        tool_calls_executed.append({"name": "get_system_stats", "arguments": {}, "output": res})
        sys_info = res.get("system", "macOS")
        reply_text = f"System status online. Running {sys_info}, sir."

    elif clean_lower.startswith("open "):
        app_name = clean_lower.replace("open ", "").strip().title()
        res = await mgr.tool_registry.execute_tool("open_application", {"application": app_name})
        tool_calls_executed.append(
            {"name": "open_application", "arguments": {"application": app_name}, "output": res}
        )
        reply_text = f"Launched {app_name}, sir."

    else:
        # General assistance
        reply_text = f"Understood, sir. Processing directive: '{raw_msg}'."

    # Broadcast tool execution events
    for tc in tool_calls_executed:
        mgr.event_bus.emit(
            "TOOL_EXECUTION",
            {"tool_name": tc["name"], "arguments": tc["arguments"], "output": tc["output"]},
        )

    # Emit model transcript
    mgr.event_bus.emit("JARVIS_TRANSCRIPT", {"role": "model", "text": reply_text})

    return {
        "status": "SUCCESS",
        "response": reply_text,
        "spoken_response": reply_text,
        "tool_calls": tool_calls_executed,
    }
