"use client";

import { useState } from "react";
import { formatDate, requestJson } from "../lib/api";
import type { Task } from "../lib/contracts";
import { availableTaskActions } from "../lib/dashboard-utils.mjs";
import { formatTaskStatus } from "../lib/task-status.mjs";

export function TaskCard({
  task,
  onChanged,
  compact = false,
}: {
  task: Task;
  onChanged: () => void;
  compact?: boolean;
}) {
  const [expanded, setExpanded] = useState(!compact);
  const [showJson, setShowJson] = useState(false);
  const [actionPending, setActionPending] = useState(false);

  async function control(action: "pause" | "resume" | "cancel") {
    try {
      setActionPending(true);
      await requestJson(`/api/v1/tasks/${task.id}/${action}`, { method: "POST" });
      onChanged();
    } finally {
      setActionPending(false);
    }
  }

  const steps = task.plan.steps || [];
  const evidence = task.result?.evidence || [];
  const isTerminal = ["success", "partial_success", "failed", "cancelled"].includes(task.status);
  const progressPercent = isTerminal
    ? 100
    : task.status === "running"
    ? 65
    : task.status === "planning"
    ? 25
    : 10;

  return (
    <article className={`card taskCard ${task.status}`}>
      <div className="cardHead">
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span className={`status ${task.status}`}>{formatTaskStatus(task.status)}</span>
          <span style={{ fontSize: "10px", opacity: 0.6, fontFamily: "var(--font-mono)" }}>
            ID: {task.id.slice(0, 8)}...
          </span>
        </div>
        <time>{formatDate(task.updated_at)}</time>
      </div>

      <h3>{task.objective}</h3>

      {!isTerminal && (
        <div className="progressBar">
          <div className="progressFill" style={{ width: `${progressPercent}%` }} />
        </div>
      )}

      {expanded && steps.length > 0 && (
        <ol className="steps">
          {steps.map((step, index) => {
            const risk = step.capability.startsWith("files.write") || step.capability.startsWith("shell")
              ? "r1"
              : step.capability.startsWith("agency.task")
              ? "r1"
              : "r0";
            return (
              <li key={`${task.id}-${index}`}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <strong>{step.capability}</strong>
                    <span className={`riskBadge ${risk}`}>{risk.toUpperCase()}</span>
                  </div>
                  <small>{step.success_condition}</small>
                </div>
              </li>
            );
          })}
        </ol>
      )}

      {task.result?.message && <div className="resultBox">{task.result.message}</div>}

      {expanded && evidence.length > 0 && (
        <div className="evidenceBox">
          <strong style={{ display: "block", marginBottom: "6px", color: "var(--green)" }}>
            Verified Evidence ({evidence.length}):
          </strong>
          {evidence.map((item, idx) => (
            <div key={`${task.id}-ev-${idx}`} style={{ margin: "3px 0" }}>
              ✓ {item}
            </div>
          ))}
        </div>
      )}

      {task.error && (
        <div className="notice error" style={{ marginTop: "12px", marginBottom: "0" }}>
          <strong>Error:</strong> {task.error}
        </div>
      )}

      {showJson && (
        <pre
          style={{
            marginTop: "12px",
            padding: "12px",
            background: "var(--bg)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            fontSize: "11px",
            fontFamily: "var(--font-mono)",
            overflowX: "auto",
            maxHeight: "220px",
          }}
        >
          {JSON.stringify(task, null, 2)}
        </pre>
      )}

      <div
        className="controls"
        style={{ justifyContent: "space-between", alignItems: "center" }}
      >
        <div style={{ display: "flex", gap: "8px" }}>
          {availableTaskActions(task.status).map((action) => (
            <button
              key={action}
              type="button"
              disabled={actionPending}
              className={action === "cancel" ? "danger" : "secondary"}
              onClick={() => void control(action as "pause" | "resume" | "cancel")}
            >
              {actionPending ? "..." : action}
            </button>
          ))}
        </div>

        <div style={{ display: "flex", gap: "8px" }}>
          <button
            type="button"
            className="secondary"
            style={{ minHeight: "32px", fontSize: "10px", padding: "0 10px" }}
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "COLLAPSE" : `VIEW DETAILS (${steps.length} STEPS)`}
          </button>
          <button
            type="button"
            className="secondary"
            style={{ minHeight: "32px", fontSize: "10px", padding: "0 10px" }}
            onClick={() => setShowJson(!showJson)}
          >
            {showJson ? "HIDE JSON" : "JSON"}
          </button>
        </div>
      </div>
    </article>
  );
}
