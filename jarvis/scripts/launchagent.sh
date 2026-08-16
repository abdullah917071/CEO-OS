#!/usr/bin/env bash
set -e

PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$PLIST_DIR/com.ceo-os.jarvis.plist"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

mkdir -p "$PLIST_DIR"

cat <<EOF > "$PLIST_FILE"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ceo-os.jarvis</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/env</string>
        <string>uv</string>
        <string>run</string>
        <string>python</string>
        <string>-m</string>
        <string>jarvis.main</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/jarvis_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/jarvis_stderr.log</string>
</dict>
</plist>
EOF

chmod 644 "$PLIST_FILE"
echo "✓ Installed Jarvis LaunchAgent: $PLIST_FILE"
echo "To load manually: launchctl load $PLIST_FILE"
