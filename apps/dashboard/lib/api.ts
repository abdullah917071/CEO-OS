/**
 * Dynamic API and WebSocket configuration for CEO OS Dashboard.
 * Supports localhost development, LAN access, remote deployments, reverse proxies, and HTTPS/WSS.
 */

export function getApiUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "");
  }
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;
    // When running on local dev frontend port (3000, 3001, 3005, 5173, etc.), route API calls to FastAPI port 8000
    if (
      window.location.port !== "8000" &&
      (hostname === "localhost" || hostname === "127.0.0.1" || hostname.endsWith(".local"))
    ) {
      return `${protocol}//${hostname}:8000`;
    }
    return window.location.origin;
  }
  return "http://localhost:8000";
}

export function getWsUrl(path: string = ""): string {
  const cleanPath = path ? (path.startsWith("/") ? path : `/${path}`) : "";
  if (process.env.NEXT_PUBLIC_WS_URL) {
    const base = process.env.NEXT_PUBLIC_WS_URL.replace(/\/ws\/.*$/, "").replace(/\/$/, "");
    return `${base}${cleanPath}`;
  }
  if (typeof window !== "undefined") {
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const hostname = window.location.hostname;
    if (
      window.location.port !== "8000" &&
      (hostname === "localhost" || hostname === "127.0.0.1" || hostname.endsWith(".local"))
    ) {
      return `${wsProto}//${hostname}:8000${cleanPath}`;
    }
    return `${wsProto}//${window.location.host}${cleanPath}`;
  }
  return `ws://localhost:8000${cleanPath}`;
}

export const API = getApiUrl();
export const WS = getWsUrl();
export const WS_EVENTS = getWsUrl("/ws/events");

export async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const base = typeof window !== "undefined" ? getApiUrl() : API;
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const response = await fetch(`${base}${cleanPath}`, {
    cache: "no-store",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as { detail?: unknown; message?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
      else if (typeof body.message === "string") detail = body.message;
    } catch {}
    throw new Error(detail);
  }
  return (await response.json()) as T;
}

export function formatDate(value: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function summarizePayload(payload: Record<string, unknown>): string {
  for (const key of ["objective", "status", "capability", "message", "title", "summary"]) {
    if (typeof payload[key] === "string") return String(payload[key]);
  }
  const keys = Object.keys(payload);
  return keys.length ? keys.slice(0, 3).join(", ") : "No additional detail";
}
