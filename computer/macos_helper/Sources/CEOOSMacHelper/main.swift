import AppKit
import ApplicationServices
import Foundation

private let protocolVersion = 1
private let maxInputBytes = 65_536
private let bundlePattern = try! NSRegularExpression(
    pattern: #"^[A-Za-z0-9][A-Za-z0-9.-]{1,254}$"#
)

private struct Request: Decodable {
    let id: String
    let version: Int
    let action: String
    let bundle_id: String?
    let text: String?
    let key: String?
    let modifiers: [String]?
}

private struct HelperFailure: Error {
    let code: String
    let message: String
}

private func emit(_ value: [String: Any], exitCode: Int32 = 0) -> Never {
    let data = try! JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
    FileHandle.standardOutput.write(data)
    FileHandle.standardOutput.write(Data("\n".utf8))
    exit(exitCode)
}

private func fail(id: String?, code: String, message: String) -> Never {
    emit([
        "id": id ?? "unknown",
        "version": protocolVersion,
        "ok": false,
        "error": ["code": code, "message": message],
    ], exitCode: 1)
}

private func validateBundleID(_ value: String?) throws -> String {
    guard let value else { throw HelperFailure(code: "missing_argument", message: "bundle_id is required") }
    let range = NSRange(value.startIndex..<value.endIndex, in: value)
    guard bundlePattern.firstMatch(in: value, range: range) != nil else {
        throw HelperFailure(code: "invalid_bundle_id", message: "bundle_id has an invalid format")
    }
    return value
}

private func runningApplication(_ bundleID: String) -> NSRunningApplication? {
    NSRunningApplication.runningApplications(withBundleIdentifier: bundleID).first
}

private func appPayload(_ app: NSRunningApplication) -> [String: Any] {
    [
        "bundle_id": app.bundleIdentifier ?? "",
        "name": app.localizedName ?? "",
        "path": app.bundleURL?.path ?? "",
        "running": !app.isTerminated,
        "frontmost": app.isActive,
        "pid": app.processIdentifier,
    ]
}

private func listApplications() -> [[String: Any]] {
    let workspace = NSWorkspace.shared
    let roots = [URL(fileURLWithPath: "/Applications"), URL(fileURLWithPath: "/System/Applications")]
    var records: [String: [String: Any]] = [:]
    for root in roots {
        guard let entries = try? FileManager.default.contentsOfDirectory(
            at: root, includingPropertiesForKeys: [.isApplicationKey], options: [.skipsHiddenFiles]
        ) else { continue }
        for url in entries where url.pathExtension == "app" {
            guard let bundle = Bundle(url: url), let identifier = bundle.bundleIdentifier else { continue }
            records[identifier] = [
                "bundle_id": identifier,
                "name": (bundle.object(forInfoDictionaryKey: "CFBundleDisplayName") as? String)
                    ?? (bundle.object(forInfoDictionaryKey: "CFBundleName") as? String)
                    ?? url.deletingPathExtension().lastPathComponent,
                "path": url.path,
                "running": runningApplication(identifier) != nil,
                "frontmost": NSWorkspace.shared.frontmostApplication?.bundleIdentifier == identifier,
            ]
        }
    }
    for app in workspace.runningApplications where app.bundleIdentifier != nil {
        records[app.bundleIdentifier!] = appPayload(app)
    }
    return records.values.sorted {
        String(describing: $0["name"]).localizedCaseInsensitiveCompare(
            String(describing: $1["name"])
        ) == .orderedAscending
    }
}

private func requireAccessibility() throws {
    guard AXIsProcessTrusted() else {
        throw HelperFailure(
            code: "accessibility_permission_required",
            message: "CEO OS does not have macOS Accessibility permission"
        )
    }
}

private func requireFrontmost(_ bundleID: String) throws {
    guard NSWorkspace.shared.frontmostApplication?.bundleIdentifier == bundleID else {
        throw HelperFailure(code: "target_not_frontmost", message: "Target application is not frontmost")
    }
}

private func keyCode(for key: String) throws -> CGKeyCode {
    let codes: [String: CGKeyCode] = [
        "return": 36, "tab": 48, "space": 49, "delete": 51, "escape": 53,
        "left": 123, "right": 124, "down": 125, "up": 126,
    ]
    guard let code = codes[key] else {
        throw HelperFailure(code: "unsupported_key", message: "Key is not allowlisted")
    }
    return code
}

