#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "   🚀 Setting up Jarvis macOS Voice Assistant"
echo "=========================================================="

mkdir -p "$HOME/Library/Application Support/Jarvis"
chmod 700 "$HOME/Library/Application Support/Jarvis"
mkdir -p ./data/secrets
mkdir -p ./data/jarvis

echo "✓ Jarvis directories initialized"
echo "✓ To launch Jarvis standalone: uv run python -m jarvis.main"
echo "✓ To launch web dashboard: npm --prefix apps/dashboard run dev"
