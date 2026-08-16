"use client";

import React, { memo, useEffect, useState } from "react";

export interface CommandItem {
  id: string;
  label: string;
  category: "Actions" | "Navigation" | "Models" | "System";
  icon: string;
  shortcut?: string;
  action: () => void;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectAction: (actionName: string) => void;
}

export const CommandPalette = memo(function CommandPalette({
  isOpen,
  onClose,
  onSelectAction,
}: CommandPaletteProps) {
  const [query, setQuery] = useState("");

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        if (isOpen) onClose();
        else onSelectAction("open_palette");
      }
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, onSelectAction]);

  if (!isOpen) return null;

  const defaultCommands: CommandItem[] = [
    {
      id: "new_task",
      label: "Start New CEO Task",
      category: "Actions",
      icon: "✨",
      shortcut: "⌘N",
      action: () => {
        onSelectAction("new_task");
        onClose();
      },
    },
    {
      id: "talk_jarvis",
      label: "Activate Jarvis Voice Assistant",
      category: "Actions",
      icon: "🎙️",
      shortcut: "Space",
      action: () => {
        onSelectAction("talk_jarvis");
        onClose();
      },
    },
    {
      id: "view_running",
      label: "View Running Autonomous Tasks",
      category: "Navigation",
      icon: "⚡",
      action: () => {
        onSelectAction("view_running");
        onClose();
      },
    },
    {
      id: "pause_agents",
      label: "Pause All Active Agents",
      category: "System",
      icon: "⏸️",
      action: () => {
        onSelectAction("pause_all");
        onClose();
      },
    },
    {
      id: "open_computer",
      label: "Open macOS Computer Control Preview",
      category: "Navigation",
      icon: "🖥️",
      action: () => {
        onSelectAction("open_computer");
        onClose();
      },
    },
    {
      id: "open_browser",
      label: "Inspect Browser Session",
      category: "Navigation",
      icon: "🌐",
      action: () => {
        onSelectAction("open_browser");
        onClose();
      },
    },
    {
      id: "search_memory",
      label: "Search Episodic & Semantic Memory",
      category: "Navigation",
      icon: "🧠",
      action: () => {
        onSelectAction("search_memory");
        onClose();
      },
    },
    {
      id: "switch_gemini",
      label: "Set Primary Model: Gemini 3.7 Flash",
      category: "Models",
      icon: "💎",
      action: () => {
        onSelectAction("model_gemini");
        onClose();
      },
    },
  ];

  const filteredCommands = defaultCommands.filter(
    (c) =>
      c.label.toLowerCase().includes(query.toLowerCase()) ||
      c.category.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="commandPaletteOverlay" onClick={onClose}>
      <div
        className="commandPaletteModal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="commandInputRow">
          <span className="searchIcon">🔍</span>
          <input
            type="text"
            className="commandInputField"
            placeholder="Type a command or search actions... (ESC to exit)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          <kbd className="commandKbdBadge">ESC</kbd>
        </div>

        <div className="commandResultsList">
          {filteredCommands.length === 0 ? (
            <div className="emptyResults">No matching commands found.</div>
          ) : (
            filteredCommands.map((cmd) => (
              <button
                key={cmd.id}
                className="commandItemBtn"
                onClick={cmd.action}
              >
                <span className="cmdIcon">{cmd.icon}</span>
                <span className="cmdLabel">{cmd.label}</span>
                <span className="cmdCategory">{cmd.category}</span>
                {cmd.shortcut && (
                  <kbd className="cmdShortcut">{cmd.shortcut}</kbd>
                )}
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
});
