export const terminalStatuses = new Set(["success", "partial_success", "failed", "cancelled"]);
export function availableTaskActions(status) { if(terminalStatuses.has(status)) return []; return status === "waiting" ? ["resume", "cancel"] : ["pause", "cancel"]; }
export function groupCapabilities(capabilities) { return capabilities.reduce((groups, capability) => { const domain=capability.name.split(".")[0]||"other"; (groups[domain]??=[]).push(capability); return groups; },{}); }
