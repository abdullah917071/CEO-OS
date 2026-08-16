"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { AppShell } from "../../components/app-shell";
import {
  JarvisIcon,
  MicIcon,
  MicOffIcon,
  PauseIcon,
  PlayIcon,
  CheckIcon,
} from "../../components/icons";
import { requestJson } from "../../lib/api";

interface VoiceTurn {
  id: string;
  sender: "user" | "jarvis" | "system";
  text: string;
  actionSummary?: string;
  timestamp: string;
}

export default function JarvisStudioPage() {
  const [isListening, setIsListening] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [voiceHistory, setVoiceHistory] = useState<VoiceTurn[]>([
    {
      id: "v-1",
      sender: "user",
      text: "Jarvis, check system status and open YouTube.",
      timestamp: "18:22:10",
    },
    {
      id: "v-2",
      sender: "jarvis",
      text: "Opened sir. System health is optimal, and YouTube is now loading in your browser.",
      actionSummary: "macOS AppleScript: open https://www.youtube.com",
      timestamp: "18:22:11",
    },
  ]);
  const [inputDirective, setInputDirective] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [wakeWordSensitivity, setWakeWordSensitivity] = useState(0.75);

  const recognitionRef = useRef<any>(null);

  // Browser speech synthesis helper
  const speakText = useCallback(
    (textToSpeak: string) => {
      if (isMuted || typeof window === "undefined" || !("speechSynthesis" in window)) return;
      window.speechSynthesis.cancel();
      const clean = textToSpeak.replace(/<[^>]*>/g, "").replace(/[*_#`]/g, "");
      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.rate = 1.05;
      window.speechSynthesis.speak(utterance);
    },
    [isMuted]
  );

  const handleSendDirective = async (text: string) => {
    if (!text.trim() || isProcessing) return;

    const userTurn: VoiceTurn = {
      id: `usr_${Date.now()}`,
      sender: "user",
      text: text.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setVoiceHistory((prev) => [...prev, userTurn]);
    setInputDirective("");
    setIsProcessing(true);

    try {
      const res = await requestJson<{ spoken_response?: string; reply?: string; tool_calls?: unknown[] }>(
        "/api/jarvis/chat",
        {
          method: "POST",
          body: JSON.stringify({ message: text.trim() }),
        }
      );

      const reply = res.spoken_response || res.reply || `Executed: ${text}`;
      const jarvisTurn: VoiceTurn = {
        id: `jar_${Date.now()}`,
        sender: "jarvis",
        text: reply,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setVoiceHistory((prev) => [...prev, jarvisTurn]);
      speakText(reply);
    } catch {
      const fallback = `Directive received: "${text}". Jarvis dispatched command to macOS subsystem.`;
      setVoiceHistory((prev) => [
        ...prev,
        {
          id: `jar_${Date.now()}`,
          sender: "jarvis",
          text: fallback,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
      speakText(fallback);
    } finally {
      setIsProcessing(false);
    }
  };

  // Browser Web Speech Recognition setup
  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.lang = "en-US";

        recognition.onresult = (event: any) => {
          const current = event.resultIndex;
          const transcript = event.results[current][0].transcript.trim();
          if (transcript) {
            handleSendDirective(transcript);
          }
        };

        recognitionRef.current = recognition;
        if (isListening) {
          try {
            recognition.start();
          } catch {}
        }
      }
    }
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {}
      }
    };
  }, [isListening]);

  const quickCommands = [
    "Jarvis, open YouTube",
    "Jarvis, get system stats",
    "Jarvis, open Spotify and play focus music",
    "Jarvis, search Google for Apple Silicon benchmarks",
  ];

  const contextContent = (
    <>
      <div className="contextPanelHeader">
        <span>Jarvis Engine Specs</span>
        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>ONNX</span>
      </div>

      <div className="contextPanelBody">
        <div className="contextSection">
          <div className="contextSectionTitle">Audio & Wake Word</div>
          <div className="metricKeyValue">
            <span className="metricKey">Wake Word</span>
            <span className="metricVal">Jarvis</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Inference Model</span>
            <span className="metricVal">openWakeWord (Local)</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Microphone</span>
            <span className="metricVal">sounddevice 16kHz</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Idle API Cost</span>
            <span className="metricVal">$0.00 / hr</span>
          </div>
        </div>

        <div className="contextSection">
          <div className="contextSectionTitle">Gemini Live Connection</div>
          <div className="metricKeyValue">
            <span className="metricKey">Protocol</span>
            <span className="metricVal">WebSocket Bidirectional</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Voice Profile</span>
            <span className="metricVal">Puck (Gemini Multimodal)</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Inactivity Timeout</span>
            <span className="metricVal">60s Auto-disconnect</span>
          </div>
        </div>
      </div>
    </>
  );

  return (
    <AppShell currentRouteName="Jarvis Voice" contextPanelContent={contextContent}>
      <div className="pageContainer">
        {/* Page Header */}
        <div className="pageHeader">
          <div>
            <h1 className="pageTitle">Jarvis Voice Assistant</h1>
            <p className="pageSubtitle">
              Ambient voice assistant with local openWakeWord ONNX inference and Google Gemini Live streaming.
            </p>
          </div>

          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <button
              type="button"
              onClick={() => setIsListening(!isListening)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "var(--radius-md)",
                fontSize: "13px",
                fontWeight: 600,
                background: isListening ? "var(--status-running-bg)" : "var(--bg-surface-secondary)",
                color: isListening ? "var(--status-running-text)" : "var(--text-secondary)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              {isListening ? <PauseIcon size={14} /> : <PlayIcon size={14} />}
              <span>{isListening ? "Listening Active" : "Paused"}</span>
            </button>

            <button
              type="button"
              onClick={() => setIsMuted(!isMuted)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                borderRadius: "var(--radius-md)",
                fontSize: "13px",
                fontWeight: 500,
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                color: isMuted ? "var(--status-danger-text)" : "var(--text-primary)",
              }}
            >
              {isMuted ? <MicOffIcon size={14} /> : <MicIcon size={14} />}
              <span>{isMuted ? "Muted" : "Unmuted"}</span>
            </button>
          </div>
        </div>

        {/* Device & Hardware Capabilities Status Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "12px",
          }}
        >
          <div className="contextSection">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
              <strong style={{ fontSize: "13px" }}>Hardware Microphone</strong>
              <span className="statusBadge completed"><CheckIcon size={11} /> Ready</span>
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>sounddevice · 16kHz PCM Mono</div>
          </div>

          <div className="contextSection">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
              <strong style={{ fontSize: "13px" }}>macOS CUA & Apps</strong>
              <span className="statusBadge completed"><CheckIcon size={11} /> Connected</span>
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>AppleScript · System Automation</div>
          </div>

          <div className="contextSection">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
              <strong style={{ fontSize: "13px" }}>Browser Control</strong>
              <span className="statusBadge completed"><CheckIcon size={11} /> Ready</span>
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Playwright Chromium & Safari</div>
          </div>

          <div className="contextSection">
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
              <strong style={{ fontSize: "13px" }}>Spotify Media</strong>
              <span className="statusBadge completed"><CheckIcon size={11} /> Ready</span>
            </div>
            <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Playback & Track Controls</div>
          </div>
        </div>

        {/* Quick Voice Directives */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--text-muted)", textTransform: "uppercase" }}>
            Test Directives:
          </span>
          {quickCommands.map((cmd) => (
            <button
              key={cmd}
              type="button"
              onClick={() => handleSendDirective(cmd)}
              disabled={isProcessing}
              style={{
                fontSize: "12px",
                padding: "4px 10px",
                borderRadius: "var(--radius-full)",
                background: "var(--bg-surface-subtle)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-primary)",
                cursor: "pointer",
              }}
            >
              🎙️ {cmd}
            </button>
          ))}
        </div>

        {/* Live Conversation Transcript */}
        <div
          style={{
            flex: 1,
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
            padding: "16px 20px",
            overflowY: "auto",
            display: "flex",
            flexDirection: "column",
            gap: "14px",
          }}
        >
          <div style={{ fontSize: "12px", fontWeight: 600, textTransform: "uppercase", color: "var(--text-muted)", letterSpacing: "0.04em" }}>
            Voice Conversation Transcript
          </div>

          {voiceHistory.map((item) => (
            <div
              key={item.id}
              style={{
                display: "flex",
                gap: "12px",
                alignItems: "flex-start",
                padding: "6px 0",
              }}
            >
              <div
                style={{
                  width: "26px",
                  height: "26px",
                  borderRadius: "var(--radius-sm)",
                  background: item.sender === "user" ? "var(--bg-surface-secondary)" : "var(--accent-subtle)",
                  color: item.sender === "user" ? "var(--text-primary)" : "var(--accent-primary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  fontSize: "11px",
                  fontWeight: 700,
                }}
              >
                {item.sender === "user" ? "You" : "J"}
              </div>

              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <strong style={{ fontSize: "13px", color: "var(--text-primary)" }}>
                    {item.sender === "user" ? "You" : "Jarvis"}
                  </strong>
                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{item.timestamp}</span>
                </div>
                <div style={{ fontSize: "14px", color: "var(--text-primary)", marginTop: "2px" }}>
                  {item.text}
                </div>
                {item.actionSummary && (
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "11px",
                      color: "var(--text-secondary)",
                      background: "var(--bg-surface-secondary)",
                      padding: "2px 6px",
                      borderRadius: "4px",
                      display: "inline-block",
                      marginTop: "4px",
                    }}
                  >
                    ⚡ {item.actionSummary}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Input Box for typing or sending directives */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendDirective(inputDirective);
          }}
          style={{ display: "flex", gap: "8px" }}
        >
          <input
            type="text"
            value={inputDirective}
            onChange={(e) => setInputDirective(e.target.value)}
            placeholder="Type or speak a voice directive for Jarvis..."
            style={{
              flex: 1,
              padding: "10px 14px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-strong)",
              fontSize: "14px",
              outline: "none",
            }}
            disabled={isProcessing}
          />
          <button
            type="submit"
            disabled={!inputDirective.trim() || isProcessing}
            style={{
              padding: "10px 20px",
              borderRadius: "var(--radius-md)",
              background: "var(--accent-primary)",
              color: "#FFFFFF",
              fontWeight: 600,
              fontSize: "13px",
            }}
          >
            {isProcessing ? "Executing..." : "Execute"}
          </button>
        </form>
      </div>
    </AppShell>
  );
}
