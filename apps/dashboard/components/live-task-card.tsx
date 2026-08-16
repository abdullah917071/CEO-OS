"use client";

/**
 * LiveTaskCard — Real-time task execution card with step-by-step tool trace.
 * Follows frontend-developer skill: memo, performance, clear separation of concerns.
 */

import { memo } from "react";

export interface TaskStep {
  step_index: number;
  thought: string;
  tool_call?: { name: string; arguments: Record<string, unknown> } | null;
  tool_response?: { output: unknown } | null;
  duration_ms: number;
}

export interface LiveTask {
  id: string;
  status: "planning" | "running" | "retrying" | "waiting" | "needs_approval" | "success" | "partial_success" | "failed" | "cancelled";
  message?: string;
  objective?: string;
  created_at: string;
  updated_at?: string;
  steps?: TaskStep[];
  error?: string;
}

const STATUS_CONFIG: Record<LiveTask["status"], { label: string; color: string; dot: string; animate: boolean }> = {
  planning:       { label: "PLANNING",   color: "text-violet-400 bg-violet-950/60 border-violet-700/40",  dot: "bg-violet-400",  animate: true  },
  running:        { label: "RUNNING",    color: "text-cyan-400   bg-cyan-950/60   border-cyan-700/40",    dot: "bg-cyan-400",    animate: true  },
  retrying:       { label: "RETRYING",   color: "text-amber-400  bg-amber-950/60  border-amber-700/40",   dot: "bg-amber-400",   animate: true  },
  waiting:        { label: "WAITING",    color: "text-slate-400  bg-slate-800/60  border-slate-700/40",   dot: "bg-slate-400",   animate: false },
  needs_approval: { label: "APPROVAL",   color: "text-orange-400 bg-orange-950/60 border-orange-700/40",  dot: "bg-orange-400",  animate: true  },
  success:        { label: "DONE",       color: "text-emerald-400 bg-emerald-950/60 border-emerald-700/40", dot: "bg-emerald-400", animate: false },
  partial_success:{ label: "PARTIAL",    color: "text-yellow-400 bg-yellow-950/60 border-yellow-700/40",  dot: "bg-yellow-400",  animate: false },
  failed:         { label: "FAILED",     color: "text-red-400    bg-red-950/60    border-red-700/40",     dot: "bg-red-400",     animate: false },
  cancelled:      { label: "CANCELLED",  color: "text-slate-500  bg-slate-900/60  border-slate-700/40",   dot: "bg-slate-500",   animate: false },
};

function formatElapsed(createdAt: string): string {
  const diff = Date.now() - new Date(createdAt).getTime();
  if (diff < 60000) return `${Math.round(diff / 1000)}s`;
  if (diff < 3600000) return `${Math.round(diff / 60000)}m`;
  return `${Math.round(diff / 3600000)}h`;
}

interface LiveTaskCardProps {
  task: LiveTask;
  compact?: boolean;
}

export const LiveTaskCard = memo(function LiveTaskCard({ task, compact = false }: LiveTaskCardProps) {
  const cfg = STATUS_CONFIG[task.status] ?? STATUS_CONFIG.waiting;
  const title = task.message || task.objective || "Task";
  const elapsed = formatElapsed(task.created_at);
  const isActive = ["planning", "running", "retrying", "needs_approval"].includes(task.status);

  return (
    <div
      className={`rounded-xl border transition-all duration-300 ${
        isActive
          ? "border-cyan-700/30 bg-slate-900/70 shadow-lg shadow-cyan-950/20"
          : "border-slate-800/60 bg-slate-900/40"
      } ${compact ? "p-2.5" : "p-3.5"}`}
    >
      {/* Header row */}
      <div className="flex items-center justify-between gap-2">
        <span
          className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[10px] font-mono font-bold ${cfg.color}`}
        >
          <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot} ${cfg.animate ? "animate-pulse" : ""}`} />
          {cfg.label}
        </span>
        <span className="font-mono text-[10px] text-slate-500">{elapsed} ago</span>
      </div>

      {/* Title */}
      <div className={`mt-1.5 font-medium text-slate-200 ${compact ? "text-xs line-clamp-1" : "text-xs line-clamp-2"}`}>
        {title}
      </div>

      {/* Step trace — shown only in non-compact mode and when there are steps */}
      {!compact && task.steps && task.steps.length > 0 && (
        <div className="mt-2 border-t border-slate-800/60 pt-2 space-y-1">
          {task.steps.slice(-3).map((step) => (
            <div key={step.step_index} className="flex items-start gap-1.5 text-[10px] font-mono">
              <span className="text-violet-400/70 flex-shrink-0">S{step.step_index + 1}</span>
              {step.tool_call ? (
                <span className="text-emerald-400/80 truncate">
                  ▶ {step.tool_call.name}
                </span>
              ) : (
                <span className="text-slate-500 truncate">{step.thought.slice(0, 60)}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {task.status === "failed" && task.error && (
        <div className="mt-1.5 text-[10px] font-mono text-red-400/80 truncate">
          ✗ {task.error.slice(0, 80)}
        </div>
      )}

      {/* Active progress bar */}
      {isActive && (
        <div className="mt-2 h-0.5 w-full overflow-hidden rounded-full bg-slate-800">
          <div className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 animate-[progress_2s_ease-in-out_infinite]" />
        </div>
      )}
    </div>
  );
});
