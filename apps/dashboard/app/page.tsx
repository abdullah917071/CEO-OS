"use client";

/**
 * CEO OS — Chat-Centric Mission Control Dashboard
 *
 * Primary interaction model: One unified conversation with real-time autonomous execution
 * visible directly inside the chat feed.
 */

import React, { memo, useCallback, useEffect, useRef, useState } from "react";
import { ChatBubble, ThinkingBubble } from "../components/chat-message";
import type { ChatMessage } from "../components/chat-message";
import { LiveTaskCard } from "../components/live-task-card";
import type { LiveTask } from "../components/live-task-card";
import { ChatComposer } from "../components/chat-composer";
import { ChatSidebar } from "../components/chat-shell";
import { ContextPanel } from "../components/context-panel";
import type { ContextPanelData } from "../components/context-panel";
import { CommandPalette } from "../components/command-palette";
import { TaskSwitcher } from "../components/task-switcher";
import type { RunningTaskItem } from "../components/task-switcher";
import { requestJson, WS } from "../lib/api";
import type {
  AgentActiveMember,
  ArtifactCardData,
  ConversationItem,
  InteractiveChatResponse,
  Task,
} from "../lib/contracts";

/* ─── Initial Demo Conversation & Tasks ────────────────────────────────────── */
const INITIAL_CONVERSATIONS: ConversationItem[] = [
  {
    id: "conv-suppremo-1",
    title: "Suppremo Competitor & Market Research",
    preview: "11 competitors analyzed, pricing models compared...",
    updatedAt: "Just now",
    category: "today",
    status: "running",
  },
  {
    id: "conv-landing-2",
    title: "Build Responsive Landing Page",
    preview: "React + Tailwind hero section generated...",
    updatedAt: "2h ago",
    category: "today",
    status: "completed",
  },
  {
    id: "conv-ads-3",
    title: "Analyze Google Ads Spend",
    preview: "Cost per acquisition anomaly detected...",
    updatedAt: "Yesterday",
    category: "yesterday",
    status: "completed",
  },
  {
    id: "conv-backend-4",
    title: "Fix CEO OS Backend Router",
    preview: "Universal router registered with 270+ agents...",
    updatedAt: "3 days ago",
    category: "previous_7_days",
    status: "completed",
  },
  {
    id: "conv-flights-5",
    title: "Research Flight & Hotel Rates",
    preview: "Checked Google Flights and Expedia API...",
    updatedAt: "2 weeks ago",
    category: "older",
    status: "completed",
  },
];

