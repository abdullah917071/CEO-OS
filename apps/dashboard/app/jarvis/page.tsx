"use client";

/**
 * Jarvis Voice Studio — Full-featured voice assistant dashboard
 *
 * Combines:
 * - Live chat conversation feed (wake-word events shown as system messages)
 * - Voice waveform visualizer
 * - Configuration tabs (Google Cloud, wake-word, audio, tools, logs)
 * - Real-time WebSocket telemetry
 */

import { useEffect, useRef, useState, useCallback, memo } from "react";
import { VoiceOrb } from "../../components/voice-orb";
import { ChatBubble, ThinkingBubble } from "../../components/chat-message";
import type { ChatMessage } from "../../components/chat-message";
import { API, WS } from "../../lib/api";

/* ─── Types ─────────────────────────────────────────────────────────────── */
type JarvisState = "IDLE_WAKE_WORD" | "ACTIVE" | "ENDING" | string;

type JarvisStatus = {
  state: JarvisState;
  is_running: boolean;
  is_muted: boolean;
  wake_word: string;
  wake_model: string;
  gemini_model: string;
  gemini_voice: string;
  gemini_connected: boolean;
  active_session_id: string | null;
  service_account_configured: boolean;
  project_id: string | null;
  today_sessions: number;
  active_minutes_today: number;
  estimated_cost_usd_today: number;
  tool_calls_today: number;
};

type ToolInfo = {
  name: string;
  description: string;
  parameters: unknown;
  permission: "ALLOW" | "ASK" | "DENY";
};

type LogRecord = {
  timestamp: string;
  level: string;
  event_type: string;
  message: string;
};

type AudioTelemetry = {
  rms: number;
  meter: string;
  is_speech: boolean;
};

/* ─── Waveform bars visualizer ──────────────────────────────────────────── */
const WaveformBars = memo(function WaveformBars({
  rms, isActive,
}: { rms: number; isActive: boolean }) {
  const BAR_COUNT = 16;
  const bars = Array.from({ length: BAR_COUNT }, (_, i) => {
    const center = Math.abs(i - BAR_COUNT / 2) / (BAR_COUNT / 2);
    const base = isActive ? Math.max(0.15, 1 - center * 0.8) * rms * 2.5 : 0.08;
    return Math.min(1, Math.max(0.05, base));
  });

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 2, height: 32 }}>
      {bars.map((h, i) => (
        <div
          key={i}
          style={{
            width: 3,
            height: `${h * 100}%`,
            borderRadius: 99,
            background: isActive
              ? `rgba(6,182,212,${0.4 + h * 0.6})`
              : "rgba(71,85,105,0.4)",
            transition: "height 60ms ease, background 200ms ease",
          }}
        />
      ))}
    </div>
  );
});

/* ─── Stat mini card ─────────────────────────────────────────────────────── */
const MiniStat = memo(function MiniStat({
  label, value, sub, color = "var(--color-text-primary)",
}: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="metricCard" style={{ padding: "10px 14px" }}>
      <div className="metricLabel">{label}</div>
      <div style={{ fontSize: "1.2rem", fontWeight: 700, fontFamily: "var(--font-mono)", color, lineHeight: 1, marginTop: 4 }}>
        {value}
      </div>
    </div>
  );
});

