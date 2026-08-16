"use client";

import Link from "next/link";
import React, { memo, useState } from "react";
import type { ConversationItem } from "../lib/contracts";

interface ChatSidebarProps {
  conversations: ConversationItem[];
  activeConversationId: string;
  onSelectConversation: (id: string) => void;
  onNewTask: () => void;
  onOpenCommandPalette: () => void;
}

export const ChatSidebar = memo(function ChatSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewTask,
  onOpenCommandPalette,
}: ChatSidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filtered = conversations.filter(
    (c) =>
      c.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.preview.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const groups = {
    today: filtered.filter((c) => c.category === "today"),
    yesterday: filtered.filter((c) => c.category === "yesterday"),
    previous_7_days: filtered.filter((c) => c.category === "previous_7_days"),
    older: filtered.filter((c) => c.category === "older"),
  };

  return (
    <nav className="sidebar" aria-label="Main Navigation">
      {/* Brand */}
      <div className="brand">
        <div className="brandMark" aria-hidden="true">
          <div className="innerDot" />
        </div>
        <div>
          <span className="brandTitle">CEO OS</span>
          <span className="brandSubtitle">Autonomous Intelligence</span>
        </div>
      </div>

      {/* New Task & Quick Search */}
      <div className="sidebarHeaderActions">
        <button className="btnNewTask" onClick={onNewTask}>
          <span>+</span> New Task
        </button>

        <div className="sidebarSearchBox" onClick={onOpenCommandPalette}>
          <span>🔍</span>
          <span className="searchPlaceholder">Search or ⌘K...</span>
        </div>
      </div>

      {/* Grouped History List */}
      <div className="historyGroupContainer">
        {groups.today.length > 0 && (
          <div className="historyGroup">
            <span className="historyGroupTitle">TODAY</span>
            {groups.today.map((item) => (
              <button
                key={item.id}
                className={`historyItemBtn ${item.id === activeConversationId ? "active" : ""}`}
                onClick={() => onSelectConversation(item.id)}
              >
                <span className="historyItemTitle">{item.title}</span>
                {item.status === "running" && <span className="historyRunningDot" />}
              </button>
            ))}
          </div>
        )}

        {groups.yesterday.length > 0 && (
          <div className="historyGroup">
            <span className="historyGroupTitle">YESTERDAY</span>
            {groups.yesterday.map((item) => (
              <button
                key={item.id}
                className={`historyItemBtn ${item.id === activeConversationId ? "active" : ""}`}
                onClick={() => onSelectConversation(item.id)}
              >
                <span className="historyItemTitle">{item.title}</span>
              </button>
            ))}
          </div>
        )}

        {groups.previous_7_days.length > 0 && (
          <div className="historyGroup">
            <span className="historyGroupTitle">PREVIOUS 7 DAYS</span>
            {groups.previous_7_days.map((item) => (
              <button
                key={item.id}
                className={`historyItemBtn ${item.id === activeConversationId ? "active" : ""}`}
                onClick={() => onSelectConversation(item.id)}
              >
                <span className="historyItemTitle">{item.title}</span>
              </button>
            ))}
          </div>
        )}

        {groups.older.length > 0 && (
          <div className="historyGroup">
            <span className="historyGroupTitle">OLDER</span>
            {groups.older.map((item) => (
              <button
                key={item.id}
                className={`historyItemBtn ${item.id === activeConversationId ? "active" : ""}`}
                onClick={() => onSelectConversation(item.id)}
              >
                <span className="historyItemTitle">{item.title}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Secondary Bottom Links */}
      <div className="sidebarFooterNav">
        <Link href="/tasks" className="navItemSmall">
          <span className="navGlyph">📋</span> Tasks
        </Link>
        <Link href="/agents" className="navItemSmall">
          <span className="navGlyph">🤖</span> Agents
        </Link>
        <Link href="/memory" className="navItemSmall">
          <span className="navGlyph">🧠</span> Memory
        </Link>
        <Link href="/integrations" className="navItemSmall">
          <span className="navGlyph">🔌</span> Integrations
        </Link>
        <Link href="/desktop" className="navItemSmall">
          <span className="navGlyph">🖥️</span> System
        </Link>
        <Link href="/settings" className="navItemSmall">
          <span className="navGlyph">⚙️</span> Settings
        </Link>
      </div>
    </nav>
  );
});
