"use client";

import { useEffect, useMemo, useState } from "react";
import { requestJson } from "../../lib/api";
import type {
  Capability,
  IntegrationStatus,
  OAuthTokenRecord,
  SecretReference,
} from "../../lib/contracts";
import { groupCapabilities } from "../../lib/dashboard-utils.mjs";

type TabMode = "integrations" | "capabilities" | "secrets";

function healthBadge(health: string) {
  const map: Record<string, string> = {
    healthy: "success",
    degraded: "warning",
    unavailable: "failed",
    unknown: "queued",
  };
  return map[health] ?? "queued";
}

export default function IntegrationsPage() {
  const [tab, setTab] = useState<TabMode>("integrations");
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [secrets, setSecrets] = useState<SecretReference[]>([]);
  const [oauthTokens, setOAuthTokens] = useState<OAuthTokenRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [installSuccess, setInstallSuccess] = useState<string | null>(null);

  // Search & Filter
  const [capSearch, setCapSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("all");

  // Form state for MCP
  const [serverName, setServerName] = useState("");
  const [command, setCommand] = useState("python3");
  const [args, setArgs] = useState("");
  const [domain, setDomain] = useState("integrations");
  const [riskCeiling, setRiskCeiling] = useState("R1");
  const [installing, setInstalling] = useState(false);

  const refreshAll = () => {
    requestJson<Capability[]>("/api/v1/capabilities")
      .then(setCapabilities)
      .catch((value) => setError(value instanceof Error ? value.message : "API unavailable"));
    requestJson<IntegrationStatus[]>("/api/v1/integrations")
      .then(setIntegrations)
      .catch(() => {});
    requestJson<SecretReference[]>("/api/v1/secrets")
      .then(setSecrets)
      .catch(() => {});
    requestJson<OAuthTokenRecord[]>("/api/v1/integrations/oauth/status")
      .then(setOAuthTokens)
      .catch(() => {});
  };

  useEffect(() => {
    refreshAll();
  }, []);

  const handleInstallMcp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!serverName.trim() || !command.trim()) return;
    setInstalling(true);
    setError(null);
    setInstallSuccess(null);
    try {
      const parsedArgs = args.trim() ? args.split(" ").filter(Boolean) : [];
      await requestJson<IntegrationStatus>("/api/v1/integrations/mcp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: serverName.trim(),
          command: command.trim(),
          args: parsedArgs,
          domain: domain.trim() || "integrations",
          risk_ceiling: riskCeiling,
          enabled: true,
        }),
      });
      setInstallSuccess(`Successfully installed and connected MCP server: ${serverName}`);
      setServerName("");
      setArgs("");
      refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to install MCP server");
    } finally {
      setInstalling(false);
    }
  };

  const handleUninstall = async (name: string) => {
    if (!confirm(`Uninstall integration '${name}'?`)) return;
    try {
      await requestJson(`/api/v1/integrations/${encodeURIComponent(name)}`, {
        method: "DELETE",
      });
      refreshAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to uninstall integration");
    }
  };

  const filteredCaps = useMemo(() => {
    return capabilities.filter((c) => {
      const matchesSearch =
        capSearch === "" ||
        c.name.toLowerCase().includes(capSearch.toLowerCase()) ||
        c.description.toLowerCase().includes(capSearch.toLowerCase());
      const matchesRisk =
        riskFilter === "all" || c.risk.toLowerCase() === riskFilter.toLowerCase();
      return matchesSearch && matchesRisk;
    });
  }, [capabilities, capSearch, riskFilter]);

  const groups = groupCapabilities(filteredCaps);

  return (
    <>
      <section className="pageIntro">
        <p className="eyebrow">INTEGRATION & CAPABILITY MATRIX</p>
        <h1>Integrations & MCP Platform</h1>
        <p>
          Manage native and MCP integrations, inspect typed capabilities across risk ceilings, and
          manage Secret Vault credentials.
        </p>
      </section>

      {/* Telemetry Stats */}
      <div className="statGrid">
        <div className="stat highlight">
          <span>CAPABILITIES REGISTERED</span>
          <strong>{capabilities.length}</strong>
          <small>Typed tools available to CEO</small>
        </div>
        <div className="stat">
          <span>ACTIVE INTEGRATIONS</span>
          <strong>{integrations.length}</strong>
          <small>Native & MCP adapters</small>
        </div>
        <div className="stat">
          <span>SECRET REFERENCES</span>
          <strong>{secrets.length}</strong>
          <small>Masked in vault</small>
        </div>
        <div className="stat">
          <span>ACTIVE OAUTH SESSIONS</span>
          <strong>{oauthTokens.length}</strong>
          <small>PKCE tokens leased</small>
        </div>
      </div>

      {error && <p className="notice error">CEO Error: {error}</p>}
      {installSuccess && <p className="notice success">{installSuccess}</p>}

      {/* Interactive Tabs */}
      <div className="tabNav">
        <button
          type="button"
          className={`tabButton ${tab === "integrations" ? "active" : ""}`}
          onClick={() => setTab("integrations")}
        >
          Connected Integrations <span>({integrations.length})</span>
        </button>
        <button
          type="button"
          className={`tabButton ${tab === "capabilities" ? "active" : ""}`}
          onClick={() => setTab("capabilities")}
        >
          Capability Matrix <span>({capabilities.length})</span>
        </button>
        <button
          type="button"
          className={`tabButton ${tab === "secrets" ? "active" : ""}`}
          onClick={() => setTab("secrets")}
        >
          Secret Vault & OAuth <span>({secrets.length})</span>
        </button>
      </div>

      {/* ── TAB 1: INTEGRATIONS ──────────────────────────────────────────── */}
      {tab === "integrations" && (
        <>
          {/* Dynamic MCP Install Form */}
          <div className="card" style={{ marginBottom: "28px" }}>
            <p className="eyebrow">DYNAMIC EXTENSIBILITY</p>
            <h3 style={{ margin: "6px 0 14px", font: "600 18px var(--font-sans)" }}>
              Install MCP Server Integration
            </h3>
            <form onSubmit={handleInstallMcp}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                  gap: "12px",
                  marginBottom: "14px",
                }}
              >
                <div>
                  <label style={{ fontSize: "11px", color: "var(--muted)" }}>Server Name</label>
                  <input
                    type="text"
                    style={{
                      width: "100%",
                      minHeight: "40px",
                      padding: "0 12px",
                      background: "var(--bg)",
                      border: "1px solid var(--border)",
                      color: "var(--ink)",
                      borderRadius: "var(--radius-sm)",
                    }}
                    placeholder="e.g. postgres_mcp"
                    value={serverName}
                    onChange={(e) => setServerName(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <label style={{ fontSize: "11px", color: "var(--muted)" }}>Command / Binary</label>
                  <input
                    type="text"
                    style={{
                      width: "100%",
                      minHeight: "40px",
                      padding: "0 12px",
                      background: "var(--bg)",
                      border: "1px solid var(--border)",
                      color: "var(--ink)",
                      borderRadius: "var(--radius-sm)",
                    }}
                    value={command}
                    onChange={(e) => setCommand(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <label style={{ fontSize: "11px", color: "var(--muted)" }}>Arguments (space separated)</label>
                  <input
                    type="text"
                    style={{
                      width: "100%",
                      minHeight: "40px",
                      padding: "0 12px",
                      background: "var(--bg)",
                      border: "1px solid var(--border)",
                      color: "var(--ink)",
                      borderRadius: "var(--radius-sm)",
                    }}
                    placeholder="-m mcp_server"
                    value={args}
                    onChange={(e) => setArgs(e.target.value)}
                  />
                </div>
                <div>
                  <label style={{ fontSize: "11px", color: "var(--muted)" }}>Risk Ceiling</label>
                  <select
                    className="filterSelect"
                    style={{ width: "100%", minHeight: "40px" }}
                    value={riskCeiling}
                    onChange={(e) => setRiskCeiling(e.target.value)}
                  >
                    <option value="R0">R0 - Read Only</option>
                    <option value="R1">R1 - Harmless Write</option>
                    <option value="R2">R2 - Reversible Action</option>
                    <option value="R3">R3 - Sensitive Action</option>
                  </select>
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <button type="submit" disabled={installing || !serverName.trim()}>
                  {installing ? "INSTALLING..." : "+ INSTALL MCP SERVER"}
                </button>
              </div>
            </form>
          </div>

          {/* Integrations Grid */}
          <div className="sectionTitle">
            <div>
              <p className="eyebrow">CONNECTED PLATFORMS</p>
              <h2>Installed Integrations</h2>
            </div>
            <span>{integrations.length} total</span>
          </div>

          <div className="cards integrationGrid">
            {integrations.map((item) => (
              <article className="card integrationCard" key={item.name}>
                <div className="integrationIcon">{item.name.slice(0, 3).toUpperCase()}</div>
                <div>
                  <div className="cardHead">
                    <span className={`status ${healthBadge(item.health)}`}>{item.health}</span>
                    <span>{item.integration_type.toUpperCase()}</span>
                  </div>

                  <h3 style={{ margin: "8px 0 4px", fontSize: "17px", fontWeight: "600" }}>
                    {item.name}
                  </h3>
                  <p style={{ color: "var(--muted)", fontSize: "12px", margin: "0 0 10px", lineHeight: "1.4" }}>
                    {item.description}
                  </p>

                  <div className="tagRow">
                    <span>{item.tool_count} capabilities</span>
                    <span className="riskBadge r1">{item.risk_ceiling}</span>
                    {item.domain && <span>{item.domain}</span>}
                  </div>

                  {item.integration_type === "mcp" && (
                    <div style={{ marginTop: "12px" }}>
                      <button
                        type="button"
                        className="danger"
                        style={{ minHeight: "32px", fontSize: "10px" }}
                        onClick={() => void handleUninstall(item.name)}
                      >
                        UNINSTALL
                      </button>
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        </>
      )}

      {/* ── TAB 2: CAPABILITY MATRIX ─────────────────────────────────────── */}
      {tab === "capabilities" && (
        <>
          <div className="searchBar">
            <input
              type="text"
              placeholder="Search capabilities by name, namespace, or action..."
              value={capSearch}
              onChange={(e) => setCapSearch(e.target.value)}
            />
            <select
              className="filterSelect"
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
            >
              <option value="all">All Risk Levels</option>
              <option value="r0">R0 - Read Only</option>
              <option value="r1">R1 - Harmless Write</option>
              <option value="r2">R2 - Policy Evaluated</option>
              <option value="r3">R3 - High Risk</option>
            </select>
          </div>

          <div style={{ display: "grid", gap: "24px" }}>
            {Object.entries(groups).map(([domainName, caps]) => (
              <div key={domainName} className="card">
                <div className="cardHead" style={{ marginBottom: "12px" }}>
                  <strong style={{ fontSize: "14px", color: "var(--green)", textTransform: "uppercase" }}>
                    {domainName} ({caps.length})
                  </strong>
                  <span>Domain Group</span>
                </div>

                <div className="capabilityList">
                  {caps.map((cap) => (
                    <span key={cap.name}>
                      <div>
                        <strong>{cap.name}</strong>
                        <small style={{ display: "block", marginTop: "2px" }}>{cap.description}</small>
                      </div>
                      <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                        <span className={`riskBadge ${cap.risk.toLowerCase()}`}>{cap.risk}</span>
                      </div>
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ── TAB 3: SECRET VAULT ──────────────────────────────────────────── */}
      {tab === "secrets" && (
        <>
          <div className="sectionTitle">
            <div>
              <p className="eyebrow">CREDENTIAL ISOLATION</p>
              <h2>Secret Vault References</h2>
            </div>
            <span>{secrets.length} credentials</span>
          </div>

          <div className="cards">
            {secrets.map((sec) => (
              <article className="card" key={sec.credential_id}>
                <div className="cardHead">
                  <span className="riskBadge r0">MASKED IN VAULT</span>
                  <span>ID: {sec.credential_id}</span>
                </div>
                <h3 style={{ margin: "10px 0 4px" }}>{sec.name}</h3>
                <p style={{ color: "var(--muted)", fontSize: "12px" }}>{sec.description}</p>
                <div className="tagRow">
                  {sec.tags.map((t) => (
                    <span key={t}>{t}</span>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </>
  );
}