private func flags(for modifiers: [String]) throws -> CGEventFlags {
    var flags: CGEventFlags = []
    for modifier in modifiers {
        switch modifier {
        case "command": flags.insert(.maskCommand)
        case "control": flags.insert(.maskControl)
        case "option": flags.insert(.maskAlternate)
        case "shift": flags.insert(.maskShift)
        default: throw HelperFailure(code: "unsupported_modifier", message: "Modifier is not allowlisted")
        }
    }
    return flags
}

let input = FileHandle.standardInput.readDataToEndOfFile()
guard input.count <= maxInputBytes else { fail(id: nil, code: "request_too_large", message: "Request exceeds size limit") }

private let request: Request
do {
    request = try JSONDecoder().decode(Request.self, from: input)
} catch {
    fail(id: nil, code: "invalid_json", message: "Request must be valid protocol JSON")
}

guard request.version == protocolVersion else {
    fail(id: request.id, code: "unsupported_version", message: "Only protocol version 1 is supported")
}

do {
    var result: [String: Any]
    switch request.action {
    case "status":
        result = [
            "platform": "macos",
            "helper_version": "1.0.0",
            "accessibility_trusted": AXIsProcessTrusted(),
            "frontmost_bundle_id": NSWorkspace.shared.frontmostApplication?.bundleIdentifier as Any,
        ]
    case "list_apps":
        result = ["applications": listApplications()]
    case "open_app":
        let bundleID = try validateBundleID(request.bundle_id)
        guard let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: bundleID) else {
            throw HelperFailure(code: "application_not_found", message: "No application has that bundle identifier")
        }
        let semaphore = DispatchSemaphore(value: 0)
        var launched: NSRunningApplication?
        var launchError: Error?
        NSWorkspace.shared.openApplication(at: url, configuration: .init()) { app, error in
            launched = app
            launchError = error
            semaphore.signal()
        }
        guard semaphore.wait(timeout: .now() + 10) == .success else {
            throw HelperFailure(code: "launch_timeout", message: "Application launch timed out")
        }
        if let launchError { throw HelperFailure(code: "launch_failed", message: launchError.localizedDescription) }
        guard let launched else { throw HelperFailure(code: "launch_failed", message: "Application did not launch") }
        result = ["application": appPayload(launched)]
    case "focus_app":
        let bundleID = try validateBundleID(request.bundle_id)
        guard let app = runningApplication(bundleID) else {
            throw HelperFailure(code: "application_not_running", message: "Application is not running")
        }
        guard app.activate(options: []) else {
            throw HelperFailure(code: "focus_failed", message: "Application could not be activated")
        }
        result = ["application": appPayload(app)]
    case "type_text":
        let bundleID = try validateBundleID(request.bundle_id)
        guard let value = request.text, value.utf8.count <= 10_000 else {
            throw HelperFailure(code: "invalid_text", message: "text is required and limited to 10000 UTF-8 bytes")
        }
        try requireAccessibility()
        try requireFrontmost(bundleID)
        guard let source = CGEventSource(stateID: .hidSystemState),
              let event = CGEvent(keyboardEventSource: source, virtualKey: 0, keyDown: true) else {
            throw HelperFailure(code: "event_creation_failed", message: "Could not create keyboard event")
        }
        let units = Array(value.utf16)
        event.keyboardSetUnicodeString(stringLength: units.count, unicodeString: units)
        event.post(tap: .cghidEventTap)
        result = ["bundle_id": bundleID, "typed_utf8_bytes": value.utf8.count]
    case "key_press":
        let bundleID = try validateBundleID(request.bundle_id)
        let code = try keyCode(for: request.key ?? "")
        let eventFlags = try flags(for: request.modifiers ?? [])
        try requireAccessibility()
        try requireFrontmost(bundleID)
        guard let source = CGEventSource(stateID: .hidSystemState),
              let down = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: true),
              let up = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: false) else {
            throw HelperFailure(code: "event_creation_failed", message: "Could not create keyboard event")
        }
        down.flags = eventFlags
        up.flags = eventFlags
        down.post(tap: .cghidEventTap)
        up.post(tap: .cghidEventTap)
        result = ["bundle_id": bundleID, "key": request.key ?? "", "modifiers": request.modifiers ?? []]
    default:
        throw HelperFailure(code: "unsupported_action", message: "Action is not supported")
    }
    emit(["id": request.id, "version": protocolVersion, "ok": true, "result": result])
} catch let error as HelperFailure {
    fail(id: request.id, code: error.code, message: error.message)
} catch {
    fail(id: request.id, code: "internal_error", message: "Helper operation failed")
}
