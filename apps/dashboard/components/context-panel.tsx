"use client";

import React, { memo } from "react";
import type { AgentActiveMember, ArtifactCardData } from "../lib/contracts";

export type ContextPanelMode =
  | "default"
  | "agent"
  | "browser"
  | "computer"
  | "memory"
  | "artifact"
  | "task";

export type ContextPanelData = {
  mode: ContextPanelMode;
  agent?: AgentActiveMember | null;
  browser?: {
    currentUrl: string;
    visitedPages: Array<{ url: string; title: string; status: "visited" | "current" | "pending" }>;
    extractedSummary?: string;
  } | null;
  computer?: {
    activeApp: string;
    action: string;
    cuaStatus: "active" | "idle" | "paused";
    screenshotUrl?: string;
    mouseX?: number;
    mouseY?: number;
  } | null;
  memory?: Array<{ content: string; source: string; confidence: number }> | null;
  artifact?: ArtifactCardData | null;
  taskOverview?: {
    taskId: string;
    title: string;
    status: string;
    progress: number;
    agentCount: number;
    toolCount: number;
    actionsCount: number;
    elapsed: string;
    model: string;
    reasoning: string;
    cost: string;
    tokens: string;
  } | null;
};

interface ContextPanelProps {
  isOpen: boolean;
  onClose: () => void;
  data: ContextPanelData;
  onInterruptComputer?: () => void;
  onPauseTask?: () => void;
}

