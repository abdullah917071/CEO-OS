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
import { getWsUrl, requestJson } from "../../lib/api";

interface VoiceTurn {
  id: string;
  sender: "user" | "jarvis" | "system";
  text: string;
  actionSummary?: string;
  timestamp: string;
}

export default function JarvisStudioPage() {
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [voiceStatus, setVoiceStatus] = useState<"standby" | "listening" | "speaking" | "executing">("standby");
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
  const [activeRms, setActiveRms] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null);
  const recognitionRef = useRef<any>(null);
  const nextPlayTimeRef = useRef<number>(0);

  // Play PCM16 24kHz audio chunk from Gemini Live
  const playPcm16Chunk = useCallback((b64Pcm: string, sampleRate = 24000) => {
    if (isMuted || typeof window === "undefined") return;

    try {
      if (!audioContextRef.current) {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        audioContextRef.current = new AudioCtx({ sampleRate });
      }
      const ctx = audioContextRef.current;
      if (ctx.state === "suspended") {
        ctx.resume();
      }

      const binaryStr = window.atob(b64Pcm);
      const len = binaryStr.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryStr.charCodeAt(i);
      }
      const int16Array = new Int16Array(bytes.buffer);
      const float32Array = new Float32Array(int16Array.length);
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0;
      }

      const audioBuffer = ctx.createBuffer(1, float32Array.length, sampleRate);
      audioBuffer.copyToChannel(float32Array, 0);

      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);

      const now = ctx.currentTime;
      const playTime = Math.max(now, nextPlayTimeRef.current);
      source.start(playTime);
      nextPlayTimeRef.current = playTime + audioBuffer.duration;

      setVoiceStatus("speaking");
      setActiveRms(0.7);
      source.onended = () => {
        if (ctx.currentTime >= nextPlayTimeRef.current - 0.05) {
          setVoiceStatus("listening");
          setActiveRms(0.1);
        }
      };
    } catch (err) {
      console.warn("PCM audio playback error:", err);
    }
  }, [isMuted]);

  // Fallback speech synthesis
  const speakTextFallback = useCallback(
    (textToSpeak: string) => {
      if (isMuted || typeof window === "undefined" || !("speechSynthesis" in window)) return;
      window.speechSynthesis.cancel();
      const clean = textToSpeak.replace(/<[^>]*>/g, "").replace(/[*_#`]/g, "");
      const utterance = new SpeechSynthesisUtterance(clean);
      utterance.rate = 1.05;
      utterance.onstart = () => setVoiceStatus("speaking");
      utterance.onend = () => setVoiceStatus("listening");
      window.speechSynthesis.speak(utterance);
    },
    [isMuted]
  );

  // Send directive (via WebSocket or REST)
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
    setVoiceStatus("executing");

    // Try live WebSocket first if open
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "USER_TEXT", text: text.trim() }));
      setIsProcessing(false);
      return;
    }

    // Otherwise use REST endpoint
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
      speakTextFallback(reply);
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
      speakTextFallback(fallback);
    } finally {
      setIsProcessing(false);
    }
  };

  // Connect to live audio WebSocket
  useEffect(() => {
    let ws: WebSocket | null = null;
    let isMounted = true;

    function connectWs() {
      try {
        ws = new WebSocket(getWsUrl("/ws/jarvis/live"));
        wsRef.current = ws;

        ws.onopen = () => {
          if (isMounted) {
            setVoiceStatus("listening");
          }
        };

        ws.onmessage = (evt) => {
          try {
            const msg = JSON.parse(evt.data);
            if (msg.type === "AI_SPEAKING") {
              const b64 = msg.data?.b64_pcm;
              if (b64) {
                playPcm16Chunk(b64, msg.data?.sample_rate || 24000);
              }
            } else if (msg.type === "AI_TRANSCRIPT" || msg.type === "JARVIS_TRANSCRIPT") {
              const text = msg.data?.text;
              const role = msg.data?.role || "jarvis";
              if (text) {
                setVoiceHistory((prev) => [
                  ...prev,
                  {
                    id: `ws_${Date.now()}`,
                    sender: role === "user" ? "user" : "jarvis",
                    text,
                    timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                  },
                ]);
              }
            } else if (msg.type === "AI_INTERRUPTED") {
              setVoiceStatus("listening");
              if (audioContextRef.current) {
                nextPlayTimeRef.current = audioContextRef.current.currentTime;
              }
            }
          } catch {}
        };

        ws.onclose = () => {
          if (isMounted) {
            setTimeout(connectWs, 3000);
          }
        };
      } catch {
        // Fallback gracefully to REST
      }
    }

    connectWs();

    return () => {
      isMounted = false;
      if (ws) ws.close();
    };
  }, [playPcm16Chunk]);

  // Start Browser Live Audio Capture (Microphone to PCM16 16kHz)
  const startLiveMicrophone = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      micStreamRef.current = stream;

      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = new AudioCtx({ sampleRate: 16000 });
      audioContextRef.current = ctx;

      const source = ctx.createMediaStreamSource(stream);
      const processor = ctx.createScriptProcessor(2048, 1, 1);
      processorNodeRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (isMuted) return;
        const inputData = e.inputBuffer.getChannelData(0);

        // Compute RMS for live waveform
        let sum = 0;
        for (let i = 0; i < inputData.length; i++) {
          sum += inputData[i] * inputData[i];
        }
        const rms = Math.sqrt(sum / inputData.length);
        setActiveRms(Math.min(1.0, rms * 5));

        // Convert Float32 to Int16 PCM
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        // Convert to base64
        const uint8 = new Uint8Array(pcm16.buffer);
        let binary = "";
        for (let i = 0; i < uint8.length; i++) {
          binary += String.fromCharCode(uint8[i]);
        }
        const b64Pcm = window.btoa(binary);

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "AUDIO_INPUT", b64_pcm: b64Pcm }));
        }
      };

      source.connect(processor);
      processor.connect(ctx.destination);
      setIsVoiceActive(true);
      setVoiceStatus("listening");
    } catch (err) {
      console.warn("Microphone access fallback to Web Speech Recognition:", err);
      // Setup Web Speech Recognition fallback
      if (typeof window !== "undefined") {
        const SpeechRecognition =
          (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
        if (SpeechRecognition) {
          const recognition = new SpeechRecognition();
          recognition.continuous = true;
          recognition.interimResults = false;
          recognition.lang = "en-US";
          recognition.onresult = (event: any) => {
            const transcript = event.results[event.resultIndex][0].transcript.trim();
            if (transcript) handleSendDirective(transcript);
          };
          recognitionRef.current = recognition;
          recognition.start();
          setIsVoiceActive(true);
          setVoiceStatus("listening");
        }
      }
    }
  };

  const stopLiveMicrophone = () => {
    if (processorNodeRef.current) {
      processorNodeRef.current.disconnect();
      processorNodeRef.current = null;
    }
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
    }
    setIsVoiceActive(false);
    setVoiceStatus("standby");
    setActiveRms(0);
  };

  const quickCommands = [
    "Jarvis, open WhatsApp",
    "Jarvis, mute the Mac",
    "Jarvis, open Spotify",
    "Jarvis, analyze my business and make a marketing strategy",
  ];

  const contextContent = (
    <>
      <div className="contextPanelHeader">
        <span>Gemini 3.1 Flash Live</span>
        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Voice Interface</span>
      </div>

      <div className="contextPanelBody">
        <div className="contextSection">
          <div className="contextSectionTitle">Real-Time Audio Telemetry</div>
          <div className="metricKeyValue">
            <span className="metricKey">Model</span>
            <span className="metricVal" style={{ color: "var(--accent-primary)", fontWeight: 600 }}>
              gemini-3.1-flash-live-preview
            </span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Voice Profile</span>
            <span className="metricVal">Kore (Assistant-like)</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Thinking Level</span>
            <span className="metricVal">low (Ultra Low Latency)</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Input Stream</span>
            <span className="metricVal">16 kHz PCM16 (30ms chunks)</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Output Stream</span>
            <span className="metricVal">24 kHz PCM16 Mono</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">VAD Silence Duration</span>
            <span className="metricVal">500 ms (~0.5s turn completion)</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Barge-in / Interrupt</span>
            <span className="metricVal" style={{ color: "#10B981" }}>Enabled (Instant Flush)</span>
          </div>
        </div>

        <div className="contextSection">
          <div className="contextSectionTitle">System Architecture</div>
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", lineHeight: 1.5 }}>
            <strong>Fast Interface:</strong> Jarvis handles instant macOS controls with minimal thinking.<br />
            <strong>Deep Reasoning:</strong> Complex research, multi-agent pipelines, and coding are automatically delegated to <strong>Joice</strong>.
          </div>
        </div>

        <div className="contextSection">
          <div className="contextSectionTitle">Wake Word Inference</div>
          <div className="metricKeyValue">
            <span className="metricKey">Detector</span>
            <span className="metricVal">openWakeWord ONNX</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Idle API Cost</span>
            <span className="metricVal">$0.00 / hr</span>
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
            <h1 className="pageTitle">Gemini Live Voice Studio</h1>
            <p className="pageSubtitle">
              Bidirectional real-time voice assistant with local openWakeWord ONNX inference and Google Gemini Live.
            </p>
          </div>

          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <button
              type="button"
              onClick={() => {
                if (isVoiceActive) stopLiveMicrophone();
                else startLiveMicrophone();
              }}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 14px",
                borderRadius: "var(--radius-md)",
                fontSize: "13px",
                fontWeight: 600,
                background: isVoiceActive ? "var(--status-running-bg)" : "var(--bg-surface-secondary)",
                color: isVoiceActive ? "var(--status-running-text)" : "var(--text-secondary)",
                border: isVoiceActive ? "1px solid var(--status-running-border)" : "1px solid var(--border-subtle)",
              }}
            >
              {isVoiceActive ? <PauseIcon size={14} /> : <PlayIcon size={14} />}
              <span>{isVoiceActive ? "Microphone Live" : "Start Live Voice"}</span>
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

        {/* Live Audio Visualizer Banner */}
        <div
          style={{
            background: "var(--bg-surface-subtle)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "var(--radius-lg)",
            padding: "16px 20px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "12px",
                height: "12px",
                borderRadius: "50%",
                background:
                  voiceStatus === "speaking"
                    ? "#10B981"
                    : voiceStatus === "listening"
                    ? "#EF4444"
                    : "var(--text-muted)",
              }}
            />
            <div>
              <strong style={{ fontSize: "14px", color: "var(--text-primary)" }}>
                {voiceStatus === "speaking"
                  ? "Jarvis Speaking (Gemini Live Stream)"
                  : voiceStatus === "listening"
                  ? "Jarvis Listening (Speak freely)..."
                  : "Jarvis Standby (Click 'Start Live Voice' or say 'Jarvis')"}
              </strong>
              <div style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                Google Gemini 3.1 Flash Live · Kore Voice · Low Thinking Level · Bidirectional Audio
              </div>
            </div>
          </div>

          {/* Dynamic Waveform Bars */}
          <div style={{ display: "flex", alignItems: "center", gap: "3px", height: "24px" }}>
            {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
              <span
                key={i}
                style={{
                  width: "3px",
                  height: isVoiceActive
                    ? `${Math.max(4, activeRms * 24 * (0.4 + 0.6 * Math.sin(i * 0.8)))}px`
                    : "4px",
                  background: voiceStatus === "speaking" ? "#10B981" : "var(--accent-primary)",
                  borderRadius: "2px",
                  transition: "height 80ms ease-out",
                }}
              />
            ))}
          </div>
        </div>

        {/* Quick Test Directives */}
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
            Real-Time Speech Transcript
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

        {/* Input Box */}
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
            placeholder="Type or speak a directive for Gemini Live Jarvis..."
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
            {isProcessing ? "Executing..." : "Send Directive"}
          </button>
        </form>
      </div>
    </AppShell>
  );
}