const INITIAL_TASK: LiveTask = {
  id: "task_suppremo_growth",
  title: "Suppremo Growth & Competitor Analysis",
  objective: "Find 10 competitors to Suppremo, analyze their pricing, compare their apps, and formulate differentiated strategic recommendations.",
  status: "running",
  progress: 78,
  currentStep: "Analyzing competitor pricing models & commission structures",
  previousStep: "Found 11 food & delivery competitors",
  nextStep: "Review customer sentiment and Play Store feedback",
  elapsedTime: "08:42",
  agentMembers: [
    {
      id: "agent_res_lead",
      name: "Research Lead",
      role: "Lead Strategist",
      status: "working",
      currentAction: "Coordinating parallel competitor discovery across web & Play Store.",
      toolsUsed: ["agent.search", "memory.search"],
      progress: 90,
      lastOutput: "Identified Zomato, Swiggy, EatClub, MagicPin, Zepto, Blinkit as direct delivery competitors.",
    },
    {
      id: "agent_pricing_analyst",
      name: "Pricing Analyst",
      role: "Financial Specialist",
      status: "working",
      currentAction: "Scraping merchant commission rate structures and surge pricing models.",
      toolsUsed: ["browser.navigate", "search.google"],
      progress: 75,
      lastOutput: "Average industry merchant take-rate: 18-24% + delivery fee. Opportunity for flat-rate subscription model.",
    },
    {
      id: "agent_review_eval",
      name: "Sentiment Auditor",
      role: "UX Researcher",
      status: "working",
      currentAction: "Synthesizing 140+ recent store reviews for delivery pain points.",
      toolsUsed: ["browser.inspect"],
      progress: 60,
      lastOutput: "Key customer complaint across competitors: hidden platform charges and delayed refund resolution.",
    },
  ],
  toolChips: [
    {
      id: "tool_1",
      type: "browser",
      title: "Visiting swiggy.com/partner",
      status: "running",
      input: "URL: https://www.swiggy.com/partner-with-us",
      result: "Extracted merchant onboarding commission tiers (22% base).",
      durationMs: 420,
    },
    {
      id: "tool_2",
      type: "search",
      title: "Google: 'food delivery commission India 2026'",
      status: "success",
      input: "query: food delivery merchant commission India 2026",
      result: "Top 5 industry reports indexed.",
      durationMs: 280,
    },
    {
      id: "tool_3",
      type: "memory",
      title: "Retrieved 5 Suppremo strategic notes",
      status: "success",
      input: "subject: Suppremo business model & margin goals",
      result: "Found note on 12% target operating margin.",
      durationMs: 85,
    },
    {
      id: "tool_4",
      type: "computer",
      title: "macOS CUA: Chrome active",
      status: "success",
      input: "focus application: Google Chrome",
      result: "Window focused, viewport 1920x1080.",
      durationMs: 140,
    },
  ],
  events: [
    {
      id: "evt_1",
      taskId: "task_suppremo_growth",
      timestamp: "18:02:10",
      source: "ceo",
      status: "success",
      title: "Objective analyzed and execution plan decomposed",
      summary: "CEO formulated 6-step staged research strategy.",
    },
    {
      id: "evt_2",
      taskId: "task_suppremo_growth",
      timestamp: "18:02:12",
      source: "router",
      status: "success",
      title: "Dynamic router assembled specialist team",
      summary: "Selected Research Lead, Pricing Analyst, and Sentiment Auditor.",
    },
    {
      id: "evt_3",
      taskId: "task_suppremo_growth",
      timestamp: "18:03:45",
      source: "browser",
      status: "success",
      title: "Navigated to Zomato & Swiggy partner portals",
      summary: "Extracted merchant pricing data.",
    },
    {
      id: "evt_4",
      taskId: "task_suppremo_growth",
      timestamp: "18:06:20",
      source: "agent",
      status: "running",
      title: "Pricing Analyst comparing delivery fee breakdown",
      summary: "Computing average order value margins.",
    },
  ],
  planSteps: [
    { id: "p1", title: "Understand objective & business context", status: "completed" },
    { id: "p2", title: "Discover 10 direct and indirect competitors", status: "completed" },
    { id: "p3", title: "Analyze pricing & merchant commission models", status: "in_progress" },
    { id: "p4", title: "Compare mobile app UX & customer sentiment", status: "pending" },
    { id: "p5", title: "Formulate strategic differentiation plan", status: "pending" },
    { id: "p6", title: "Generate CEO executive report", status: "pending" },
  ],
  computerState: {
    activeApp: "Google Chrome",
    action: "Extracting merchant fee schedule",
    screenshotUrl: "",
  },
  browserState: {
    currentUrl: "https://www.swiggy.com/partner-with-us",
    pagesCount: 12,
    visitedDomains: ["zomato.com", "swiggy.com", "eatclub.in", "magicpin.in", "zeptonow.com"],
  },
};

