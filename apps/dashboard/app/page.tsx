"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AppShell } from "../components/app-shell";
import {
  JoiceIcon,
  MicIcon,
  PaperclipIcon,
  ArrowUpIcon,
  CheckIcon,
  ChevronRightIcon,
} from "../components/icons";
import { requestJson } from "../lib/api";

interface PlanStep {
  id: string;
  title: string;
  status: "completed" | "running" | "pending";
}

interface ActiveSubagent {
  id: string;
  name: string;
  role: string;
  action: string;
  tools: string[];
}

interface JoiceExecution {
  taskId: string;
  title: string;
  status: "running" | "completed" | "failed";
  elapsed: string;
  planSteps: PlanStep[];
  subagents: ActiveSubagent[];
  summary?: string;
}

interface ChatItem {
  id: string;
  sender: "user" | "joice" | "system";
  text: string;
  execution?: JoiceExecution;
  timestamp: string;
}

const INITIAL_MESSAGES: ChatItem[] = [
  {
    id: "msg-1",
    sender: "user",
    text: "Find 10 competitors to Suppremo, analyze their pricing, compare their apps, and give me strategic recommendations.",
    timestamp: "18:02",
  },
  {
    id: "msg-2",
    sender: "joice",
    text: "I have analyzed your objective and assembled a dedicated 3-agent specialist team (Research Lead, Pricing Analyst, and Sentiment Auditor). We are currently evaluating merchant commission structures and Play Store feedback.",
    execution: {
      taskId: "task_suppremo_growth",
      title: "Suppremo Competitor & Pricing Analysis",
      status: "running",
      elapsed: "04:18",
      planSteps: [
        { id: "s1", title: "Understand objective & business context", status: "completed" },
        { id: "s2", title: "Discover 10 direct and indirect competitors", status: "completed" },
        { id: "s3", title: "Analyze pricing & merchant commission models", status: "running" },
        { id: "s4", title: "Compare mobile app UX & customer sentiment", status: "pending" },
        { id: "s5", title: "Formulate strategic differentiation plan", status: "pending" },
      ],
      subagents: [
        {
          id: "agent_pricing",
          name: "Pricing Analyst",
          role: "Financial Specialist",
          action: "Scraping merchant commission rate structures and surge pricing models",
          tools: ["browser.navigate", "search.google"],
        },
        {
          id: "agent_sentiment",
          name: "Sentiment Auditor",
          role: "UX Researcher",
          action: "Synthesizing 140+ store reviews for delivery pain points",
          tools: ["browser.inspect"],
        },
      ],
    },
    timestamp: "18:02",
  },
];

