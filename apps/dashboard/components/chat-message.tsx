"use client";

import { useState } from "react";

export interface ToolExecution {
  name: string;
  arguments: Record<string, unknown>;
  output?: unknown;
  status: "pending" | "running" | "done" | "error";
  durationMs?: number;
}

export interface ReActStep {
  step_index: number;
  thought: string;
  tool_call?: { name: string; arguments: Record<string, unknown> } | null;
  tool_response?: { output: unknown } | null;
  duration_ms: number;
}

export interface ChatMessage {
  id: string;
  sender: "user" | "jarvis" | "ceo" | "system" | "action";
  text: string;
  thought?: string;
  evidence?: string[];
  toolCalls?: ToolExecution[];
  steps?: ReActStep[];
  durationMs?: number;
  spokenResponse?: string;
  timestamp: string;
  actionType?: "opened_app" | "opened_url" | "searched" | "system_check" | "tool_exec";
  actionTarget?: string;
  isStreaming?: boolean;
}

interface ChatBubbleProps {
  message: ChatMessage;
  onSpeak?: (text: string) => void;
}

const SENDER_CONFIG = {
  user: {
    label: "You (CEO)",
    avatar: "👤",
    align: "items-end",
    bubble: "bg-gradient-to-br from-cyan-600/90 to-blue-700/90 text-white rounded-br-sm",
    avatarClass: "bg-cyan-700 text-white",
  },
  ceo: {
    label: "CEO AI",
    avatar: "👑",
    align: "items-start",
    bubble: "bg-slate-900/95 border border-cyan-500/30 text-slate-100 rounded-bl-sm",
    avatarClass: "bg-gradient-to-br from-amber-500 to-yellow-600 text-black font-bold",
  },
  jarvis: {
    label: "Jarvis",
    avatar: "🤖",
    align: "items-start",
    bubble: "bg-slate-900/95 border border-slate-700/80 text-slate-100 rounded-bl-sm",
    avatarClass: "bg-slate-800 text-cyan-400",
  },
  system: {
    label: "System",
    avatar: "⚙️",
    align: "items-start",
    bubble: "bg-amber-950/40 border border-amber-700/30 text-amber-200 rounded-bl-sm",
    avatarClass: "bg-amber-900/50 text-amber-400",
  },
  action: {
    label: "Action",
    avatar: "⚡",
    align: "items-start",
    bubble: "bg-emerald-950/40 border border-emerald-700/40 text-emerald-100 rounded-bl-sm",
    avatarClass: "bg-emerald-900/50 text-emerald-400",
  },
};

const ACTION_ICONS: Record<string, string> = {
  opened_app: "🚀",
  opened_url: "🌐",
  searched: "🔍",
  system_check: "💻",
  tool_exec: "⚡",
};

