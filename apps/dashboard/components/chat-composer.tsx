"use client";

import React, { memo, useEffect, useRef, useState } from "react";
import { VoiceOrb } from "./voice-orb";

interface ChatComposerProps {
  onSendMessage: (text: string, attachments?: string[]) => void;
  isProcessing: boolean;
  isVoiceActive: boolean;
  onToggleVoice: () => void;
  onOpenCommandPalette: () => void;
}

export const ChatComposer = memo(function ChatComposer({
  onSendMessage,
  isProcessing,
  isVoiceActive,
  onToggleVoice,
  onOpenCommandPalette,
}: ChatComposerProps) {
  const [text, setText] = useState("");
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState("Gemini 3.7 Flash");
  const [reasoningLevel, setReasoningLevel] = useState("High (Autonomous)");
  const [executionMode, setExecutionMode] = useState<"ceo" | "jarvis" | "swarm">("ceo");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Auto-grow textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [text]);

  const handleSend = () => {
    if (!text.trim() || isProcessing) return;
    onSendMessage(text.trim());
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickVoiceDirectives = [
    "Find 10 competitors to Suppremo and analyze pricing",
    "Audit AWS cloud spend & FinOps run rate",
    "Jarvis, get system stats",
    "Jarvis, open Spotify",
  ];

  return (
    <div className="chatComposerContainer">
      {/* Quick Voice & Directive Pills */}
      <div className="quickDirectiveRow">
        <span className="quickDirectiveLabel">⚡ Quick Directives:</span>
        {quickVoiceDirectives.map((cmd) => (
          <button
            key={cmd}
            type="button"
            className="quickDirectivePill"
            onClick={() => onSendMessage(cmd)}
            disabled={isProcessing}
          >
            🚀 {cmd}
          </button>
        ))}
      </div>

      {/* Advanced Settings Drawer (Collapsible) */}
      {isAdvancedOpen && (
        <div className="advancedSettingsDrawer">
          <div className="settingItem">
            <span className="settingLabel">Intelligence Engine</span>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="selectSmall"
            >
              <option value="Gemini 3.7 Flash">Gemini 3.7 Flash (Fastest / Multimodal)</option>
              <option value="GPT-5.6 Sol">GPT-5.6 Sol (Deep Reasoning)</option>
              <option value="Claude 3.7 Sonnet">Claude 3.7 Sonnet (Architecture)</option>
              <option value="Deterministic">Deterministic Engine (Local-first / Offline)</option>
            </select>
          </div>

          <div className="settingItem">
            <span className="settingLabel">Reasoning Tier</span>
            <select
              value={reasoningLevel}
              onChange={(e) => setReasoningLevel(e.target.value)}
              className="selectSmall"
            >
              <option value="High (Autonomous)">High (Autonomous Execution)</option>
              <option value="Standard">Standard (Step Confirmation)</option>
              <option value="Direct">Direct / Fast (No Subagents)</option>
            </select>
          </div>

          <div className="settingItem">
            <span className="settingLabel">Execution Mode</span>
            <div className="modePills">
              <button
                type="button"
                className={`modePill ${executionMode === "ceo" ? "active" : ""}`}
                onClick={() => setExecutionMode("ceo")}
              >
                👑 CEO AI
              </button>
              <button
                type="button"
                className={`modePill ${executionMode === "jarvis" ? "active" : ""}`}
                onClick={() => setExecutionMode("jarvis")}
              >
                🤖 Jarvis Voice
              </button>
              <button
                type="button"
                className={`modePill ${executionMode === "swarm" ? "active" : ""}`}
                onClick={() => setExecutionMode("swarm")}
              >
                🐝 Multi-Agent Swarm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Composer Box */}
      <div className={`composerMainBox ${isVoiceActive ? "voiceActiveBorder" : ""}`}>
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            isVoiceActive
              ? "🎙️ Jarvis is listening... Speak your directive or type here..."
              : "Ask CEO OS or say 'Jarvis, open YouTube' (Shift+Enter for newline)..."
          }
          className="composerTextarea"
          disabled={isProcessing}
        />

        <div className="composerBottomBar">
          <div className="composerLeftControls">
            <button
              type="button"
              className="composerIconBtn"
              onClick={() => setIsAdvancedOpen(!isAdvancedOpen)}
              title="Configure Model & Execution Mode"
            >
              ⚙️ <span className="activeModelTag">{selectedModel.split(" ")[0]}</span>
            </button>

            <button
              type="button"
              className="composerIconBtn"
              onClick={onOpenCommandPalette}
              title="Open Command Palette (⌘K)"
            >
              ⌘K
            </button>
          </div>

          <div className="composerRightControls">
            {/* Prominent Jarvis Voice Orb Trigger */}
            <button
              type="button"
              className={`composerVoiceOrbBtn ${isVoiceActive ? "recording" : ""}`}
              onClick={onToggleVoice}
              title={isVoiceActive ? "Stop Voice Listening" : "Start Jarvis Voice Conversation"}
            >
              <div className="orbWrapperSmall">
                <VoiceOrb
                  state={
                    isVoiceActive
                      ? isProcessing
                        ? "thinking"
                        : "listening"
                      : isProcessing
                        ? "thinking"
                        : "idle"
                  }
                  size={32}
                />
              </div>
              <span className="voiceBtnLabel">
                {isVoiceActive ? "Listening..." : "Jarvis Voice"}
              </span>
            </button>

            <button
              type="button"
              className="composerSendBtn"
              onClick={handleSend}
              disabled={!text.trim() || isProcessing}
              title="Send Directive (Enter)"
            >
              {isProcessing ? "⏳" : "↑"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
});