/* ─── Page ───────────────────────────────────────────────────────────────── */
export default function JarvisVoiceStudioPage() {
  const [status, setStatus]     = useState<JarvisStatus | null>(null);
  const [tools, setTools]       = useState<ToolInfo[]>([]);
  const [logs, setLogs]         = useState<LogRecord[]>([]);
  const [audio, setAudio]       = useState<AudioTelemetry>({ rms: 0, meter: " ", is_speech: false });
  const [testResult, setTestResult] = useState<string | null>(null);
  const [isTesting, setIsTesting]   = useState(false);

  // Active tab
  const [activeTab, setActiveTab] = useState<
    "chat" | "overview" | "google" | "wakeword" | "audio" | "tools" | "logs"
  >("chat");

  // Voice chat state (embedded Jarvis conversation)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: "jarvis-welcome",
      sender: "jarvis",
      text: `I'm Jarvis — your voice-activated AI assistant.\n\nI'm currently listening locally for the wake word "${status?.wake_word || "Jarvis"}". When I hear it, I'll connect to Gemini Live for a real-time bidirectional conversation.\n\nYou can also send directives here directly.`,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [voiceInput, setVoiceInput] = useState("");
  const [isSendingChat, setIsSendingChat] = useState(false);
  const [orbState, setOrbState] = useState<"idle" | "listening" | "thinking" | "speaking">("idle");
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Config form state
  const [svcAccountJson, setSvcAccountJson] = useState("");
  const [systemPrompt, setSystemPrompt]     = useState("");
  const [inactivityTimeout, setInactivityTimeout] = useState(60);
  const [selectedVoice, setSelectedVoice]   = useState("Puck");
  const [selectedModel, setSelectedModel]   = useState("gemini-2.0-flash-exp");
  const [wakeSensitivity, setWakeSensitivity] = useState(0.5);
  const [echoCancellation, setEchoCancellation] = useState(true);
  const [noiseSuppression, setNoiseSuppression] = useState(true);

  /* ── Auto-scroll chat ─────────────────────────────────────────────── */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, isSendingChat]);

  /* ── Polling + WebSocket ──────────────────────────────────────────── */
  useEffect(() => {
    fetchStatus();
    fetchTools();
    fetchLogs();
    const pollInterval = setInterval(() => { fetchStatus(); fetchLogs(); }, 3000);

    let ws: WebSocket | null = null;
    let prevState: string | null = null;

    try {
      ws = new WebSocket(`${WS}/ws/jarvis/status`);
      ws.onmessage = (ev) => {
        try {
          const payload = JSON.parse(ev.data);
          if (payload.type === "AUDIO_FRAME_TELEMETRY") {
            setAudio(payload.data);
            if (payload.data.is_speech) setOrbState("speaking");
          } else if (payload.type === "STATUS_UPDATE" || payload.type === "HEARTBEAT") {
            const newStatus = payload.data as JarvisStatus;
            setStatus(newStatus);

            // Inject state transition as system chat message
            if (prevState !== null && prevState !== newStatus.state) {
              const transitionMsg: ChatMessage = {
                id: `sys-${Date.now()}`,
                sender: "system",
                text:
                  newStatus.state === "ACTIVE"
                    ? `🔴 Wake word detected! Gemini Live session started. Speak naturally — I'm listening.`
                    : newStatus.state === "IDLE_WAKE_WORD"
                    ? `🔵 Session ended. Returning to local wake-word detection. Say "${newStatus.wake_word}" to start again.`
                    : `State changed: ${newStatus.state}`,
                timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              };
              setChatMessages((prev) => [...prev, transitionMsg]);

              setOrbState(newStatus.state === "ACTIVE" ? "listening" : "idle");
            }
            prevState = newStatus.state;
          } else if (payload.type === "TOOL_EXECUTION") {
            const toolMsg: ChatMessage = {
              id: `tool-${Date.now()}`,
              sender: "action",
              text: `Executed tool: ${payload.tool_name}`,
              actionType: "tool_exec",
              actionTarget: payload.tool_name,
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            };
            setChatMessages((prev) => [...prev, toolMsg]);
          } else if (payload.type === "JARVIS_TRANSCRIPT") {
            if (payload.role === "user") {
              setChatMessages((prev) => [
                ...prev,
                {
                  id: `vuser-${Date.now()}`,
                  sender: "user",
                  text: payload.text,
                  timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                } as ChatMessage,
              ]);
              setOrbState("thinking");
            } else if (payload.role === "model") {
              setChatMessages((prev) => [
                ...prev,
                {
                  id: `vjarvis-${Date.now()}`,
                  sender: "jarvis",
                  text: payload.text,
                  timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                } as ChatMessage,
              ]);
              setOrbState("speaking");
            }
          }
        } catch {
          // ignore JSON parse errors
        }
      };
    } catch {
      // ws unavailable
    }

    return () => {
      clearInterval(pollInterval);
      ws?.close();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── API helpers ──────────────────────────────────────────────────── */
  async function fetchStatus() {
    try {
      const res = await fetch(`${API}/api/jarvis/status`);
      if (res.ok) setStatus(await res.json());
    } catch {}
  }
  async function fetchTools() {
    try {
      const res = await fetch(`${API}/api/jarvis/tools`);
      if (res.ok) { const d = await res.json(); setTools(d.tools || []); }
    } catch {}
  }
  async function fetchLogs() {
    try {
      const res = await fetch(`${API}/api/jarvis/logs?limit=40`);
      if (res.ok) setLogs(await res.json());
    } catch {}
  }

  /* ── Session controls ─────────────────────────────────────────────── */
  async function handleActivate() {
    try { await fetch(`${API}/api/jarvis/session/activate`, { method: "POST" }); await fetchStatus(); } catch {}
  }
  async function handleEnd() {
    try { await fetch(`${API}/api/jarvis/session/end`, { method: "POST" }); await fetchStatus(); } catch {}
  }
  async function handleToggleMute() {
    if (!status) return;
    try {
      await fetch(`${API}/api/jarvis/agent/mute`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ muted: !status.is_muted }),
      });
      await fetchStatus();
    } catch {}
  }

  /* ── Testing ──────────────────────────────────────────────────────── */
  async function handleTestWakeWord() {
    setIsTesting(true); setTestResult(null);
    try {
      const res = await fetch(`${API}/api/jarvis/wakeword/test`, { method: "POST" });
      const d = await res.json();
      setTestResult(`✓ Wake word "${d.wake_word}" detected! Latency: ${d.latency_ms?.toFixed(0)}ms, Confidence: ${((d.confidence ?? 0) * 100).toFixed(0)}%`);
    } catch (e: any) { setTestResult(`✗ Wake word test failed: ${e.message}`); }
    finally { setIsTesting(false); }
  }

  async function handleTestVertex() {
    setIsTesting(true); setTestResult(null);
    try {
      const res = await fetch(`${API}/api/jarvis/gemini/test`, { method: "POST" });
      const d = await res.json();
      setTestResult(d.success
        ? `✓ Vertex AI connected! Project: ${d.project_id}, Region: ${d.location}`
        : `✗ Connection failed: ${d.error || d.message}`);
    } catch (e: any) { setTestResult(`✗ Connection test failed: ${e.message}`); }
    finally { setIsTesting(false); }
  }

  async function handleSaveServiceAccount() {
    if (!svcAccountJson.trim()) { alert("Paste service account JSON first"); return; }
    try {
      const parsed = JSON.parse(svcAccountJson);
      const res = await fetch(`${API}/api/jarvis/gemini/service-account`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ service_account_json: parsed }),
      });
      const d = await res.json();
      if (res.ok) { alert("✓ Service account stored securely (0600 permissions)"); setSvcAccountJson(""); await fetchStatus(); }
      else alert(`Failed: ${d.detail || "Error"}`);
    } catch (e: any) { alert("Invalid JSON: " + e.message); }
  }

  async function handleToolPermission(name: string, mode: "ALLOW" | "ASK" | "DENY") {
    try {
      await fetch(`${API}/api/jarvis/tools/${name}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      await fetchTools();
    } catch {}
  }

  /* ── Embedded chat send (text commands to Jarvis) ────────────────── */
  const handleChatSend = useCallback(async () => {
    const text = voiceInput.trim();
    if (!text || isSendingChat) return;

    setChatMessages((prev) => [
      ...prev,
      {
        id: `cu-${Date.now()}`,
        sender: "user",
        text,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      } as ChatMessage,
    ]);
    setVoiceInput("");
    setIsSendingChat(true);
    setOrbState("thinking");

    try {
      const res = await fetch(`${API}/api/jarvis/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const d = await res.json();

      if (d.tool_calls) {
        for (const tc of d.tool_calls as any[]) {
          if (["open_url","launch_application","open_application"].includes(tc.name)) {
            const target = String(tc.arguments?.url ?? tc.arguments?.app_name ?? "");
            setChatMessages((prev) => [
              ...prev,
              {
                id: `act-${Date.now()}`,
                sender: "action",
                text: tc.name === "open_url" ? `Opened URL — ${target}` : `Launched — ${target}`,
                actionType: tc.name === "open_url" ? "opened_url" : "opened_app",
                actionTarget: target,
                timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              } as ChatMessage,
            ]);
          }
        }
      }

      const reply = d.response || d.final_answer || d.message || "Done.";
      setChatMessages((prev) => [
        ...prev,
        {
          id: `jr-${Date.now()}`,
          sender: "jarvis",
          text: reply,
          toolCalls: d.tool_calls,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        } as ChatMessage,
      ]);

      // Speak back
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        const utt = new SpeechSynthesisUtterance(reply.replace(/[*#`_]/g, "").slice(0, 300));
        utt.rate = 1.05; utt.pitch = 0.9;
        utt.onstart = () => setOrbState("speaking");
        utt.onend   = () => setOrbState("idle");
        window.speechSynthesis.speak(utt);
      } else {
        setOrbState("idle");
      }
    } catch (e: any) {
      setChatMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          sender: "system",
          text: `Failed: ${e.message}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        } as ChatMessage,
      ]);
      setOrbState("idle");
    } finally {
      setIsSendingChat(false);
    }
  }, [voiceInput, isSendingChat]);

  const isActive = status?.state === "ACTIVE";

  /* ── Render ─────────────────────────────────────────────────────── */
  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>

      {/* ── Header ───────────────────────────────────────────────── */}
      <div className="card" style={{ padding: "20px 24px", background: "linear-gradient(135deg, #0d0e1a, #0f0f1e)", position: "relative", overflow: "hidden" }}>
        <div style={{ position: "absolute", right: -40, top: -40, width: 160, height: 160, borderRadius: "50%", background: "rgba(6,182,212,0.07)", filter: "blur(30px)", pointerEvents: "none" }} />

        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            {/* Orb */}
            <div className={`orbRing ${orbState}`}>
              <VoiceOrb state={orbState} size={56} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <h1 style={{ fontSize: "1.4rem", fontWeight: 800, letterSpacing: "0.04em", background: "linear-gradient(90deg, #06b6d4, #3b82f6)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
                  JARVIS
                </h1>
                <span className="badge badge-cyan" style={{ fontSize: "0.6rem" }}>REALTIME VOICE</span>
                <span
                  className={`badge ${isActive ? "badge-emerald" : "badge-amber"}`}
                  style={{ fontSize: "0.6rem" }}
                >
                  {status?.state ?? "INITIALIZING"}
                </span>
              </div>
              <p style={{ fontSize: "0.78rem", color: "var(--color-text-secondary)" }}>
                Local wake-word detection · Gemini Live WebSocket · Safe macOS tool execution
              </p>
            </div>
          </div>

          {/* Session controls */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              onClick={handleToggleMute}
              className={`btn ${status?.is_muted ? "btn-danger" : "btn-ghost"}`}
              style={{ fontSize: "0.75rem" }}
            >
              {status?.is_muted ? "🔇 Unmute" : "🎙️ Mute Mic"}
            </button>
            {isActive ? (
              <button onClick={handleEnd} className="btn" style={{ background: "var(--color-amber)", color: "#000", fontWeight: 700, fontSize: "0.75rem" }}>
                ⏹ End Session
              </button>
            ) : (
              <button onClick={handleActivate} className="btn btn-primary" style={{ fontSize: "0.75rem" }}>
                ⚡ Activate Gemini Live
              </button>
            )}
          </div>
        </div>

        {/* Live waveform */}
        <div style={{ marginTop: 14, display: "flex", alignItems: "center", gap: 12, borderTop: "1px solid var(--color-border)", paddingTop: 12 }}>
          <WaveformBars rms={audio.rms} isActive={audio.is_speech} />
          <span style={{ fontSize: "0.65rem", fontFamily: "var(--font-mono)", color: "var(--color-text-muted)" }}>
            RMS: {audio.rms} · VAD: <span style={{ color: audio.is_speech ? "var(--color-emerald)" : "var(--color-text-muted)" }}>{audio.is_speech ? "SPEECH" : "SILENCE"}</span>
            {status && <> · 💰 $0.00 idle (Gemini disconnected)</>}
          </span>
        </div>
      </div>

      {/* ── Metrics ──────────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12 }}>
        <MiniStat label="Today Sessions" value={status?.today_sessions ?? 0} color="var(--color-cyan)" />
        <MiniStat label="Active Minutes" value={status?.active_minutes_today ?? 0} sub="today" />
        <MiniStat label="Tool Calls" value={status?.tool_calls_today ?? 0} color="var(--color-purple)" />
        <MiniStat
          label="Est. Cost Today"
          value={`$${(status?.estimated_cost_usd_today ?? 0).toFixed(4)}`}
          color="var(--color-emerald)"
        />
      </div>

      {/* ── Tabs ─────────────────────────────────────────────────── */}
      <div className="tabs">
        {[
          { id: "chat",     label: "💬 Live Conversation" },
          { id: "overview", label: "🧪 Tests & Controls" },
          { id: "google",   label: "🌐 Google Cloud" },
          { id: "wakeword", label: "🗣️ Wake Word" },
          { id: "audio",    label: "🎛️ Audio" },
          { id: "tools",    label: "🛡️ Tools" },
          { id: "logs",     label: "📜 Logs" },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id as any)}
            className={`tab ${activeTab === tab.id ? "active" : ""}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── Tab: Conversation ─────────────────────────────────────── */}
      {activeTab === "chat" && (
        <div className="card" style={{ display: "flex", flexDirection: "column", minHeight: 520, maxHeight: 680 }}>
          <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--color-border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: isActive ? "var(--color-emerald)" : "var(--color-cyan)", animation: "pulse 2s infinite", display: "inline-block" }} />
              <span style={{ fontSize: "0.8125rem", fontWeight: 600 }}>
                {isActive ? "Live Gemini Session Active" : `Waiting for "${status?.wake_word || "Jarvis"}"…`}
              </span>
            </div>
            <button
              type="button"
              onClick={() => setChatMessages([])}
              style={{ fontSize: "0.7rem", color: "var(--color-text-muted)", background: "none", border: "none", cursor: "pointer" }}
            >
              Clear
            </button>
          </div>

          <div className="chatFeed" style={{ flex: 1, overflowY: "auto" }}>
            {chatMessages.map((msg) => (
              <div key={msg.id} className="fadeIn">
                <ChatBubble
                  message={msg}
                  onSpeak={(text) => {
                    if ("speechSynthesis" in window) {
                      window.speechSynthesis.cancel();
                      const utt = new SpeechSynthesisUtterance(text);
                      utt.rate = 1.05; utt.pitch = 0.9;
                      window.speechSynthesis.speak(utt);
                    }
                  }}
                />
              </div>
            ))}
            {isSendingChat && <div className="fadeIn"><ThinkingBubble /></div>}
            <div ref={chatEndRef} />
          </div>

          <div style={{ borderTop: "1px solid var(--color-border)", padding: "12px 16px", background: "rgba(7,8,16,0.4)", borderRadius: "0 0 var(--radius-xl) var(--radius-xl)" }}>
            <div style={{ display: "flex", gap: 8 }}>
              <input
                type="text"
                value={voiceInput}
                onChange={(e) => setVoiceInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") void handleChatSend(); }}
                placeholder='Send a text command to Jarvis (e.g. "open YouTube")'
                className="chatInput"
                style={{ flex: 1, height: 40 }}
                disabled={isSendingChat}
              />
              <button
                type="button"
                onClick={handleChatSend}
                disabled={isSendingChat || !voiceInput.trim()}
                className="btn btn-primary"
                style={{ height: 40, flexShrink: 0 }}
              >
                {isSendingChat ? (
                  <span className="spin" style={{ width: 14, height: 14, borderRadius: "50%", border: "2px solid rgba(0,0,0,0.2)", borderTopColor: "#000", display: "inline-block" }} />
                ) : "Send"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Overview / Tests ─────────────────────────────────── */}
      {activeTab === "overview" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="card" style={{ padding: 24 }}>
            <h2 style={{ fontSize: "0.875rem", fontFamily: "var(--font-mono)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
              🧪 Component Tests
            </h2>
            <p style={{ fontSize: "0.78rem", color: "var(--color-text-secondary)", marginBottom: 16 }}>
              Verify individual subsystems before a full live session.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 10 }}>
              {[
                { label: "🗣️ Test Wake Word", sub: "Local detector latency", fn: handleTestWakeWord },
                { label: "🌐 Test Vertex AI", sub: "Service account reachability", fn: handleTestVertex },
                { label: "⚡ Force Activate", sub: "Bypass wake-word, open session", fn: handleActivate },
                { label: "⏹ Force End", sub: "Close active session", fn: handleEnd },
              ].map((btn) => (
                <button
                  key={btn.label}
                  onClick={btn.fn}
                  disabled={isTesting}
                  className="btn btn-ghost"
                  style={{ flexDirection: "column", alignItems: "flex-start", padding: "12px 16px", height: "auto", gap: 4 }}
                >
                  <span style={{ fontWeight: 700, fontSize: "0.8125rem" }}>{btn.label}</span>
                  <span style={{ fontSize: "0.65rem", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>{btn.sub}</span>
                </button>
              ))}
            </div>
            {testResult && (
              <div style={{ marginTop: 14, padding: "10px 14px", borderRadius: "var(--radius-md)", background: "var(--color-bg)", border: "1px solid var(--color-border)", fontSize: "0.75rem", fontFamily: "var(--font-mono)", color: testResult.startsWith("✓") ? "var(--color-emerald)" : "var(--color-red)" }}>
                {testResult}
              </div>
            )}
          </div>

          <div className="card" style={{ padding: 24 }}>
            <h3 style={{ fontSize: "0.8125rem", fontFamily: "var(--font-mono)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12 }}>
              🔒 Architecture Invariants
            </h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              {[
                { title: "Zero Idle API Cost", body: "Gemini Live WebSocket is 100% disconnected while listening for the wake word. Audio is processed entirely on-device." },
                { title: "Instant Barge-In", body: "Speaking immediately increments the playback generation ID and drops stale Gemini audio chunks in flight." },
                { title: "Local Wake-Word", body: "openWakeWord ONNX model runs on CPU — never sends audio to any cloud until \"Jarvis\" is detected." },
                { title: "Safe Tool Execution", body: "Each macOS tool has a configurable permission: ALLOW / ASK / DENY. DENY tools are excluded from Gemini schemas." },
              ].map((inv) => (
                <div key={inv.title} style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "12px 14px" }}>
                  <div style={{ fontSize: "0.78rem", fontWeight: 600, marginBottom: 4 }}>{inv.title}</div>
                  <div style={{ fontSize: "0.7rem", color: "var(--color-text-secondary)", lineHeight: 1.5 }}>{inv.body}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Google Cloud ─────────────────────────────────────── */}
      {activeTab === "google" && (
        <div className="card" style={{ padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
          <div>
            <h2 style={{ fontSize: "0.875rem", fontFamily: "var(--font-mono)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>
              Google Cloud Service Account (Vertex AI)
            </h2>
            <p style={{ fontSize: "0.78rem", color: "var(--color-text-secondary)", marginTop: 4 }}>
              Paste your service account JSON. It's stored by the backend with 0600 permissions — private keys never reach the browser.
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", borderRadius: "var(--radius-md)", background: status?.service_account_configured ? "rgba(16,185,129,0.08)" : "rgba(239,68,68,0.08)", border: `1px solid ${status?.service_account_configured ? "rgba(16,185,129,0.25)" : "rgba(239,68,68,0.25)"}` }}>
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: status?.service_account_configured ? "var(--color-emerald)" : "var(--color-red)", flexShrink: 0 }} />
            <span style={{ fontSize: "0.78rem", fontFamily: "var(--font-mono)" }}>
              {status?.service_account_configured
                ? `✓ Service account configured · Project: ${status.project_id}`
                : "✗ Service account not configured"}
            </span>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.75rem", fontFamily: "var(--font-mono)", marginBottom: 6, color: "var(--color-text-secondary)" }}>
              Paste Service Account JSON:
            </label>
            <textarea
              value={svcAccountJson}
              onChange={(e) => setSvcAccountJson(e.target.value)}
              placeholder='{"type": "service_account", "project_id": "...", "private_key": "..."}'
              rows={6}
              className="textarea"
            />
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <button onClick={handleSaveServiceAccount} className="btn btn-primary" style={{ fontSize: "0.78rem" }}>
              💾 Save Securely
            </button>
            <button onClick={handleTestVertex} disabled={isTesting} className="btn btn-ghost" style={{ fontSize: "0.78rem" }}>
              🔍 Test Connection
            </button>
          </div>

          <div style={{ borderTop: "1px solid var(--color-border)", paddingTop: 16, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontFamily: "var(--font-mono)", marginBottom: 6, color: "var(--color-text-secondary)" }}>Gemini Model</label>
              <select value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} className="select" style={{ width: "100%" }}>
                <option value="gemini-2.0-flash-exp">gemini-2.0-flash-exp (Default)</option>
                <option value="gemini-2.0-flash-realtime">gemini-2.0-flash-realtime</option>
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontFamily: "var(--font-mono)", marginBottom: 6, color: "var(--color-text-secondary)" }}>Prebuilt Voice</label>
              <select value={selectedVoice} onChange={(e) => setSelectedVoice(e.target.value)} className="select" style={{ width: "100%" }}>
                {["Puck","Charon","Kore","Fenrir","Aoede"].map((v) => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Wake Word ────────────────────────────────────────── */}
      {activeTab === "wakeword" && (
        <div className="card" style={{ padding: 24 }}>
          <h2 style={{ fontSize: "0.875rem", fontFamily: "var(--font-mono)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 16 }}>
            Local Wake-Word Engine
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontFamily: "var(--font-mono)", marginBottom: 6, color: "var(--color-text-secondary)" }}>Active Wake Word</label>
                <select className="select" style={{ width: "100%" }}>
                  {["Jarvis (jarvis.onnx)","Computer (computer.onnx)","Friday (friday.onnx)","Assistant (assistant.onnx)","Hey Nova (hey_nova.onnx)"].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </div>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontFamily: "var(--font-mono)", marginBottom: 6, color: "var(--color-text-secondary)" }}>
                  Sensitivity: {wakeSensitivity}
                </label>
                <input type="range" min={0.1} max={0.9} step={0.05} value={wakeSensitivity} onChange={(e) => setWakeSensitivity(parseFloat(e.target.value))} className="range" />
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.65rem", fontFamily: "var(--font-mono)", color: "var(--color-text-muted)", marginTop: 4 }}>
                  <span>Fewer false triggers</span><span>More sensitive</span>
                </div>
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontFamily: "var(--font-mono)", marginBottom: 6, color: "var(--color-text-secondary)" }}>
                  Inactivity Timeout: {inactivityTimeout}s
                </label>
                <input type="range" min={15} max={120} step={15} value={inactivityTimeout} onChange={(e) => setInactivityTimeout(parseInt(e.target.value))} className="range" />
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.65rem", fontFamily: "var(--font-mono)", color: "var(--color-text-muted)", marginTop: 4 }}>
                  <span>15s</span><span>60s</span><span>120s</span>
                </div>
              </div>
              <button onClick={handleTestWakeWord} disabled={isTesting} className="btn btn-ghost" style={{ fontSize: "0.78rem" }}>
                ⚡ Test Wake Word Detector
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Audio ───────────────────────────────────────────── */}
      {activeTab === "audio" && (
        <div className="card" style={{ padding: 24 }}>
          <h2 style={{ fontSize: "0.875rem", fontFamily: "var(--font-mono)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 16 }}>
            Audio Processing
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                { label: "Acoustic Echo Cancellation (AEC)", sub: "Prevents Jarvis from hearing its own voice", val: echoCancellation, set: setEchoCancellation },
                { label: "Noise Suppression + AGC", sub: "Suppresses fan noise and keyboard clicks", val: noiseSuppression, set: setNoiseSuppression },
              ].map((ctrl) => (
                <div key={ctrl.label} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 14px", background: "var(--color-bg)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)" }}>
                  <div>
                    <div style={{ fontSize: "0.78rem", fontWeight: 600 }}>{ctrl.label}</div>
                    <div style={{ fontSize: "0.65rem", color: "var(--color-text-muted)", marginTop: 2 }}>{ctrl.sub}</div>
                  </div>
                  <input type="checkbox" checked={ctrl.val} onChange={(e) => ctrl.set(e.target.checked)} className="checkbox" />
                </div>
              ))}
            </div>
            <div style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "16px 20px" }}>
              <div style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)", fontWeight: 600, marginBottom: 12 }}>Live Mic Telemetry</div>
              <WaveformBars rms={audio.rms} isActive={audio.is_speech} />
              <div style={{ marginTop: 10, fontSize: "0.7rem", fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)" }}>
                RMS: <span style={{ color: "var(--color-text-primary)" }}>{audio.rms}</span>
                {" · "}VAD: <span style={{ color: audio.is_speech ? "var(--color-emerald)" : "var(--color-text-muted)", fontWeight: 700 }}>{audio.is_speech ? "SPEECH" : "SILENCE"}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Tab: Tools ───────────────────────────────────────────── */}
      {activeTab === "tools" && (
        <div className="card" style={{ padding: 24 }}>
          <h2 style={{ fontSize: "0.875rem", fontFamily: "var(--font-mono)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
            Safe macOS Tool Permissions
          </h2>
          <p style={{ fontSize: "0.78rem", color: "var(--color-text-secondary)", marginBottom: 16 }}>
            DENY removes tools from Gemini schemas entirely. ASK prompts before execution.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
            {tools.map((tool, i) => (
              <div
                key={tool.name}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12,
                  padding: "12px 4px",
                  borderTop: i > 0 ? "1px solid var(--color-border)" : "none",
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: "0.78rem", fontFamily: "var(--font-mono)", fontWeight: 600, color: "var(--color-cyan)" }}>{tool.name}</div>
                  <div style={{ fontSize: "0.65rem", color: "var(--color-text-muted)", marginTop: 2 }}>{tool.description}</div>
                </div>
                <div style={{ display: "flex", gap: 5, flexShrink: 0 }}>
                  {(["ALLOW", "ASK", "DENY"] as const).map((mode) => (
                    <button
                      key={mode}
                      onClick={() => handleToolPermission(tool.name, mode)}
                      className={`permBtn ${tool.permission === mode ? mode.toLowerCase() : ""}`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            {tools.length === 0 && (
              <div style={{ padding: "24px 0", textAlign: "center", fontSize: "0.78rem", color: "var(--color-text-muted)" }}>
                No tools loaded. Start the Jarvis backend to see available tools.
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Tab: Logs ────────────────────────────────────────────── */}
      {activeTab === "logs" && (
        <div className="card" style={{ padding: 24 }}>
          <h2 style={{ fontSize: "0.875rem", fontFamily: "var(--font-mono)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 12 }}>
            Structured Event Logs (Secrets Auto-Redacted)
          </h2>
          <div style={{ background: "var(--color-bg)", border: "1px solid var(--color-border)", borderRadius: "var(--radius-md)", padding: "12px 16px", maxHeight: 400, overflowY: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
            {logs.length === 0 ? (
              <div style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>No logs yet.</div>
            ) : (
              logs.map((log, i) => (
                <div key={i} className="logLine">
                  <span className="logTime">{log.timestamp.slice(11, 19)}</span>
                  <span className={`logTag ${log.level}`}>[{log.event_type}]</span>
                  <span className="logMsg">{log.message}</span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
