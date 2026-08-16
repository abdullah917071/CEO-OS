"use client";

import React, { memo, useState } from "react";
import type {
  AgentActiveMember,
  ArtifactCardData,
  ExecutionEvent,
  HumanApprovalCardData,
  TaskPlanStep,
  ToolExecutionChip,
} from "../lib/contracts";

export interface LiveTask {
  id: string;
  title: string;
  objective: string;
  status: "running" | "completed" | "failed" | "blocked" | "awaiting_approval" | "incomplete";
  progress: number;
  currentStep: string;
  previousStep?: string;
  nextStep?: string;
  elapsedTime: string;
  agentMembers: AgentActiveMember[];
  toolChips: ToolExecutionChip[];
  events: ExecutionEvent[];
  planSteps: TaskPlanStep[];
  approvalRequest?: HumanApprovalCardData | null;
  artifacts?: ArtifactCardData[];
  resultSummary?: {
    findings: string[];
    stats: Record<string, string | number>;
    conclusion: string;
    totalDuration: string;
  } | null;
  computerState?: {
    activeApp: string;
    action: string;
    screenshotUrl?: string;
  } | null;
  browserState?: {
    currentUrl: string;
    pagesCount: number;
    visitedDomains: string[];
  } | null;
}

interface LiveTaskCardProps {
  task: LiveTask;
  onSelectAgent?: (agent: AgentActiveMember) => void;
  onSelectBrowser?: () => void;
  onSelectComputer?: () => void;
  onSelectMemory?: () => void;
  onSelectArtifact?: (artifact: ArtifactCardData) => void;
  onApproveAction?: (approvalId: string) => void;
  onRejectAction?: (approvalId: string) => void;
  onAddInstruction?: (taskId: string, instruction: string) => void;
}