export function ChatBubble({ message, onSpeak }: ChatBubbleProps) {
  const [thoughtExpanded, setThoughtExpanded] = useState(false);
  const [stepsExpanded, setStepsExpanded] = useState(false);

  const config = SENDER_CONFIG[message.sender] || SENDER_CONFIG.ceo;

  // Action confirmation card
  if (message.sender === "action") {
    return (
      <div className="flex items-start gap-2 px-1">
        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-emerald-950/60 border border-emerald-700/40 flex items-center justify-center text-sm">
          {message.actionType ? ACTION_ICONS[message.actionType] : "⚡"}
        </div>
        <div className="flex-1 rounded-xl border border-emerald-700/30 bg-emerald-950/30 px-4 py-2.5 text-xs font-mono">
          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-emerald-300 font-semibold">{message.text}</span>
          </div>
          {message.actionTarget && (
            <div className="mt-1 text-emerald-500/80 text-[11px]">
              Target: {message.actionTarget}
            </div>
          )}
          <div className="mt-1 text-slate-500 text-[10px]">{message.timestamp}</div>
        </div>
      </div>
    );
  }

  const isUser = message.sender === "user";

  return (
    <div className={`flex flex-col gap-1 ${config.align}`}>
      <div className={`flex items-end gap-2 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
        {/* Avatar */}
        <div
          className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-sm ${config.avatarClass}`}
          title={config.label}
        >
          {config.avatar}
        </div>

        {/* Bubble */}
        <div className={`max-w-[82%] rounded-2xl px-4 py-3 shadow-lg ${config.bubble}`}>
          {/* Header */}
          <div className={`flex items-center gap-2 mb-1.5 text-[11px] font-mono opacity-60 ${isUser ? "flex-row-reverse" : ""}`}>
            <span className="font-semibold">{config.label}</span>
            <span>·</span>
            <span>{message.timestamp}</span>
            {message.durationMs && (
              <>
                <span>·</span>
                <span>⚡ {Math.round(message.durationMs)}ms</span>
              </>
            )}
          </div>

          {/* Main text */}
          <div className={`text-sm leading-relaxed whitespace-pre-wrap ${message.isStreaming ? "after:animate-pulse after:content-['▋'] after:ml-0.5" : ""}`}>
            {message.text}
          </div>

          {/* ReAct Thought Trace */}
          {message.thought && (
            <div className="mt-2.5 border-t border-slate-700/50 pt-2">
              <button
                type="button"
                onClick={() => setThoughtExpanded((v) => !v)}
                className="flex items-center gap-1.5 text-[11px] font-mono text-cyan-400/80 hover:text-cyan-300 transition-colors"
              >
                <span>🧠</span>
                <span>ReAct Scratchpad</span>
                <span className="opacity-60">{thoughtExpanded ? "▲" : "▼"}</span>
              </button>
              {thoughtExpanded && (
                <div className="mt-1.5 p-2.5 rounded-lg bg-slate-950/70 border border-cyan-500/15 text-[11px] font-mono text-cyan-300/80 whitespace-pre-wrap leading-relaxed max-h-40 overflow-y-auto">
                  {message.thought}
                </div>
              )}
            </div>
          )}

          {/* Step-by-step trace */}
          {message.steps && message.steps.length > 0 && (
            <div className="mt-2.5 border-t border-slate-700/50 pt-2">
              <button
                type="button"
                onClick={() => setStepsExpanded((v) => !v)}
                className="flex items-center gap-1.5 text-[11px] font-mono text-violet-400/80 hover:text-violet-300 transition-colors"
              >
                <span>📋</span>
                <span>{message.steps.length} Reasoning Steps</span>
                <span className="opacity-60">{stepsExpanded ? "▲" : "▼"}</span>
              </button>
              {stepsExpanded && (
                <div className="mt-1.5 space-y-1.5 max-h-52 overflow-y-auto">
                  {message.steps.map((step, i) => (
                    <div key={i} className="rounded-lg bg-slate-950/70 border border-slate-700/40 p-2 text-[11px] font-mono">
                      <div className="text-violet-400 font-bold mb-0.5">Step {step.step_index + 1} · {step.duration_ms}ms</div>
                      <div className="text-slate-400 line-clamp-2">{step.thought}</div>
                      {step.tool_call && (
                        <div className="mt-1 text-emerald-400">
                          ▶ {step.tool_call.name}({JSON.stringify(step.tool_call.arguments).slice(0, 60)})
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tool Calls */}
          {message.toolCalls && message.toolCalls.length > 0 && (
            <div className="mt-2.5 border-t border-slate-700/50 pt-2 space-y-1.5">
              <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">⚡ Executed:</div>
              {message.toolCalls.map((tool, i) => (
                <div key={i} className="rounded-lg bg-slate-950/70 border border-emerald-500/25 p-2 text-[11px] font-mono">
                  <div className="flex items-center justify-between">
                    <span className="text-emerald-400 font-bold">✓ {tool.name}</span>
                    {tool.durationMs && (
                      <span className="text-slate-500">{tool.durationMs}ms</span>
                    )}
                  </div>
                  {tool.arguments && Object.keys(tool.arguments).length > 0 && (
                    <div className="mt-0.5 text-slate-400 truncate">
                      {JSON.stringify(tool.arguments).slice(0, 80)}
                    </div>
                  )}
                  {tool.output !== undefined && tool.output !== null && (
                    <div className="mt-1 text-slate-300 bg-slate-900/80 p-1 rounded truncate">
                      → {typeof tool.output === "object" ? JSON.stringify(tool.output).slice(0, 100) : String(tool.output).slice(0, 100)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Voice + Actions row */}
          {message.sender === "jarvis" && (
            <div className="mt-2 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => onSpeak && onSpeak(message.spokenResponse || message.text)}
                className="inline-flex items-center gap-1 text-[11px] text-cyan-400/70 hover:text-cyan-300 font-mono transition-colors"
                title="Speak again"
              >
                🔊
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function ThinkingBubble({ text }: { text?: string } = {}) {
  return (
    <div className="flex items-end gap-2">
      <div className="w-7 h-7 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-sm">
        🤖
      </div>
      <div className="max-w-[70%] rounded-2xl rounded-bl-sm bg-slate-900/95 border border-slate-700/80 px-4 py-3 shadow-lg">
        <div className="flex items-center gap-2 text-xs font-mono text-cyan-400">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
          <span className="animate-pulse">{text || "ReAct Reasoning..."}</span>
        </div>
        <div className="mt-1.5 text-[11px] font-mono text-slate-400 animate-pulse">
          Evaluating → Routing → Dispatching → Synthesizing
        </div>
        <div className="mt-2 flex gap-1">
          {[0, 1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-1.5 bg-cyan-500/60 rounded-full animate-pulse"
              style={{
                width: `${20 + Math.random() * 30}px`,
                animationDelay: `${i * 150}ms`,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
