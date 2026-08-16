# Computer Control

Computer actions follow a strict preference ladder: direct deterministic function, command line, browser DOM/CDP, macOS Accessibility, then vision-guided mouse/keyboard. The router chooses the highest reliable tier, not merely the most human-like one.

The subsystem will maintain application/window/screen state, foreground ownership, clipboard state, screenshots, and a cancel token. A Swift helper will expose narrowly scoped macOS Accessibility operations through a versioned local IPC contract.

All operations declare required permissions, target scope, verification method, and rollback support. Visual content is untrusted data. The global stop control must prevent new input and release any active automation ownership immediately.

Milestone 4 adds native control; Milestone 6 adds visual fallback. Phase 1 filesystem and shell tools are not general computer control.

## Native control implementation

The macOS helper is a Swift executable with a versioned JSON protocol. It supports status,
application discovery, application launch/focus, bounded Unicode text entry, and a small allowlist
of keyboard keys and modifiers. It accepts no shell, AppleScript, arbitrary code, coordinates, or
model-authored executable payloads.

The Python client starts the helper directly without a shell and validates request identity,
protocol version, response structure, exit status, timeout, and response size. A controller
serializes input ownership and maintains the frontmost application, current action, stop state, and
cancellation generation.

Effects are disabled by default. Enabling them requires
`CEO_OS_COMPUTER_EFFECTS_ENABLED=true` and an explicit comma-separated bundle allowlist in
`CEO_OS_COMPUTER_ALLOWED_BUNDLE_IDS`. Input is rejected unless the helper verifies that the target
bundle is frontmost, and macOS Accessibility permission is required for keyboard events.

The owner can call `/api/v1/computer/stop` without queuing a CEO task. This cancels the active helper
request, invalidates its generation, and blocks subsequent effects. `/api/v1/computer/resume`
creates a fresh generation and never replays the cancelled effect. Status is available at
`/api/v1/computer/status`; containers and non-macOS systems report unsupported truthfully.

## Cua Driver visual fallback

Milestone 6 wraps the version-bounded Cua Driver Python SDK behind CEO OS-owned protocols. The
in-process runtime is created and shut down with the API lifecycle. Only a narrow window-scoped
surface is admitted: list windows, capture one exact window, and optionally perform bounded click,
type, key, or scroll actions. Generic driver calls, desktop scope, unrestricted permission mode,
existing browser profiles, and replay are not exposed.

Every target must come from the latest window listing and binds an exact PID and window ID. Effects
also require `CEO_OS_VISION_EFFECTS_ENABLED=true` and an exact application-name allowlist in
`CEO_OS_VISION_ALLOWED_APP_NAMES`. Background delivery is the default. Foreground delivery is
rejected unless the caller selects it explicitly and
`CEO_OS_VISION_FOREGROUND_ESCALATION_ENABLED=true`; desktop control is not exposed.

Screenshot bytes remain internal. Capability results contain MIME type, byte count, SHA-256 digest,
bounded snapshot metadata, and an `untrusted_screen_content` marker. Cua action effect, delivery,
route, degraded state, and verification are preserved as evidence. Unknown completion is never
retried automatically. Pixel actions require a current capture of the same PID/window. CEO OS maps
captured-image coordinates into the native window frame and can require an independently observed
exact window-title postcondition before reporting success.

The owner endpoints are `/api/v1/vision/status`, `/api/v1/vision/stop`, and
`/api/v1/vision/resume`. Stop cancels the admitted operation and advances a generation; resume opens
a new generation without replay.

On macOS, live window capture requires Screen Recording and effects require Accessibility under the
responsible Cua Driver/host identity. Configuration and contract tests run without those grants and
status remains truthful when they are absent. On the development Mac, both grants and direct capture
were verified on 2026-08-15. A live canvas-only fixture then passed capture, foreground click, and
independent title-transition verification without degraded output.