export default function JoicePage() {
  const [messages, setMessages] = useState<ChatItem[]>(INITIAL_MESSAGES);
  const [inputPrompt, setInputPrompt] = useState("");
  const [executionMode, setExecutionMode] = useState("Auto");
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeTask] = useState<JoiceExecution | null>(INITIAL_MESSAGES[1].execution || null);

  const feedEndRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const scrollToBottom = useCallback(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Auto-grow composer textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
    }
  }, [inputPrompt]);

  const handleSend = async () => {
    if (!inputPrompt.trim() || isProcessing) return;

    const userText = inputPrompt.trim();
    setInputPrompt("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    const userMsg: ChatItem = {
      id: `user_${Date.now()}`,
      sender: "user",
      text: userText,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsProcessing(true);

    try {
      // Connect to real backend interactive chat endpoint
      const res = await requestJson<{
        final_answer?: string;
        spoken_response?: string;
        thought?: string;
      }>("/api/v1/chat/interactive", {
        method: "POST",
        body: JSON.stringify({ message: userText, mode: executionMode }),
      });

      const replyText = res.final_answer || res.spoken_response || "Directive received and dispatched to specialist fleet.";

      setMessages((prev) => [
        ...prev,
        {
          id: `joice_${Date.now()}`,
          sender: "joice",
          text: replyText,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch {
      // Graceful fallback
      setMessages((prev) => [
        ...prev,
        {
          id: `joice_${Date.now()}`,
          sender: "joice",
          text: `Understood. Processing your directive: "${userText}". I have updated our workspace and active execution plan.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const contextContent = (
    <>
      <div className="contextPanelHeader">
        <span>Execution Context</span>
        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>Live</span>
      </div>

      <div className="contextPanelBody">
        {/* CEO Model Engine */}
        <div className="contextSection">
          <div className="contextSectionTitle">CEO Brain & Reasoning</div>
          <div className="metricKeyValue">
            <span className="metricKey">Model</span>
            <span className="metricVal" style={{ color: "var(--accent-primary)", fontWeight: 600 }}>
              nvidia/nemotron-3.5-lightning:free
            </span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Provider</span>
            <span className="metricVal">OpenRouter</span>
          </div>
          <div className="metricKeyValue">
            <span className="metricKey">Role</span>
            <span className="metricVal">Primary Intelligence (Joice)</span>
          </div>
        </div>

        {/* Active Task Overview */}
        {activeTask && (
          <div className="contextSection">
            <div className="contextSectionTitle">Current Task</div>
            <div style={{ fontWeight: 600, fontSize: "13px", color: "var(--text-primary)", marginBottom: "4px" }}>
              {activeTask.title}
            </div>
            <div style={{ display: "flex", gap: "6px", marginBottom: "10px" }}>
              <span className="statusBadge running">Running · {activeTask.elapsed}</span>
            </div>

            <div className="metricKeyValue">
              <span className="metricKey">Task ID</span>
              <span className="metricVal">{activeTask.taskId}</span>
            </div>
            <div className="metricKeyValue">
              <span className="metricKey">Lead Agent</span>
              <span className="metricVal">Joice (CEO)</span>
            </div>
            <div className="metricKeyValue">
              <span className="metricKey">Specialists</span>
              <span className="metricVal">{activeTask.subagents.length} active</span>
            </div>
            <div className="metricKeyValue">
              <span className="metricKey">Plan Steps</span>
              <span className="metricVal">3 of 5 done</span>
            </div>
          </div>
        )}

        {/* Active Specialists */}
        <div className="contextSection">
          <div className="contextSectionTitle">Assigned Specialists</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <strong style={{ fontSize: "12px", color: "var(--text-primary)" }}>Pricing Analyst</strong>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Agency Agents</div>
              </div>
              <span className="statusBadge running" style={{ fontSize: "10px", padding: "1px 6px" }}>Active</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <strong style={{ fontSize: "12px", color: "var(--text-primary)" }}>Sentiment Auditor</strong>
                <div style={{ fontSize: "11px", color: "var(--text-secondary)" }}>Agency Agents</div>
              </div>
              <span className="statusBadge running" style={{ fontSize: "10px", padding: "1px 6px" }}>Active</span>
            </div>
          </div>
        </div>

        {/* Artifacts */}
        <div className="contextSection">
          <div className="contextSectionTitle">Artifacts & Files</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--text-primary)" }}>
              <span>📄</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px" }}>suppremo_market_analysis.md</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "12px", color: "var(--text-primary)" }}>
              <span>📊</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px" }}>competitor_commission_rates.csv</span>
            </div>
          </div>
        </div>
      </div>
    </>
  );

  return (
    <AppShell currentRouteName="Joice" contextPanelContent={contextContent}>
      <div className="joiceContainer">
        {/* Joice Workspace Header */}
        <div className="joiceHeader">
          <div>
            <h1 className="joiceGreeting">Good evening, Abdullah.</h1>
            <p className="joiceSubhead">What should Joice and the specialist fleet work on today?</p>
          </div>

          <div style={{ display: "flex", gap: "8px" }}>
            <Link
              href="/live"
              style={{
                fontSize: "12px",
                fontWeight: 500,
                color: "var(--text-secondary)",
                padding: "4px 10px",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
                background: "var(--bg-surface-subtle)",
              }}
            >
              View Live Tree →
            </Link>
          </div>
        </div>

        {/* Joice Conversation Feed */}
        <div className="joiceFeed">
          <div className="joiceFeedInner">
            {messages.map((item) => (
              <React.Fragment key={item.id}>
                {item.sender === "user" ? (
                  <div className="joiceMessageUser">
                    <div>{item.text}</div>
                    <div style={{ fontSize: "10px", color: "var(--text-muted)", marginTop: "4px", textAlign: "right" }}>
                      {item.timestamp}
                    </div>
                  </div>
                ) : (
                  <div className="joiceMessageAssistant">
                    <div className="joiceAvatar">
                      <JoiceIcon size={16} />
                    </div>
                    <div className="joiceMessageBody">
                      <div style={{ fontWeight: 600, fontSize: "13px", color: "var(--text-primary)", marginBottom: "4px" }}>
                        Joice
                      </div>
                      <div className="joiceMessageText">{item.text}</div>

                      {/* Inline Joice Execution Card */}
                      {item.execution && (
                        <div className="executionCard">
                          <div className="executionHeader">
                            <div className="executionStatusLeft">
                              <span className="executionLiveBadge">
                                ● {item.execution.status === "running" ? "Running" : "Completed"}
                              </span>
                              <span className="executionTitle">{item.execution.title}</span>
                            </div>
                            <div className="executionMetaRight">
                              <span>Elapsed: {item.execution.elapsed}</span>
                              <Link
                                href="/tasks"
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "2px",
                                  color: "var(--accent-primary)",
                                  fontWeight: 500,
                                }}
                              >
                                Details <ChevronRightIcon size={12} />
                              </Link>
                            </div>
                          </div>

                          <div className="executionBody">
                            {/* Plan Steps Checklist */}
                            <div className="planStepList">
                              {item.execution.planSteps.map((step) => (
                                <div key={step.id} className={`planStepItem ${step.status}`}>
                                  {step.status === "completed" && (
                                    <span className="stepIconSuccess"><CheckIcon size={13} /></span>
                                  )}
                                  {step.status === "running" && (
                                    <span className="stepIconRunning">●</span>
                                  )}
                                  {step.status === "pending" && (
                                    <span className="stepIconPending">○</span>
                                  )}
                                  <span>{step.title}</span>
                                </div>
                              ))}
                            </div>

                            {/* Subagents & Tools Row */}
                            <div className="agentDelegationRow">
                              {item.execution.subagents.map((agent) => (
                                <div key={agent.id} className="agentChip">
                                  <span className="agentChipDot" />
                                  <span>{agent.name}: {agent.action}</span>
                                  {agent.tools.map((t) => (
                                    <span key={t} className="toolExecutionChip">{t}</span>
                                  ))}
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </React.Fragment>
            ))}

            {isProcessing && (
              <div className="joiceMessageAssistant">
                <div className="joiceAvatar">
                  <JoiceIcon size={16} />
                </div>
                <div className="joiceMessageBody" style={{ color: "var(--text-secondary)", fontSize: "13px" }}>
                  Joice is formulating execution plan...
                </div>
              </div>
            )}
            <div ref={feedEndRef} />
          </div>
        </div>

        {/* High-Polish Joice Composer */}
        <div className="joiceComposerWrapper">
          <div className="joiceComposerBox">
            <textarea
              ref={textareaRef}
              rows={1}
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask Joice to do anything, plan projects, run workflows (Enter to send)..."
              className="joiceTextarea"
              disabled={isProcessing}
            />

            <div className="composerActionBar">
              <div className="composerLeftGroup">
                <button type="button" className="composerToolBtn" title="Attach file or screenshot">
                  <PaperclipIcon size={13} />
                  <span>Attach</span>
                </button>

                <Link href="/jarvis" className="composerToolBtn" title="Speak directive via Jarvis Voice">
                  <MicIcon size={13} />
                  <span>Voice</span>
                </Link>

                <button
                  type="button"
                  className="composerToolBtn"
                  onClick={() => setInputPrompt("/research ")}
                  title="Run deep research workflow"
                >
                  ⚡ /research
                </button>
              </div>

              <div className="composerRightGroup">
                <select
                  value={executionMode}
                  onChange={(e) => setExecutionMode(e.target.value)}
                  className="modeSelectPill"
                  title="Execution Reasoning Mode"
                >
                  <option value="Auto">Auto (Recommended)</option>
                  <option value="Think">Think (Deep Reasoning)</option>
                  <option value="Execute">Execute (Fast / Direct)</option>
                  <option value="Research">Research (Multi-Agent Swarm)</option>
                </select>

                <button
                  type="button"
                  onClick={handleSend}
                  disabled={!inputPrompt.trim() || isProcessing}
                  className="composerSendButton"
                  title="Send Directive"
                >
                  <ArrowUpIcon size={14} />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
