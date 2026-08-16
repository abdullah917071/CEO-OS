"use client";

import React, { useState } from "react";
import { AppShell } from "../../components/app-shell";
import { CommunicationsIcon, CheckIcon } from "../../components/icons";

interface CommItem {
  id: string;
  source: "Email" | "WhatsApp" | "Telegram" | "Call";
  sender: string;
  subject: string;
  preview: string;
  receivedAt: string;
  requiresAction?: boolean;
}

const DEMO_COMMS: CommItem[] = [
  {
    id: "comm_1",
    source: "Email",
    sender: "investors@vcpartner.com",
    subject: "Q3 Strategic Update & Margin Projections",
    preview: "Could you share the updated margin models and competitor differentiation deck by EOD tomorrow?",
    receivedAt: "10m ago",
    requiresAction: true,
  },
  {
    id: "comm_2",
    source: "WhatsApp",
    sender: "Partner Lead (Swiggy Merchant Ops)",
    subject: "Tier 1 Enterprise Agreement",
    preview: "Sent over the drafted contract terms for review.",
    receivedAt: "1h ago",
    requiresAction: false,
  },
];

export default function CommunicationsPage() {
  const [comms] = useState<CommItem[]>(DEMO_COMMS);
  const [selectedComm, setSelectedComm] = useState<CommItem | null>(DEMO_COMMS[0]);

  const contextContent = selectedComm ? (
    <>
      <div className="contextPanelHeader">
        <span>Message Actions</span>
        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{selectedComm.source}</span>
      </div>

      <div className="contextPanelBody">
        <div className="contextSection">
          <strong style={{ fontSize: "13px", color: "var(--text-primary)" }}>{selectedComm.subject}</strong>
          <div style={{ fontSize: "12px", color: "var(--text-secondary)", marginTop: "2px" }}>
            From: {selectedComm.sender}
          </div>
          <div style={{ fontSize: "13px", color: "var(--text-primary)", marginTop: "8px", lineHeight: "1.5" }}>
            {selectedComm.preview}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <button
            type="button"
            style={{
              padding: "8px",
              borderRadius: "var(--radius-md)",
              background: "var(--accent-primary)",
              color: "#FFFFFF",
              fontSize: "12px",
              fontWeight: 600,
            }}
            onClick={() => alert("Joice is drafting a reply...")}
          >
            Ask Joice to Draft Reply
          </button>
          <button
            type="button"
            style={{
              padding: "8px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-strong)",
              background: "var(--bg-surface)",
              fontSize: "12px",
              fontWeight: 500,
            }}
            onClick={() => alert("Created follow-up task in Joice.")}
          >
            Create Task from Email
          </button>
        </div>
      </div>
    </>
  ) : null;

  return (
    <AppShell currentRouteName="Communications" contextPanelContent={contextContent}>
      <div className="pageContainer">
        <div className="pageHeader">
          <div>
            <h1 className="pageTitle">Communications</h1>
            <p className="pageSubtitle">
              Unified inbox allowing Joice to synthesize threads and draft executive replies.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {comms.map((c) => (
            <div
              key={c.id}
              onClick={() => setSelectedComm(c)}
              style={{
                background: selectedComm?.id === c.id ? "var(--bg-surface-subtle)" : "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
                borderRadius: "var(--radius-lg)",
                padding: "12px 16px",
                cursor: "pointer",
                display: "flex",
                flexDirection: "column",
                gap: "4px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <span style={{ fontSize: "11px", fontWeight: 600, color: "var(--accent-primary)" }}>
                    {c.source}
                  </span>
                  <strong style={{ fontSize: "13px", color: "var(--text-primary)" }}>{c.sender}</strong>
                </div>
                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>{c.receivedAt}</span>
              </div>
              <div style={{ fontSize: "13px", fontWeight: 600, color: "var(--text-primary)" }}>{c.subject}</div>
              <div style={{ fontSize: "13px", color: "var(--text-secondary)" }}>{c.preview}</div>
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
