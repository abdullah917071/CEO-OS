"use client";

/**
 * CEO OS — Main Executive Chat Page
 *
 * Following skills applied:
 * - frontend-developer: memo, useCallback, performance-first, TypeScript
 * - ui-designer: design tokens, visual hierarchy, micro-interactions
 * - technical-writer: clear naming, inline docs
 *
 * Key flows:
 *   1. User types or speaks → /api/v1/chat/interactive → LLM response
 *   2. Tool calls (e.g. open_url) → action confirmation card + speech reply
 *   3. "Jarvis, open YouTube" → Jarvis says "Opened sir" → URL opens
 *   4. WebSocket live task feed from /ws
 *   5. Agency skill router preview while typing
 */

import Link from "next/link";
import {
  FormEvent,
  memo,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { ChatBubble, ThinkingBubble } from "../components/chat-message";
import type { ChatMessage } from "../components/chat-message";
import { LiveTaskCard } from "../components/live-task-card";
import type { LiveTask } from "../components/live-task-card";
import { VoiceOrb } from "../components/voice-orb";
import { useLiveState } from "../components/dashboard-shell";
import { requestJson, WS } from "../lib/api";
import type { AgencyMatchResponse, InteractiveChatResponse, Task } from "../lib/contracts";

/* ─── Quick command palette ─────────────────────────────────────────────── */
const QUICK_COMMANDS = [
  { label: "🌐 Open YouTube",           text: "Jarvis, open YouTube",                    speak: true },
  { label: "🎵 Spotify Music",          text: "Jarvis, open Spotify and play music",     speak: true },
  { label: "🔍 Search AI News",         text: "Search Google for latest AI breakthroughs", speak: true },
  { label: "💻 System Stats",           text: "Jarvis, check macOS system stats and CPU load", speak: true },
  { label: "☁️ Cloud Cost Audit",       text: "CEO, audit our AWS cloud spend",          speak: false },
  { label: "🔒 Security Threat Model",  text: "CEO, perform an AppSec threat model",     speak: false },
  { label: "📧 Draft Email",            text: "Draft a professional follow-up email",    speak: false },
  { label: "📊 Agent Roster",           text: "Show me the top 5 specialist agents for data engineering", speak: false },
] as const;

/* ─── Wake-word constants ───────────────────────────────────────────────── */
const WAKE_WORDS = ["jarvis", "hey jarvis", "ok jarvis"];

/* ─── Helpers ───────────────────────────────────────────────────────────── */
function startsWithWakeWord(text: string): boolean {
  const lower = text.trim().toLowerCase();
  return WAKE_WORDS.some((w) => lower.startsWith(w));
}

function buildWelcome(): ChatMessage {
  return {
    id: "welcome-0",
    sender: "jarvis",
    text: "Good day, sir. CEO OS Executive AI and Jarvis Voice Control are online.\n\nYou can type a directive or click the 🎙️ microphone and say:\n  \"Jarvis, open YouTube\"\n  \"Jarvis, check my system stats\"\n  \"CEO, audit our cloud spend\"\n\nHow may I assist you?",
    thought: "System initialized. CEO ReAct engine, Gemini Live (WebSocket), openWakeWord detector, and 270+ Agency agents are ready.",
    timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
  };
}

/* ─── StatCard: memoized metric tile ───────────────────────────────────── */
const StatCard = memo(function StatCard({
  label, value, sub, accent = "cyan",
}: { label: string; value: string | number; sub?: string; accent?: "cyan" | "emerald" | "purple" | "amber" }) {
  const colors = {
    cyan:    "var(--color-cyan)",
    emerald: "var(--color-emerald)",
    purple:  "var(--color-purple)",
    amber:   "var(--color-amber)",
  };
  return (
    <div className="metricCard">
      <div className="metricLabel">{label}</div>
      <div className="metricValue" style={{ color: colors[accent] }}>{value}</div>
      {sub && <div style={{ fontSize: "0.7rem", color: "var(--color-text-muted)", marginTop: 4, fontFamily: "var(--font-mono)" }}>{sub}</div>}
    </div>
  );
});

/* ─── Page Component ─────────────────────────────────────────────────────── */
export default function ExecutiveChatPage() {
  const { revision, activeTaskCount, totalTaskCount } = useLiveState();

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([buildWelcome()]);
  const [inputMessage, setInputMessage] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [matchedSkill, setMatchedSkill] = useState<{ name: string; score: number } | null>(null);

  // Voice state
  const [voiceOrb, setVoiceOrb] = useState<"idle" | "listening" | "thinking" | "speaking">("idle");
  const [voiceSupported, setVoiceSupported] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const recognitionRef = useRef<any>(null);

  // Live tasks via WebSocket
  const [liveTasks, setLiveTasks] = useState<LiveTask[]>([]);

  // Task metrics
  const [successRate, setSuccessRate] = useState(100);

  // Refs
  const chatEndRef = useRef<HTMLDivElement>(null);

  /* ── Auto-scroll chat ─────────────────────────────────────────────── */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isProcessing]);

  /* ── Poll tasks on revision change ───────────────────────────────── */
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await requestJson<Task[]>("/api/v1/tasks?limit=12");
        if (cancelled) return;
        const mapped: LiveTask[] = data.map((t: any) => ({
          id: t.id,
          status: t.status,
          message: t.message,
          objective: t.objective,
          created_at: t.created_at,
          updated_at: t.updated_at,
          steps: t.steps,
          error: t.error,
        }));
        setLiveTasks(mapped);
        const success = mapped.filter((t) => ["success","partial_success"].includes(t.status)).length;
        const rate = mapped.length > 0 ? Math.round((success / mapped.length) * 100) : 100;
        setSuccessRate(rate);
      } catch {
        // graceful
      }
    })();
    return () => { cancelled = true; };
  }, [revision]);

  /* ── Live task WebSocket ──────────────────────────────────────────── */
  useEffect(() => {
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(`${WS}/ws/tasks`);
      ws.onmessage = (ev) => {
        try {
          const payload = JSON.parse(ev.data);
          if (payload.task) {
            setLiveTasks((prev) => {
              const idx = prev.findIndex((t) => t.id === payload.task.id);
              if (idx >= 0) {
                const next = [...prev];
                next[idx] = payload.task;
                return next;
              }
              return [payload.task, ...prev].slice(0, 12);
            });
          }
        } catch {
          // ignore
        }
      };
    } catch {
      // ws unavailable
    }
    return () => ws?.close();
  }, []);

  /* ── Debounced skill match preview ───────────────────────────────── */
  useEffect(() => {
    const trimmed = inputMessage.trim();
    if (!trimmed || trimmed.length < 8) { setMatchedSkill(null); return; }
    const timer = setTimeout(async () => {
      try {
        const res = await requestJson<AgencyMatchResponse>("/api/v1/agency/match", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: trimmed, top_k: 1 }),
        });
        if (res.best_match) {
          setMatchedSkill({ name: res.best_match.skill_name, score: Math.round(res.best_match.relevance_score * 100) });
        } else {
          setMatchedSkill(null);
        }
      } catch {
        setMatchedSkill(null);
      }
    }, 280);
    return () => clearTimeout(timer);
  }, [inputMessage]);

  /* ── Speech synthesis helper ─────────────────────────────────────── */
  const speakText = useCallback((text: string) => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
    try {
      window.speechSynthesis.cancel();
      const clean = text.replace(/[*#`_]/g, "").trim();
      const utt = new SpeechSynthesisUtterance(clean);
      utt.rate = 1.05; utt.pitch = 0.9;
      utt.onstart = () => setVoiceOrb("speaking");
      utt.onend   = () => setVoiceOrb("idle");
      utt.onerror = () => setVoiceOrb("idle");
      window.speechSynthesis.speak(utt);
    } catch {
      setVoiceOrb("idle");
    }
  }, []);

  /* ── Speech Recognition setup ────────────────────────────────────── */
  useEffect(() => {
    if (typeof window === "undefined") return;
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { setVoiceSupported(false); return; }

    const rec = new SR();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = "en-US";

    rec.onresult = (event: any) => {
      let interim = "";
      let final   = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) final += t;
        else interim += t;
      }
      if (interim) setTranscript(interim);
      if (final) {
        setTranscript("");
        setIsListening(false);
        setInputMessage(final);
        void handleSend(final, true);
      }
    };
    rec.onerror = () => { setIsListening(false); setVoiceOrb("idle"); };
    rec.onend   = () => { setIsListening(false); if (voiceOrb === "listening") setVoiceOrb("idle"); };

    recognitionRef.current = rec;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleVoice = () => {
    if (!recognitionRef.current) return;
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
      setVoiceOrb("idle");
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
        setVoiceOrb("listening");
      } catch {
        setIsListening(false);
        setVoiceOrb("idle");
      }
    }
  };

  /* ── Core send handler ───────────────────────────────────────────── */
  const handleSend = useCallback(async (textToSend?: string, autoSpeak = false) => {
    const text = (textToSend ?? inputMessage).trim();
    if (!text || isProcessing) return;

    const isVoiceCommand = autoSpeak || startsWithWakeWord(text);

    // Push user message
    setMessages((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        sender: "user",
        text,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      } as ChatMessage,
    ]);

    setInputMessage("");
    setMatchedSkill(null);
    setIsProcessing(true);
    setVoiceOrb("thinking");

    try {
      const res = await requestJson<InteractiveChatResponse>("/api/v1/chat/interactive", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, voice_mode: isVoiceCommand }),
      });

      const msgId = `jarvis-${Date.now()}`;

      // Build action confirmation cards for macOS tool calls
      const actionMessages: ChatMessage[] = [];
      if (res.tool_calls) {
        for (const tc of res.tool_calls) {
          if (["open_url", "launch_application", "open_application"].includes(tc.name)) {
            const target = String(tc.arguments?.url ?? tc.arguments?.app_name ?? tc.arguments?.application_name ?? "");
            actionMessages.push({
              id: `action-${Date.now()}-${tc.name}`,
              sender: "action",
              text: tc.name === "open_url"
                ? `Opened URL in browser — ${target}`
                : `Launched application — ${target}`,
              actionType: tc.name === "open_url" ? "opened_url" : "opened_app",
              actionTarget: target,
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            } as ChatMessage);
          }
        }
      }

      setMessages((prev) => [
        ...prev,
        ...actionMessages,
        {
          id: msgId,
          sender: "jarvis",
          text: res.final_answer,
          thought: res.thought,
          toolCalls: res.tool_calls,
          steps: res.steps,
          durationMs: res.duration_ms,
          spokenResponse: res.spoken_response,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        } as ChatMessage,
      ]);

      if (isVoiceCommand) {
        speakText(res.spoken_response || res.final_answer);
      } else {
        setVoiceOrb("idle");
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          sender: "system",
          text: `Execution failed: ${err instanceof Error ? err.message : "Unknown error"}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        } as ChatMessage,
      ]);
      setVoiceOrb("idle");
    } finally {
      setIsProcessing(false);
    }
  }, [inputMessage, isProcessing, speakText]);

  const onSubmit = (e: FormEvent) => { e.preventDefault(); void handleSend(); };

  const activeTasksCount = liveTasks.filter((t) => ["planning","running","retrying","needs_approval"].includes(t.status)).length;

  /* ── Render ─────────────────────────────────────────────────────── */
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* ── Hero Metric Bar ─────────────────────────────────────────── */}
      <div
        className="card"
        style={{
          padding: "20px 24px",
          background: "linear-gradient(135deg, #0d0e1a 0%, #0f0f1e 100%)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Background glows */}
        <div style={{ position: "absolute", right: -60, top: -60, width: 200, height: 200, borderRadius: "50%", background: "rgba(6,182,212,0.06)", filter: "blur(40px)", pointerEvents: "none" }} />
        <div style={{ position: "absolute", left: -60, bottom: -60, width: 200, height: 200, borderRadius: "50%", background: "rgba(139,92,246,0.06)", filter: "blur(40px)", pointerEvents: "none" }} />

        <div style={{ display: "flex", flexWrap: "wrap", gap: 16, alignItems: "flex-start", justifyContent: "space-between" }}>
          {/* Left: title block */}
          <div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
              <span className="badge badge-cyan">
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--color-cyan)", animation: "pulse 2s infinite", display: "inline-block" }} />
                CEO OS ACTIVE
              </span>
              <span className="badge badge-emerald">
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--color-emerald)", display: "inline-block" }} />
                {voiceSupported ? "VOICE READY" : "TEXT MODE"}
              </span>
              {activeTasksCount > 0 && (
                <span className="badge badge-amber">
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--color-amber)", animation: "pulse 2s infinite", display: "inline-block" }} />
                  {activeTasksCount} RUNNING
                </span>
              )}
            </div>
            <h1 className="heading-1" style={{ marginBottom: 4 }}>
              Executive AI Console
              <span style={{ color: "var(--color-cyan)", marginLeft: 8, fontSize: "1.2rem" }}>& Voice Control</span>
            </h1>
            <p style={{ fontSize: "0.8125rem", color: "var(--color-text-secondary)", maxWidth: 520 }}>
              Natural language + voice directives. ReAct reasoning. Live macOS tool execution.
              Say <span style={{ color: "var(--color-cyan)", fontFamily: "var(--font-mono)" }}>"Jarvis, open YouTube"</span> and watch it happen.
            </p>
          </div>

          {/* Right: metrics */}
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <div className="metricCard" style={{ minWidth: 90, padding: "10px 16px" }}>
              <div className="metricLabel">Active</div>
              <div className="metricValue" style={{ fontSize: "1.4rem", color: "var(--color-amber)" }}>{activeTaskCount}</div>
            </div>
            <div className="metricCard" style={{ minWidth: 90, padding: "10px 16px" }}>
              <div className="metricLabel">Total</div>
              <div className="metricValue" style={{ fontSize: "1.4rem" }}>{totalTaskCount}</div>
            </div>
            <div className="metricCard" style={{ minWidth: 90, padding: "10px 16px" }}>
              <div className="metricLabel">Success</div>
              <div className="metricValue" style={{ fontSize: "1.4rem", color: "var(--color-emerald)" }}>{successRate}%</div>
            </div>
          </div>
        </div>

        {/* Quick command chips */}
        <div style={{ marginTop: 16, borderTop: "1px solid var(--color-border)", paddingTop: 14 }}>
          <div style={{ fontSize: "0.65rem", fontFamily: "var(--font-mono)", color: "var(--color-text-muted)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 8 }}>
            ⚡ Quick directives (click to execute):
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {QUICK_COMMANDS.map((cmd) => (
              <button
                key={cmd.label}
                type="button"
                onClick={() => void handleSend(cmd.text, cmd.speak)}
                className="chip"
                title={cmd.text}
                disabled={isProcessing}
              >
                {cmd.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Main area: Chat + Task sidebar ─────────────────────────── */}
      <div className="grid-chat">

        {/* ── Chat Column ──────────────────────────────────────────── */}
        <div className="card" style={{ display: "flex", flexDirection: "column", minHeight: 600, maxHeight: 740 }}>
          {/* Chat Header */}
          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "12px 20px",
            borderBottom: "1px solid var(--color-border)",
            background: "rgba(13,14,26,0.6)",
            borderRadius: "var(--radius-xl) var(--radius-xl) 0 0",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              {/* Voice orb (small) */}
              <div className={`orbRing ${voiceOrb}`}>
                <VoiceOrb state={voiceOrb} size={32} />
              </div>
              <div>
                <div style={{ fontSize: "0.8125rem", fontWeight: 600 }}>
                  ReAct Live Conversation
                </div>
                <div style={{ fontSize: "0.65rem", fontFamily: "var(--font-mono)", color: "var(--color-text-muted)" }}>
                  {isListening ? `🎙️ Listening${transcript ? `: "${transcript}"` : "..."}` :
                   voiceOrb === "thinking" ? "🧠 Reasoning..." :
                   voiceOrb === "speaking" ? "🔊 Speaking..." :
                   `${messages.length} messages`}
                </div>
              </div>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <Link href="/jarvis" className="chip" style={{ fontSize: "0.65rem", padding: "2px 8px" }}>
                🎙️ Jarvis Studio →
              </Link>
              <button
                type="button"
                onClick={() => setMessages([buildWelcome()])}
                style={{ fontSize: "0.7rem", color: "var(--color-text-muted)", background: "none", border: "none", cursor: "pointer" }}
              >
                Clear
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="chatFeed">
            {messages.map((msg) => (
              <div key={msg.id} className="fadeIn">
                <ChatBubble message={msg} onSpeak={speakText} />
              </div>
            ))}

            {/* Thinking indicator */}
            {isProcessing && (
              <div className="fadeIn">
                <ThinkingBubble />
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          {/* Input Bar */}
          <div style={{
            borderTop: "1px solid var(--color-border)",
            padding: "12px 16px",
            background: "rgba(7,8,16,0.5)",
            borderRadius: "0 0 var(--radius-xl) var(--radius-xl)",
          }}>
            {/* Skill route preview */}
            {matchedSkill && (
              <div className="skillPreview">
                <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span>🎯 Auto-routing to:</span>
                  <strong style={{ color: "var(--color-purple)" }}>{matchedSkill.name}</strong>
                </span>
                <span style={{ fontWeight: 700 }}>{matchedSkill.score}% match</span>
              </div>
            )}

            <form onSubmit={onSubmit} style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {/* Voice mic button */}
              {voiceSupported && (
                <button
                  type="button"
                  onClick={toggleVoice}
                  className={`btn btn-icon-lg btn-mic ${isListening ? "listening" : ""}`}
                  title={isListening ? "Listening… click to stop" : "Click to speak voice command"}
                  aria-label="Toggle voice input"
                >
                  <span style={{ fontSize: "1.1rem" }}>{isListening ? "⏹" : "🎙️"}</span>
                </button>
              )}

              {/* Text input */}
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                placeholder={
                  isListening
                    ? (transcript ? `"${transcript}"` : "Listening… speak now")
                    : 'Type a directive or say "Jarvis, open YouTube"…'
                }
                className="chatInput"
                style={{ flex: 1, height: 44 }}
                aria-label="Message input"
                disabled={isProcessing}
              />

              {/* Send button */}
              <button
                type="submit"
                disabled={isProcessing || !inputMessage.trim()}
                className="btn btn-primary"
                style={{ height: 44, paddingLeft: 20, paddingRight: 20, flexShrink: 0 }}
                aria-label="Send message"
              >
                {isProcessing ? (
                  <span
                    className="spin"
                    style={{ width: 16, height: 16, borderRadius: "50%", border: "2px solid rgba(0,0,0,0.2)", borderTopColor: "#000", display: "inline-block" }}
                  />
                ) : "Send ↵"}
              </button>
            </form>
          </div>
        </div>

        {/* ── Right Sidebar: Live Tasks + Navigation ──────────────── */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Voice Orb Panel */}
          <div className="card" style={{ padding: 20, textAlign: "center" }}>
            <div style={{ display: "flex", justifyContent: "center", marginBottom: 12 }}>
              <div className={`orbRing ${voiceOrb}`}>
                <VoiceOrb state={voiceOrb} size={80} />
              </div>
            </div>
            <div style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)", marginBottom: 4 }}>
              {voiceOrb === "idle"      && "🟦 Awaiting command"}
              {voiceOrb === "listening" && "🔴 Listening for speech…"}
              {voiceOrb === "thinking"  && "🟣 ReAct reasoning…"}
              {voiceOrb === "speaking"  && "🟢 Jarvis speaking…"}
            </div>
            <div style={{ fontSize: "0.65rem", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)" }}>
              Say "Jarvis, …" for voice
            </div>
            {voiceSupported && (
              <button
                type="button"
                onClick={toggleVoice}
                className={`btn ${isListening ? "btn-danger" : "btn-ghost"}`}
                style={{ marginTop: 12, width: "100%", fontSize: "0.75rem" }}
              >
                {isListening ? "⏹ Stop Listening" : "🎙️ Start Listening"}
              </button>
            )}
          </div>

          {/* Live Tasks Feed */}
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", borderBottom: "1px solid var(--color-border)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: activeTasksCount > 0 ? "var(--color-amber)" : "var(--color-text-muted)", animation: activeTasksCount > 0 ? "pulse 2s infinite" : "none", display: "inline-block" }} />
                <span style={{ fontSize: "0.8125rem", fontWeight: 600 }}>Live Tasks</span>
              </div>
              <Link href="/tasks" className="chip" style={{ fontSize: "0.65rem", padding: "2px 8px" }}>
                All ({totalTaskCount}) →
              </Link>
            </div>

            <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 8, maxHeight: 360, overflowY: "auto" }}>
              {liveTasks.length === 0 ? (
                <div style={{ padding: "24px 0", textAlign: "center", fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                  No tasks yet. Send a directive to begin.
                </div>
              ) : (
                liveTasks.slice(0, 8).map((task) => (
                  <LiveTaskCard key={task.id} task={task} compact />
                ))
              )}
            </div>
          </div>

          {/* Navigation Hub */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {[
              { href: "/jarvis",       icon: "🎙️", label: "Jarvis Studio",     sub: "Gemini Live + Wake-word", accent: "var(--color-cyan)" },
              { href: "/desktop",      icon: "🖥️", label: "CUA Desktop",       sub: "macOS Automation",       accent: "var(--color-purple)" },
              { href: "/agents",       icon: "🧠", label: "Agent Swarm",        sub: "270+ Specialists",       accent: "var(--color-emerald)" },
              { href: "/integrations", icon: "🔌", label: "Integrations",       sub: "MCP + APIs",             accent: "var(--color-blue)" },
            ].map((nav) => (
              <Link key={nav.href} href={nav.href} style={{ textDecoration: "none" }}>
                <div
                  className="card"
                  style={{ padding: "12px 14px", cursor: "pointer", transition: "all var(--transition-fast)" }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = nav.accent + "50"; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = "var(--color-border)"; }}
                >
                  <div style={{ fontSize: "1.1rem", marginBottom: 4 }}>{nav.icon}</div>
                  <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--color-text-primary)" }}>{nav.label}</div>
                  <div style={{ fontSize: "0.65rem", color: "var(--color-text-muted)", fontFamily: "var(--font-mono)", marginTop: 2 }}>{nav.sub}</div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