export const ContextPanel = memo(function ContextPanel({
  isOpen,
  onClose,
  data,
  onInterruptComputer,
  onPauseTask,
}: ContextPanelProps) {
  if (!isOpen) return null;

  return (
    <aside className="contextPanelRoot">
      {/* Header */}
      <div className="contextPanelHeader">
        <div className="contextPanelTitleGroup">
          <span className="contextPanelBadge">
            {data.mode === "default" && "MISSION CONTROL"}
            {data.mode === "agent" && "SPECIALIST AGENT"}
            {data.mode === "browser" && "BROWSER RUNTIME"}
            {data.mode === "computer" && "COMPUTER CONTROL"}
            {data.mode === "memory" && "EPISODIC MEMORY"}
            {data.mode === "artifact" && "ARTIFACT PREVIEW"}
            {data.mode === "task" && "TASK OVERVIEW"}
          </span>
          <h3 className="contextPanelTitle">
            {data.mode === "default" && "System & Active State"}
            {data.mode === "agent" && (data.agent?.name || "Agent Details")}
            {data.mode === "browser" && "Live Browser Session"}
            {data.mode === "computer" && "macOS CUA Live View"}
            {data.mode === "memory" && "Retrieved Knowledge"}
            {data.mode === "artifact" && (data.artifact?.title || "Artifact Preview")}
            {data.mode === "task" && (data.taskOverview?.title || "Active Task")}
          </h3>
        </div>
        <button className="contextPanelCloseBtn" onClick={onClose} aria-label="Close panel">
          ✕
        </button>
      </div>

      {/* Content Body */}
      <div className="contextPanelBody">
        {/* 1. AGENT INSPECTION MODE */}
        {data.mode === "agent" && data.agent && (
          <div className="contextSection">
            <div className="agentHeaderCard">
              <div className="agentAvatarLarge">
                {data.agent.role.slice(0, 2).toUpperCase()}
              </div>
              <div>
                <h4 className="agentDetailName">{data.agent.name}</h4>
                <p className="agentDetailRole">{data.agent.role}</p>
                <span className={`statusPill status-${data.agent.status}`}>
                  ● {data.agent.status.toUpperCase()}
                </span>
              </div>
            </div>

            <div className="contextField">
              <span className="fieldLabel">ASSIGNED GOAL</span>
              <p className="fieldValue">
                {data.agent.currentAction || "Executing specialist delegation sub-plan."}
              </p>
            </div>

            {data.agent.toolsUsed && data.agent.toolsUsed.length > 0 && (
              <div className="contextField">
                <span className="fieldLabel">CAPABILITIES BOUND</span>
                <div className="toolChipsList">
                  {data.agent.toolsUsed.map((t, idx) => (
                    <span key={idx} className="toolChipSmall">
                      ⚡ {t}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {data.agent.lastOutput && (
              <div className="contextField">
                <span className="fieldLabel">LATEST OUTPUT</span>
                <div className="codeBlockCompact">
                  {data.agent.lastOutput}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 2. BROWSER INSPECTION MODE */}
        {data.mode === "browser" && data.browser && (
          <div className="contextSection">
            <div className="browserUrlBar">
              <span className="browserDot red" />
              <span className="browserDot yellow" />
              <span className="browserDot green" />
              <span className="browserUrlText">{data.browser.currentUrl}</span>
            </div>

            <div className="contextField">
              <span className="fieldLabel">VISITED PAGES ({data.browser.visitedPages.length})</span>
              <ul className="visitedPagesList">
                {data.browser.visitedPages.map((page, idx) => (
                  <li key={idx} className={`visitedPageItem ${page.status}`}>
                    <span className="pageIcon">
                      {page.status === "visited" ? "✓" : page.status === "current" ? "●" : "○"}
                    </span>
                    <div className="pageMeta">
                      <span className="pageTitle">{page.title || page.url}</span>
                      <span className="pageUrl">{page.url}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {data.browser.extractedSummary && (
              <div className="contextField">
                <span className="fieldLabel">EXTRACTED FINDINGS</span>
                <p className="fieldValue">{data.browser.extractedSummary}</p>
              </div>
            )}
          </div>
        )}

        {/* 3. COMPUTER CONTROL MODE */}
        {data.mode === "computer" && data.computer && (
          <div className="contextSection">
            <div className="computerLiveScreen">
              {data.computer.screenshotUrl ? (
                <img
                  src={data.computer.screenshotUrl}
                  alt="Mac Screen Capture"
                  className="computerScreenshot"
                />
              ) : (
                <div className="computerPlaceholder">
                  <span className="computerIcon">🖥️</span>
                  <span>macOS Screen Stream Active</span>
                  <span className="appBadge">{data.computer.activeApp}</span>
                </div>
              )}
              {data.computer.mouseX !== undefined && (
                <div
                  className="virtualMousePointer"
                  style={{
                    left: `${data.computer.mouseX || 50}%`,
                    top: `${data.computer.mouseY || 50}%`,
                  }}
                >
                  ↖
                </div>
              )}
            </div>

            <div className="computerStatusRow">
              <div>
                <span className="fieldLabel">ACTIVE APPLICATION</span>
                <p className="fieldValue">{data.computer.activeApp}</p>
              </div>
              <div>
                <span className="fieldLabel">CUA STATUS</span>
                <span className="statusPill status-running">● {data.computer.cuaStatus.toUpperCase()}</span>
              </div>
            </div>

            <div className="contextField">
              <span className="fieldLabel">CURRENT ACTION</span>
              <p className="fieldValue">{data.computer.action}</p>
            </div>

            <div className="actionButtonsGroup">
              <button
                className="btnDangerSmall"
                onClick={onInterruptComputer}
              >
                ⏸ Take Control / Pause
              </button>
            </div>
          </div>
        )}

        {/* 4. MEMORY MODE */}
        {data.mode === "memory" && data.memory && (
          <div className="contextSection">
            <span className="fieldLabel">RETRIEVED EPISODIC & SEMANTIC RECORDS</span>
            <div className="memoryRecordsList">
              {data.memory.map((m, idx) => (
                <div key={idx} className="memoryCardSmall">
                  <p className="memoryContent">{m.content}</p>
                  <div className="memoryMeta">
                    <span>Source: {m.source}</span>
                    <span className="confidenceBadge">{(m.confidence * 100).toFixed(0)}% Match</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 5. ARTIFACT MODE */}
        {data.mode === "artifact" && data.artifact && (
          <div className="contextSection">
            <div className="artifactHeader">
              <h4>{data.artifact.title}</h4>
              <span className="artifactTypePill">{data.artifact.type}</span>
            </div>
            {data.artifact.description && (
              <p className="fieldValue">{data.artifact.description}</p>
            )}

            {data.artifact.filesChanged !== undefined && (
              <div className="diffSummaryBar">
                <span>{data.artifact.filesChanged} files changed</span>
                <span className="diffAdd">+{data.artifact.additions || 0}</span>
                <span className="diffSub">-{data.artifact.deletions || 0}</span>
              </div>
            )}

            {data.artifact.content && (
              <pre className="artifactCodeViewer">
                <code>{data.artifact.content}</code>
              </pre>
            )}
          </div>
        )}

        {/* 6. DEFAULT / TASK OVERVIEW MODE */}
        {(data.mode === "default" || data.mode === "task") && (
          <div className="contextSection">
            {data.taskOverview && (
              <div className="taskOverviewCard">
                <div className="taskCardTop">
                  <span className="statusPill status-running">● {data.taskOverview.status}</span>
                  <span className="elapsedBadge">{data.taskOverview.elapsed}</span>
                </div>
                <h4 className="taskCardHeading">{data.taskOverview.title}</h4>
                <div className="progressBarContainer">
                  <div
                    className="progressBarFill"
                    style={{ width: `${data.taskOverview.progress}%` }}
                  />
                </div>
                <div className="taskStatsGrid">
                  <div className="taskStatItem">
                    <span className="statLabel">Agents</span>
                    <span className="statVal">{data.taskOverview.agentCount} active</span>
                  </div>
                  <div className="taskStatItem">
                    <span className="statLabel">Tools</span>
                    <span className="statVal">{data.taskOverview.toolCount} bound</span>
                  </div>
                  <div className="taskStatItem">
                    <span className="statLabel">Activity</span>
                    <span className="statVal">{data.taskOverview.actionsCount} actions</span>
                  </div>
                </div>
              </div>
            )}

            {/* System Runtime Health Status */}
            <div className="systemStatusBlock">
              <span className="fieldLabel">RUNTIME SUBSYSTEMS</span>
              <div className="runtimePillsGrid">
                <div className="runtimePill">
                  <span className="pillDot green" /> CEO Agent
                </div>
                <div className="runtimePill">
                  <span className="pillDot green" /> Jarvis Voice
                </div>
                <div className="runtimePill">
                  <span className="pillDot green" /> Dynamic Router
                </div>
                <div className="runtimePill">
                  <span className="pillDot green" /> Browser Playwright
                </div>
                <div className="runtimePill">
                  <span className="pillDot green" /> macOS CUA
                </div>
                <div className="runtimePill">
                  <span className="pillDot green" /> Memory Vector
                </div>
              </div>
            </div>

            {/* Model & Cost Details */}
            <div className="modelCostCard">
              <div className="modelRow">
                <span className="modelLabel">Primary Model</span>
                <span className="modelValue">Gemini 3.7 Flash</span>
              </div>
              <div className="modelRow">
                <span className="modelLabel">Reasoning Tier</span>
                <span className="modelValue">High (Autonomous)</span>
              </div>
              <div className="modelRow">
                <span className="modelLabel">Session Cost</span>
                <span className="modelValue highlight">₹2.38</span>
              </div>
              <div className="modelRow">
                <span className="modelLabel">Tokens Streamed</span>
                <span className="modelValue">28.4k</span>
              </div>
            </div>

            {onPauseTask && (
              <button className="pauseTaskBtn" onClick={onPauseTask}>
                ⏸ Pause Active Operations
              </button>
            )}
          </div>
        )}
      </div>
    </aside>
  );
});
