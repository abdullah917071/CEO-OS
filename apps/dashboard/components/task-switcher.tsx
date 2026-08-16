"use client";

import React, { memo, useState } from "react";

export interface RunningTaskItem {
  id: string;
  title: string;
  progress: number;
  agentCount: number;
  status: "running" | "completed" | "failed" | "awaiting_approval";
}

interface TaskSwitcherProps {
  tasks: RunningTaskItem[];
  activeTaskId?: string;
  onSelectTask: (taskId: string) => void;
}

export const TaskSwitcher = memo(function TaskSwitcher({
  tasks,
  activeTaskId,
  onSelectTask,
}: TaskSwitcherProps) {
  const [isOpen, setIsOpen] = useState(false);

  const runningCount = tasks.filter((t) => t.status === "running").length;
  if (tasks.length === 0) return null;

  return (
    <div className="taskSwitcherContainer">
      <button
        className="taskSwitcherTrigger"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="pulsingDot green" />
        <span>
          {runningCount > 0 ? `${runningCount} task${runningCount > 1 ? "s" : ""} running` : "Task Center"}
        </span>
        <span className="arrow">{isOpen ? "▲" : "▼"}</span>
      </button>

      {isOpen && (
        <div className="taskSwitcherDropdown">
          <div className="dropdownHeader">
            <span>PARALLEL AUTONOMOUS TASKS</span>
          </div>
          <div className="dropdownList">
            {tasks.map((task) => (
              <div
                key={task.id}
                className={`dropdownItem ${task.id === activeTaskId ? "selected" : ""}`}
                onClick={() => {
                  onSelectTask(task.id);
                  setIsOpen(false);
                }}
              >
                <div className="itemTop">
                  <span className="itemTitle">{task.title}</span>
                  <span className="itemPct">{task.progress}%</span>
                </div>
                <div className="itemBar">
                  <div className="itemBarFill" style={{ width: `${task.progress}%` }} />
                </div>
                <div className="itemBottom">
                  <span>{task.agentCount} agents active</span>
                  <span className={`itemStatus status-${task.status}`}>{task.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
});
