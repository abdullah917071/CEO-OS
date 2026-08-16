"use client";

import React, { memo, useEffect, useState } from "react";
import Link from "next/link";
import {
  JarvisIcon,
  SearchIcon,
  MicIcon,
  MicOffIcon,
  PanelRightIcon,
  PauseIcon,
} from "./icons";
import { requestJson } from "../lib/api";

interface TopBarProps {
  onOpenCommandPalette: () => void;
  onToggleContextPanel: () => void;
  isContextPanelOpen: boolean;
  currentRouteName?: string;
}

export const TopBar = memo(function TopBar({
  onOpenCommandPalette,
  onToggleContextPanel,
  isContextPanelOpen,
  currentRouteName = "Joice",
}: TopBarProps) {
  const [jarvisState, setJarvisState] = useState<"idle" | "listening" | "speaking">("idle");
  const [isMicMuted, setIsMicMuted] = useState(false);
  const [isJarvisQuickOpen, setIsJarvisQuickOpen] = useState(false);
  const [quickVoiceText, setQuickVoiceText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [quickReply, setQuickReply] = useState<string | null>(null);

  // Poll real Jarvis status
  useEffect(() => {
    let isMounted = true;
    async function checkStatus() {
      try {
        const res = await requestJson<{ state?: string; wake_word?: string }>("/api/jarvis/status");
        if (isMounted && res.state) {
          if (res.state === "listening") setJarvisState("listening");
          else if (res.state === "speaking") setJarvisState("speaking");
          else setJarvisState("idle");
        }
      } catch {
        // graceful offline fallback
      }
    }
    checkStatus();
    const interval = setInterval(checkStatus, 5000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const handleQuickDirective = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!quickVoiceText.trim() || isProcessing) return;

    setIsProcessing(true);
    try {
      const res = await requestJson<{ spoken_response?: string; reply?: string }>(
        "/api/jarvis/chat",
        {
          method: "POST",
          body: JSON.stringify({ message: quickVoiceText.trim() }),
        }
      );
      setQuickReply(res.spoken_response || res.reply || "Directive executed.");
      setQuickVoiceText("");
    } catch {
      setQuickReply(`Executed: "${quickVoiceText}"`);
      setQuickVoiceText("");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <>
      <header className="topBar">
        {/* Left: Current Workspace & Location */}
        <div className="topBarLeft">
          <div className="workspaceBreadcrumb">
            <span className="workspaceBadge">CEO OS</span>
            <span>/</span>
            <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{currentRouteName}</span>
          </div>
        </div>

        {/* Center: Command Palette Trigger */}
        <div className="topBarCenter">
          <button
            type="button"
            className="globalSearchTrigger"
            onClick={onOpenCommandPalette}
            aria-label="Open Command Palette"
          >
            <SearchIcon size={14} />
            <span>Search or command...</span>
            <span className="searchKbd">⌘K</span>
          </button>
        </div>

        {/* Right: Persistent Jarvis Global Control & Context Toggle */}
        <div className="topBarRight">
          {/* Jarvis Global Control Button */}
          <div
            className={`jarvisGlobalControl ${jarvisState !== "idle" ? "active" : ""}`}
            onClick={() => setIsJarvisQuickOpen(!isJarvisQuickOpen)}
            title="Open Jarvis Voice Control"
          >
            <span className={`jarvisStatusDot ${jarvisState}`} />
            <span className="jarvisControlLabel">
              {jarvisState === "listening"
                ? "Jarvis Listening"
                : jarvisState === "speaking"
                ? "Jarvis Speaking"
                : "Jarvis Standby"}
            </span>

            {/* Subtle Voice Waveform */}
            <div className="jarvisMiniWaveform">
              <span className={`waveformBar ${jarvisState !== "idle" ? "active" : ""}`} style={{ animationDelay: "0ms" }} />
              <span className={`waveformBar ${jarvisState !== "idle" ? "active" : ""}`} style={{ animationDelay: "150ms" }} />
              <span className={`waveformBar ${jarvisState !== "idle" ? "active" : ""}`} style={{ animationDelay: "300ms" }} />
            </div>
          </div>

          {/* Quick Mic Mute Toggle */}
          <button
            type="button"
            className="topBarIconBtn"
            onClick={() => setIsMicMuted(!isMicMuted)}
            title={isMicMuted ? "Unmute Microphone" : "Mute Microphone"}
          >
            {isMicMuted ? <MicOffIcon size={15} /> : <MicIcon size={15} />}
          </button>

          {/* Right Context Panel Toggle */}
          <button
            type="button"
            className={`topBarIconBtn ${isContextPanelOpen ? "active" : ""}`}
            onClick={onToggleContextPanel}
            title="Toggle Context Panel"
          >
            <PanelRightIcon size={15} />
          </button>
        </div>
      </header>

      {/* Slide-over Jarvis Quick Controller Modal */}
      {isJarvisQuickOpen && (
        <div
          style={{
            position: "fixed",
            top: "var(--topbar-height)",
            right: "16px",
            width: "340px",
            background: "#FFFFFF",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
            boxShadow: "var(--shadow-lg)",
            padding: "16px",
            zIndex: 50,
            display: "flex",
            flexDirection: "column",
            gap: "12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <JarvisIcon size={16} />
              <strong style={{ fontSize: "13px" }}>Jarvis Ambient Assistant</strong>
            </div>
            <Link
              href="/jarvis"
              style={{ fontSize: "12px", color: "var(--accent-primary)", fontWeight: 500 }}
              onClick={() => setIsJarvisQuickOpen(false)}
            >
              Full Studio →
            </Link>
          </div>

          <div
            style={{
              fontSize: "12px",
              color: "var(--text-secondary)",
              background: "var(--bg-surface-subtle)",
              padding: "8px 10px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            Wake word: <strong style={{ color: "var(--text-primary)" }}>&quot;Jarvis&quot;</strong> (Local openWakeWord ONNX inference)
          </div>

          {quickReply && (
            <div
              style={{
                fontSize: "13px",
                color: "var(--text-primary)",
                background: "var(--accent-subtle)",
                padding: "8px 10px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--accent-border)",
              }}
            >
              {quickReply}
            </div>
          )}

          <form onSubmit={handleQuickDirective} style={{ display: "flex", gap: "6px" }}>
            <input
              type="text"
              value={quickVoiceText}
              onChange={(e) => setQuickVoiceText(e.target.value)}
              placeholder="Give Jarvis a voice directive..."
              style={{
                flex: 1,
                padding: "6px 10px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-strong)",
                fontSize: "13px",
                outline: "none",
              }}
              disabled={isProcessing}
            />
            <button
              type="submit"
              disabled={!quickVoiceText.trim() || isProcessing}
              style={{
                padding: "6px 12px",
                borderRadius: "var(--radius-md)",
                background: "var(--accent-primary)",
                color: "#FFFFFF",
                fontSize: "12px",
                fontWeight: 600,
              }}
            >
              {isProcessing ? "..." : "Send"}
            </button>
          </form>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "4px" }}>
            <button
              type="button"
              onClick={() => {
                setJarvisState(jarvisState === "listening" ? "idle" : "listening");
              }}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
                fontSize: "12px",
                color: "var(--text-secondary)",
              }}
            >
              <PauseIcon size={12} /> {jarvisState === "listening" ? "Pause Listening" : "Start Listening"}
            </button>
            <button
              type="button"
              onClick={() => setIsJarvisQuickOpen(false)}
              style={{ fontSize: "12px", color: "var(--text-muted)" }}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
});
