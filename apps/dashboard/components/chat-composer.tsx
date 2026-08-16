"use client";

import React, { memo, useEffect, useRef, useState } from "react";

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

  return (
    <div className="chatComposerContainer">
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
                className={`modePill ${executionMode === "ceo" ? "active" : ""}`}
                onClick={() => setExecutionMode("ceo")}
              >
                👑 CEO Mode
              </button>
              <button
                className={`modePill ${executionMode === "jarvis" ? "active" : ""}`}
                onClick={() => setExecutionMode("jarvis")}
              >
                🎙️ Jarvis Voice
              </button>
              <button
                className={`modePill ${executionMode === "swarm" ? "active" : ""}`}
                onClick={() => setExecutionMode("swarm")}
              >
                🐝 Swarm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Composer Box */}
      <div className="composerMainBox">
        <textarea
          ref={textareaRef}
          className="composerTextarea"
          rows={1}
          placeholder="Ask CEO OS anything... (e.g. 'Research competitors to Suppremo and build a landing page')"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isProcessing}
        />

        <div className="composerControlsRow">
          <div className="composerLeftControls">
            <button
              className={`composerIconBtn ${isAdvancedOpen ? "active" : ""}`}
              onClick={() => setIsAdvancedOpen(!isAdvancedOpen)}
              title="Configure Model & Reasoning Settings"
            >
              ⚙️
            </button>
            <button
              className="composerIconBtn"
              onClick={onOpenCommandPalette}
              title="Global Command Center (⌘K)"
            >
              ⌘K
            </button>
            <span className="activeModelTag">
              👑 CEO · {selectedModel.split(" ")[0]} · {reasoningLevel.split(" ")[0]}
            </span>
          </div>

          <div className="composerRightControls">
            <button
              className={`composerVoiceBtn ${isVoiceActive ? "recording" : ""}`}
              onClick={onToggleVoice}
              title={isVoiceActive ? "Stop voice listening" : "Talk to Jarvis (Microphone)"}
            >
              {isVoiceActive ? "🔴 Listening..." : "🎙️"}
            </button>

            <button
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