export const LiveTaskCard = memo(function LiveTaskCard({
  task,
  onSelectAgent,
  onSelectBrowser,
  onSelectComputer,
  onSelectArtifact,
  onApproveAction,
  onRejectAction,
  onAddInstruction,
}: LiveTaskCardProps) {
  const [viewMode, setViewMode] = useState<"simple" | "developer">("simple");
  const [isTimelineExpanded, setIsTimelineExpanded] = useState(true);
  const [isPlanExpanded, setIsPlanExpanded] = useState(true);
  const [expandedChipId, setExpandedChipId] = useState<string | null>(null);
  const [customInstruction, setCustomInstruction] = useState("");
  const [showInstructionInput, setShowInstructionInput] = useState(false);

  const completedSteps = task.planSteps.filter((s) => s.status === "completed").length;
  const totalSteps = Math.max(task.planSteps.length, 1);

  return (
    <div className={`liveTaskCardRoot status-${task.status}`}>
      {/* 1. Header & Progress Bar */}
      <div className="taskCardHeaderRow">
        <div className="taskHeaderLeft">
          <div className="statusBadgeWithPulse">
            <span className={`pulseDot pulse-${task.status}`} />
            <span className="statusText">{task.status.replace("_", " ").toUpperCase()}</span>
          </div>
          <span className="taskElapsedTime">{task.elapsedTime}</span>
        </div>

        <div className="viewModeToggle">
          <button
            className={`toggleBtn ${viewMode === "simple" ? "active" : ""}`}
            onClick={() => setViewMode("simple")}
          >
            Simple
          </button>
          <button
            className={`toggleBtn ${viewMode === "developer" ? "active" : ""}`}
            onClick={() => setViewMode("developer")}
          >
            Developer
          </button>
        </div>
      </div>

      <h3 className="taskObjectiveHeading">{task.title || task.objective}</h3>

      {/* Progress Bar with honest step metrics */}
      <div className="progressSection">
        <div className="progressMetaRow">
          <span className="progressPct">{task.progress}%</span>
          <span className="stepCountText">
            {completedSteps} / {totalSteps} steps completed
          </span>
        </div>
        <div className="taskProgressBar">
          <div
            className={`taskProgressFill status-${task.status}`}
            style={{ width: `${task.progress}%` }}
          />
        </div>
      </div>

      {/* 2. Prominent Live Step Indicator */}
      {task.status === "running" && (
        <div className="liveStepIndicatorBox">
          <div className="currentStepRow">
            <span className="stepLabel">CURRENTLY</span>
            <div className="currentStepTextGroup">
              <span className="livePulseIcon" />
              <span className="currentStepText">{task.currentStep}</span>
            </div>
          </div>

          {(task.previousStep || task.nextStep) && (
            <div className="surroundingStepsRow">
              {task.previousStep && (
                <div className="prevStepItem">
                  <span className="subStepLabel">Previous:</span>
                  <span className="prevStepText">✓ {task.previousStep}</span>
                </div>
              )}
              {task.nextStep && (
                <div className="nextStepItem">
                  <span className="subStepLabel">Next:</span>
                  <span className="nextStepText">○ {task.nextStep}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 3. Human Approval UI if required */}
      {task.approvalRequest && task.approvalRequest.status === "pending" && (
        <div className="humanApprovalBox">
          <div className="approvalHeader">
            <span className="approvalAlertIcon">⚠️</span>
            <div>
              <h4 className="approvalTitle">Approval Required ({task.approvalRequest.riskLevel})</h4>
              <p className="approvalSubtitle">CEO OS is requesting authorization to execute an external action.</p>
            </div>
          </div>

          <div className="approvalDetailsCard">
            <div className="approvalDetailRow">
              <span className="detailKey">Action:</span>
              <span className="detailVal font-bold">{task.approvalRequest.actionName}</span>
            </div>
            {task.approvalRequest.targetRecipient && (
              <div className="approvalDetailRow">
                <span className="detailKey">Recipient:</span>
                <span className="detailVal">{task.approvalRequest.targetRecipient}</span>
              </div>
            )}
            {task.approvalRequest.subject && (
              <div className="approvalDetailRow">
                <span className="detailKey">Subject:</span>
                <span className="detailVal">{task.approvalRequest.subject}</span>
              </div>
            )}
            {task.approvalRequest.commandString && (
              <div className="approvalDetailRow">
                <span className="detailKey">Command:</span>
                <code className="detailVal codeHighlight">{task.approvalRequest.commandString}</code>
              </div>
            )}
            {task.approvalRequest.affectedPath && (
              <div className="approvalDetailRow">
                <span className="detailKey">Affected Path:</span>
                <span className="detailVal">{task.approvalRequest.affectedPath}</span>
              </div>
            )}
            <p className="approvalDescription">{task.approvalRequest.description}</p>
          </div>

          <div className="approvalActionsRow">
            <button
              className="btnApprove"
              onClick={() => onApproveAction && onApproveAction(task.approvalRequest!.id)}
            >
              ✓ Authorize & Execute
            </button>
            <button
              className="btnReject"
              onClick={() => onRejectAction && onRejectAction(task.approvalRequest!.id)}
            >
              ✕ Deny
            </button>
          </div>
        </div>
      )}

      {/* 4. Active Agent Stack */}
      {task.agentMembers && task.agentMembers.length > 0 && (
        <div className="agentStackSection">
          <span className="sectionSmallHeading">
            ACTIVE AGENT TEAM ({task.agentMembers.length})
          </span>
          <div className="agentAvatarsRow">
            {task.agentMembers.map((agent) => (
              <button
                key={agent.id}
                className="agentAvatarBtn"
                onClick={() => onSelectAgent && onSelectAgent(agent)}
                title={`${agent.name} (${agent.role}) — Click to inspect`}
              >
                <div className={`agentAvatarIcon status-${agent.status}`}>
                  {agent.role.slice(0, 2).toUpperCase()}
                </div>
                <div className="agentAvatarMeta">
                  <span className="agentAvatarName">{agent.name}</span>
                  <span className="agentAvatarStatus">● {agent.status}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 5. Tool Activity Chips */}
      {task.toolChips && task.toolChips.length > 0 && (
        <div className="toolChipsSection">
          <span className="sectionSmallHeading">CAPABILITY ACTIVITY</span>
          <div className="toolChipsGrid">
            {task.toolChips.map((chip) => {
              const isExpanded = expandedChipId === chip.id;
              return (
                <div
                  key={chip.id}
                  className={`toolExecutionChip chip-${chip.type} ${isExpanded ? "expanded" : ""}`}
                  onClick={() => setExpandedChipId(isExpanded ? null : chip.id)}
                >
                  <div className="chipHeader">
                    <span className="chipIcon">
                      {chip.type === "browser" && "🌐"}
                      {chip.type === "search" && "🔍"}
                      {chip.type === "memory" && "🧠"}
                      {chip.type === "computer" && "🖥️"}
                      {chip.type === "terminal" && "⌨️"}
                      {chip.type === "filesystem" && "📁"}
                      {chip.type === "tool" && "⚡"}
                    </span>
                    <span className="chipTitle">{chip.title}</span>
                    {chip.status === "running" && <span className="chipSpinner" />}
                  </div>

                  {isExpanded && (
                    <div className="chipExpandedDetails">
                      {chip.input && (
                        <div className="detailSubRow">
                          <span className="detailSubLabel">Input:</span>
                          <span className="detailSubText">{chip.input}</span>
                        </div>
                      )}
                      {chip.result && (
                        <div className="detailSubRow">
                          <span className="detailSubLabel">Result:</span>
                          <span className="detailSubText">{chip.result}</span>
                        </div>
                      )}
                      {chip.durationMs !== undefined && (
                        <div className="detailSubRow">
                          <span className="detailSubLabel">Latency:</span>
                          <span className="detailSubText">{chip.durationMs.toFixed(0)} ms</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* 6. Computer & Browser Mini Preview Cards */}
      <div className="previewsGrid">
        {task.computerState && (
          <div className="miniPreviewCard computerPreviewCard">
            <div className="previewHeader">
              <span className="previewIcon">🖥️ Computer Control</span>
              <button
                className="btnLinkSmall"
                onClick={onSelectComputer}
              >
                View Live ↗
              </button>
            </div>
            <p className="previewSub">{task.computerState.activeApp} · {task.computerState.action}</p>
          </div>
        )}

        {task.browserState && (
          <div className="miniPreviewCard browserPreviewCard">
            <div className="previewHeader">
              <span className="previewIcon">🌐 Browser Agent</span>
              <button
                className="btnLinkSmall"
                onClick={onSelectBrowser}
              >
                {task.browserState.pagesCount} pages ↗
              </button>
            </div>
            <p className="previewSub">{task.browserState.currentUrl}</p>
          </div>
        )}
      </div>

      {/* 7. Interactive Live Task Plan */}
      {task.planSteps && task.planSteps.length > 0 && (
        <div className="taskPlanSection">
          <div
            className="planToggleHeader"
            onClick={() => setIsPlanExpanded(!isPlanExpanded)}
          >
            <span className="sectionSmallHeading">EXECUTION PLAN</span>
            <span className="toggleArrow">{isPlanExpanded ? "▲" : "▼"}</span>
          </div>

          {isPlanExpanded && (
            <div className="planStepsList">
              {task.planSteps.map((step, idx) => (
                <div key={step.id || idx} className={`planStepRow status-${step.status}`}>
                  <span className="stepStatusSymbol">
                    {step.status === "completed" && "✓"}
                    {step.status === "in_progress" && "●"}
                    {step.status === "pending" && "○"}
                    {step.status === "failed" && "✕"}
                  </span>
                  <span className="planStepTitle">{step.title}</span>
                </div>
              ))}

              {/* Add instruction button */}
              <div className="addInstructionRow">
                {!showInstructionInput ? (
                  <button
                    className="btnAddInstruction"
                    onClick={() => setShowInstructionInput(true)}
                  >
                    + Add instruction to running task
                  </button>
                ) : (
                  <div className="instructionInputBox">
                    <input
                      type="text"
                      placeholder="e.g. Also compare their delivery fees..."
                      value={customInstruction}
                      onChange={(e) => setCustomInstruction(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && customInstruction.trim()) {
                          onAddInstruction && onAddInstruction(task.id, customInstruction.trim());
                          setCustomInstruction("");
                          setShowInstructionInput(false);
                        }
                      }}
                      className="instructionInputField"
                    />
                    <button
                      className="btnSendInstruction"
                      onClick={() => {
                        if (customInstruction.trim()) {
                          onAddInstruction && onAddInstruction(task.id, customInstruction.trim());
                          setCustomInstruction("");
                          setShowInstructionInput(false);
                        }
                      }}
                    >
                      Add
                    </button>
                    <button
                      className="btnCancelInstruction"
                      onClick={() => setShowInstructionInput(false)}
                    >
                      ✕
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 8. Collapsible Execution Timeline */}
      {task.events && task.events.length > 0 && (
        <div className="timelineSection">
          <div
            className="timelineToggleHeader"
            onClick={() => setIsTimelineExpanded(!isTimelineExpanded)}
          >
            <span className="sectionSmallHeading">
              LIVE TIMELINE ({task.events.length} events)
            </span>
            <span className="toggleArrow">{isTimelineExpanded ? "▲" : "▼"}</span>
          </div>

          {isTimelineExpanded && (
            <div className="timelineEventsList">
              {task.events.map((evt) => (
                <div key={evt.id} className={`timelineEventItem status-${evt.status}`}>
                  <span className="eventTime">{evt.timestamp}</span>
                  <span className={`eventSourceBadge source-${evt.source}`}>
                    {evt.source.toUpperCase()}
                  </span>
                  <div className="eventContent">
                    <span className="eventTitle">{evt.title}</span>
                    {evt.summary && viewMode === "developer" && (
                      <p className="eventSummary">{evt.summary}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 9. Artifacts Generated */}
      {task.artifacts && task.artifacts.length > 0 && (
        <div className="artifactsSection">
          <span className="sectionSmallHeading">PRODUCED ARTIFACTS</span>
          <div className="artifactsGrid">
            {task.artifacts.map((art) => (
              <div key={art.id} className="artifactCardMini">
                <div className="artifactCardTop">
                  <span className="artIcon">
                    {art.type === "website" && "🌐"}
                    {art.type === "code" && "💻"}
                    {art.type === "document" && "📄"}
                    {art.type === "report" && "📊"}
                    {art.type === "image" && "🖼️"}
                  </span>
                  <span className="artTitle">{art.title}</span>
                  <span className="artType">{art.type}</span>
                </div>
                {art.description && <p className="artDesc">{art.description}</p>}
                {art.filesChanged !== undefined && (
                  <div className="artDiff">
                    <span>{art.filesChanged} files changed</span>
                    <span className="diffAdd">+{art.additions}</span>
                    <span className="diffSub">-{art.deletions}</span>
                  </div>
                )}
                <div className="artActions">
                  <button
                    className="btnArtAction"
                    onClick={() => onSelectArtifact && onSelectArtifact(art)}
                  >
                    Preview
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 10. Task Result Summary when completed */}
      {task.status === "completed" && task.resultSummary && (
        <div className="completionCard">
          <div className="completionHeader">
            <span className="completionCheck">✓</span>
            <div>
              <h4 className="completionTitle">Execution Completed</h4>
              <span className="completionElapsed">Completed in {task.resultSummary.totalDuration}</span>
            </div>
          </div>

          <div className="statsHighlightGrid">
            {Object.entries(task.resultSummary.stats).map(([k, v]) => (
              <div key={k} className="statBox">
                <span className="statVal">{v}</span>
                <span className="statKey">{k}</span>
              </div>
            ))}
          </div>

          <div className="keyFindingsBlock">
            <span className="findingHeader">Key Findings & Synthesis</span>
            <p className="findingText">{task.resultSummary.conclusion}</p>
          </div>
        </div>
      )}
    </div>
  );
});