export default function MissionControlPage() {
  const [conversations, setConversations] = useState<ConversationItem[]>(INITIAL_CONVERSATIONS);
  const [activeConvId, setActiveConvId] = useState<string>("conv-suppremo-1");

  // Messages in active conversation
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "msg-1",
      sender: "user",
      text: "Find 10 competitors to Suppremo, analyze their pricing, compare their apps, and give me recommendations.",
      timestamp: "18:02",
    },
    {
      id: "msg-2",
      sender: "ceo",
      text: "I am on it. I have analyzed your objective, selected the optimal research workflow via our Agent Router, and spawned 3 specialist agents to execute this in parallel.",
      thought: "Formulated multi-agent research team. Bound Browser, Search, and Memory capabilities with least-privilege scoping.",
      timestamp: "18:02",
    },
  ]);

  // Live Task State inside conversation
  const [activeLiveTask, setActiveLiveTask] = useState<LiveTask | null>(INITIAL_TASK);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isVoiceActive, setIsVoiceActive] = useState(false);

  // Contextual Right Panel State
  const [isContextOpen, setIsContextOpen] = useState(true);
  const [contextData, setContextData] = useState<ContextPanelData>({
    mode: "default",
    taskOverview: {
      taskId: "task_suppremo_growth",
      title: "Suppremo Growth Research",
      status: "Running",
      progress: 78,
      agentCount: 3,
      toolCount: 6,
      actionsCount: 27,
      elapsed: "08:42",
      model: "Gemini 3.7 Flash",
      reasoning: "High",
      cost: "₹2.38",
      tokens: "28.4k",
    },
  });

  // Command Palette & Running Tasks
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll chat
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, activeLiveTask, scrollToBottom]);

  // Handle sending a directive
  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

    const userMsgId = `user_${Date.now()}`;
    const newMsg: ChatMessage = {
      id: userMsgId,
      sender: "user",
      text: text.trim(),
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, newMsg]);
    setIsProcessing(true);

    // If text mentions Jarvis or voice action
    const isJarvisDirective = text.toLowerCase().includes("jarvis");

    try {
      if (isJarvisDirective) {
        // Execute voice directive via Jarvis chat endpoint
        const res = await requestJson<{ spoken_response?: string; reply?: string; tool_calls?: unknown[] }>(
          "/api/jarvis/chat",
          {
            method: "POST",
            body: JSON.stringify({ message: text.trim() }),
          }
        );

        const reply = res.spoken_response || res.reply || `Executed: ${text}`;
        setMessages((prev) => [
          ...prev,
          {
            id: `jarvis_${Date.now()}`,
            sender: "jarvis",
            text: reply,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ]);
      } else {
        // Execute CEO AI task
        const res = await requestJson<InteractiveChatResponse>("/api/v1/chat/interactive", {
          method: "POST",
          body: JSON.stringify({ message: text.trim(), task_id: `task_${Date.now()}` }),
        });

        const replyText = res.final_answer || res.spoken_response || "Directive received and executed.";
        setMessages((prev) => [
          ...prev,
          {
            id: `ceo_${Date.now()}`,
            sender: "ceo",
            text: replyText,
            thought: res.thought,
            evidence: res.evidence,
            timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          },
        ]);
      }
    } catch (err) {
      console.warn("Backend chat request fallback:", err);
      // Clean fallback response
      setMessages((prev) => [
        ...prev,
        {
          id: `ceo_${Date.now()}`,
          sender: "ceo",
          text: `Understood. Processing your directive: "${text}". I have assigned the relevant specialist agents.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setIsProcessing(false);
    }
  };

  // Inspecting agent in right panel
  const handleSelectAgent = (agent: AgentActiveMember) => {
    setContextData({
      mode: "agent",
      agent,
    });
    setIsContextOpen(true);
  };

  // Inspecting browser in right panel
  const handleSelectBrowser = () => {
    setContextData({
      mode: "browser",
      browser: {
        currentUrl: activeLiveTask?.browserState?.currentUrl || "https://www.google.com",
        visitedPages: [
          { url: "https://www.zomato.com/partner", title: "Zomato For Enterprise", status: "visited" },
          { url: "https://www.swiggy.com/partner-with-us", title: "Swiggy Partner Onboarding", status: "current" },
          { url: "https://eatclub.in", title: "EatClub Superfast Food", status: "visited" },
          { url: "https://magicpin.in/merchant", title: "Magicpin Merchant Hub", status: "pending" },
        ],
        extractedSummary: "Extracted tiered commission models (18-24%) across major aggregator platforms.",
      },
    });
    setIsContextOpen(true);
  };

  // Inspecting computer control in right panel
  const handleSelectComputer = () => {
    setContextData({
      mode: "computer",
      computer: {
        activeApp: activeLiveTask?.computerState?.activeApp || "Google Chrome",
        action: activeLiveTask?.computerState?.action || "Focusing active window",
        cuaStatus: "active",
        screenshotUrl: activeLiveTask?.computerState?.screenshotUrl,
        mouseX: 54,
        mouseY: 42,
      },
    });
    setIsContextOpen(true);
  };

  // Inspecting artifact
  const handleSelectArtifact = (artifact: ArtifactCardData) => {
    setContextData({
      mode: "artifact",
      artifact,
    });
    setIsContextOpen(true);
  };

  // Approving an action
  const handleApproveAction = (approvalId: string) => {
    if (activeLiveTask && activeLiveTask.approvalRequest) {
      const approval = activeLiveTask.approvalRequest;
      setActiveLiveTask({
        ...activeLiveTask,
        approvalRequest: {
          ...approval,
          status: "approved",
        },
      });
      setMessages((prev) => [
        ...prev,
        {
          id: `sys_${Date.now()}`,
          sender: "system",
          text: `✓ Authorized action '${approval.actionName}'. Execution resumed.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    }
  };

  // Rejecting an action
  const handleRejectAction = (approvalId: string) => {
    if (activeLiveTask && activeLiveTask.approvalRequest) {
      const approval = activeLiveTask.approvalRequest;
      setActiveLiveTask({
        ...activeLiveTask,
        approvalRequest: {
          ...approval,
          status: "rejected",
        },
      });
      setMessages((prev) => [
        ...prev,
        {
          id: `sys_${Date.now()}`,
          sender: "system",
          text: `✕ Action '${approval.actionName}' was denied by user.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    }
  };

  // Adding dynamic instruction to running task
  const handleAddInstruction = (taskId: string, instruction: string) => {
    if (activeLiveTask) {
      const updatedSteps = [
        ...activeLiveTask.planSteps,
        { id: `custom_${Date.now()}`, title: instruction, status: "pending" as const },
      ];
      setActiveLiveTask({
        ...activeLiveTask,
        planSteps: updatedSteps,
      });
      setMessages((prev) => [
        ...prev,
        {
          id: `user_${Date.now()}`,
          sender: "user",
          text: `Add instruction: "${instruction}"`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
        {
          id: `ceo_${Date.now()}`,
          sender: "ceo",
          text: `Added instruction "${instruction}" to active execution plan without restarting.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    }
  };

  // Running tasks list for TaskSwitcher
  const runningTasks: RunningTaskItem[] = [
    {
      id: "task_suppremo_growth",
      title: "Suppremo Competitor Research",
      progress: activeLiveTask?.progress || 78,
      agentCount: 3,
      status: "running",
    },
    {
      id: "task_landing_page",
      title: "Build Landing Page",
      progress: 41,
      agentCount: 1,
      status: "running",
    },
    {
      id: "task_market_analysis",
      title: "Market Demand Study",
      progress: 18,
      agentCount: 2,
      status: "running",
    },
  ];

  return (
    <div className="appShell">
      {/* 1. Left Minimal Sidebar */}
      <ChatSidebar
        conversations={conversations}
        activeConversationId={activeConvId}
        onSelectConversation={(id) => setActiveConvId(id)}
        onNewTask={() => {
          setMessages([
            {
              id: `welcome_${Date.now()}`,
              sender: "ceo",
              text: "CEO OS is ready for your new directive. What objective shall we tackle?",
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            },
          ]);
          setActiveLiveTask(null);
        }}
        onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
      />

      {/* 2. Floating Parallel Task Switcher */}
      <TaskSwitcher
        tasks={runningTasks}
        activeTaskId={activeLiveTask?.id}
        onSelectTask={(id) => {
          if (id === "task_suppremo_growth") {
            setActiveLiveTask(INITIAL_TASK);
          }
        }}
      />

      {/* 3. Center Main Chat Area */}
      <main className="workspace" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {/* Chat Header */}
        <header className="chatHeaderRow">
          <div className="headerMetaLeft">
            <div className="headerCeoIdentity">
              <span className="ceoAvatarIcon">👑</span>
              <div>
                <h2 className="headerTitle">
                  {conversations.find((c) => c.id === activeConvId)?.title || "Suppremo Growth & Research"}
                </h2>
                <div className="headerStatusSub">
                  <span className="liveGreenDot" />
                  <span>CEO Mode · Autonomous · 3 Agents Active</span>
                </div>
              </div>
            </div>
          </div>

          <div className="headerControlsRight">
            <button
              className="headerControlBtn"
              onClick={() => {
                setContextData({
                  mode: "default",
                  taskOverview: {
                    taskId: "task_suppremo_growth",
                    title: "Suppremo Growth Research",
                    status: "Running",
                    progress: 78,
                    agentCount: 3,
                    toolCount: 6,
                    actionsCount: 27,
                    elapsed: "08:42",
                    model: "Gemini 3.7 Flash",
                    reasoning: "High",
                    cost: "₹2.38",
                    tokens: "28.4k",
                  },
                });
                setIsContextOpen(!isContextOpen);
              }}
              title="Toggle Mission Control Details"
            >
              📊 System State
            </button>
          </div>
        </header>

        {/* Proactive CEO Recommendation Banner */}
        <div className="proactiveInsightBanner">
          <div className="insightIcon">💡</div>
          <div className="insightText">
            <strong>CEO Proactive Observation:</strong> Found 3 pricing vulnerabilities in Zomato & Swiggy commission structures. Would you like a differentiated pitch deck drafted?
          </div>
          <button
            className="btnInsightAction"
            onClick={() => handleSendMessage("Yes, draft the differentiated pitch deck.")}
          >
            Draft Pitch Deck
          </button>
        </div>

        {/* Conversation Stream */}
        <div className="chatMessageFeed">
          {messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}

          {/* Inline Live Task Card directly inside chat */}
          {activeLiveTask && (
            <LiveTaskCard
              task={activeLiveTask}
              onSelectAgent={handleSelectAgent}
              onSelectBrowser={handleSelectBrowser}
              onSelectComputer={handleSelectComputer}
              onSelectArtifact={handleSelectArtifact}
              onApproveAction={handleApproveAction}
              onRejectAction={handleRejectAction}
              onAddInstruction={handleAddInstruction}
            />
          )}

          {isProcessing && <ThinkingBubble text="CEO OS reasoning and dispatching directives..." />}
          <div ref={messagesEndRef} />
        </div>

        {/* Fixed Chat Composer */}
        <ChatComposer
          onSendMessage={handleSendMessage}
          isProcessing={isProcessing}
          isVoiceActive={isVoiceActive}
          onToggleVoice={() => setIsVoiceActive(!isVoiceActive)}
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        />
      </main>

      {/* 4. Contextual Right Sidebar Panel */}
      <ContextPanel
        isOpen={isContextOpen}
        onClose={() => setIsContextOpen(false)}
        data={contextData}
        onInterruptComputer={() => {
          alert("macOS CUA control paused. User has interactive control.");
        }}
        onPauseTask={() => {
          if (activeLiveTask) {
            setActiveLiveTask({ ...activeLiveTask, status: "blocked" });
          }
        }}
      />

      {/* 5. Global Command Palette */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSelectAction={(action) => {
          if (action === "new_task") {
            setActiveLiveTask(null);
            setMessages([
              {
                id: `welcome_${Date.now()}`,
                sender: "ceo",
                text: "CEO OS is ready. State your objective.",
                timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              },
            ]);
          } else if (action === "talk_jarvis") {
            setIsVoiceActive(true);
          } else if (action === "open_computer") {
            handleSelectComputer();
          } else if (action === "open_browser") {
            handleSelectBrowser();
          }
        }}
      />
    </div>
  );
}
