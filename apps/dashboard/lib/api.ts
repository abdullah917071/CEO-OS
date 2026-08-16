export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
// WS is the bare WebSocket host — consumers append their own path (e.g. /ws/tasks)
export const WS = (process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000").replace(/\/ws\/.*$/, "");
// The legacy events stream for the shell
export const WS_EVENTS = `${WS}/ws/events`;
export async function requestJson<T>(path:string, init?:RequestInit):Promise<T> { const response=await fetch(`${API}${path}`,{cache:"no-store",...init}); if(!response.ok){let detail=`${response.status} ${response.statusText}`; try{const body=await response.json() as {detail?:unknown}; if(typeof body.detail==="string") detail=body.detail;}catch{} throw new Error(detail);} return await response.json() as T; }
export function formatDate(value:string):string { return new Intl.DateTimeFormat(undefined,{dateStyle:"medium",timeStyle:"short"}).format(new Date(value)); }
export function summarizePayload(payload:Record<string,unknown>):string { for(const key of ["objective","status","capability","message"]){if(typeof payload[key]==="string") return String(payload[key]);} const keys=Object.keys(payload); return keys.length?keys.slice(0,3).join(", "):"No additional detail"; }
