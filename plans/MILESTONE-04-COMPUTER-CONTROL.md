# Milestone 4 — Computer Control Execution Plan

`PLANS.md` remains the immutable governing roadmap. This file defines the concrete delivery and
acceptance contract for its Computer Control milestone.

Status: implemented and automated checks verified on 2026-08-15. The owner-controlled live typing
smoke test remains pending because macOS reports Accessibility permission as disabled.

## Objective

Provide deterministic, cancellable macOS application and Accessibility control behind a narrow,
versioned local interface. The CEO runtime discovers typed capabilities and never imports AppKit,
Accessibility, subprocess, or helper implementation details.

## Scope and decisions

- Preserve the execution ladder: direct function, existing allowlisted shell, macOS Accessibility.
  Browser DOM and vision remain Milestones 5 and 6.
- A Swift executable owns macOS APIs. It accepts one JSON request per invocation and emits one JSON
  response, keeping the protocol stateless, inspectable, bounded, and independently testable.
- Protocol V1 supports `status`, `list_apps`, `open_app`, `focus_app`, `type_text`, and `key_press`.
  It never accepts shell commands, AppleScript, arbitrary code, screen coordinates, or secrets.
- Applications are addressed by bundle identifier. Discovery returns bundle identifier, display
  name, path, and running state. Input text and identifiers have strict size/format bounds.
- The Python controller serializes input ownership, records current application/action state, and
  checks a generation-based global stop token before and after helper calls.
- Read capabilities are always available on macOS. Effects require explicit configuration and an
  application allowlist. Text entry and key presses additionally require trusted Accessibility
  permission. Containers and non-macOS hosts report unsupported instead of pretending success.
- Every successful effect returns helper evidence and the observed post-action state. Capability
  risk is R0 for status/discovery and R1 for local application/input operations; policy is enforced
  immediately before execution.
- No screenshots, clipboard content, mouse coordinates, browser automation, or vision are added in
  this milestone.

## Capability interface

- `computer.status`: platform, helper/protocol version, support, permission, policy, and active state.
- `computer.apps.list`: installed/running application inventory.
- `computer.app.open`: launch an allowlisted bundle identifier and verify it is running.
- `computer.app.focus`: activate an allowlisted running application and verify it is frontmost.
- `computer.text.type`: type bounded UTF-8 text into the allowed frontmost application.
- `computer.key.press`: send one allowlisted key with bounded modifiers.
- `computer.stop`: invalidate active ownership and reject stale or subsequent effects until resumed
  through the local controller boundary.

## Acceptance tests

- The Swift helper builds on macOS with warnings treated as errors and returns a valid V1 `status`
  response.
- Malformed JSON, unsupported protocol versions/actions, invalid bundle identifiers, oversized
  text, and unsupported keys fail closed with structured errors.
- The Python client validates request/response IDs, protocol version, timeout, exit status, and
  output size; it never invokes a shell.
- Effects are denied by default, limited to configured bundle identifiers when enabled, and input
  requires the target to be the verified frontmost application.
- Global stop invalidates an in-flight action and blocks new effects; resume creates a fresh
  generation without replaying the cancelled action.
- Capability outputs include evidence derived from the helper response; unsupported environments
  are reported truthfully.
- Planner support for explicit open/focus/type requests uses the typed computer capabilities and
  unsupported requests remain non-operative.
- Existing API, durable runtime, memory, tool-safety, dashboard, static, dependency, and container
  checks remain green.

## Manual owner-controlled acceptance

When Accessibility permission and effect configuration are explicitly enabled, run the smoke flow:
open TextEdit by bundle identifier, focus it, type a unique harmless sentence, and verify TextEdit is
frontmost. Saving to Desktop is excluded because filesystem writes remain workspace-scoped and a
safe save-dialog policy has not yet been designed.

## Verification result

- Swift Package Manager built the release helper with warnings treated as errors.
- Live helper checks passed for V1 status and structured rejection of invalid JSON, protocol
  versions, bundle identifiers, oversized text, unsupported actions, and unsupported keys.
- Twenty-nine backend tests passed, including policy default-deny, bundle allowlisting, verified
  frontmost input, in-flight global cancellation, no replay after resume, IPC validation, typed
  planner routing, and direct owner stop/resume endpoints.
- The Linux API container reports computer control as unsupported, exposes only R0 computer
  discovery capabilities under the default policy, and remains healthy with PostgreSQL and Redis.
- The live typing smoke test was not attempted because `accessibility_trusted` is `false`; no
  permission prompt or GUI effect was triggered implicitly.
