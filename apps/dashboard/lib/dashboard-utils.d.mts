import type { Capability } from "./contracts";
export const terminalStatuses:Set<string>;
export function availableTaskActions(status:string):Array<"pause"|"resume"|"cancel">;
export function groupCapabilities(capabilities:Capability[]):Record<string,Capability[]>;
