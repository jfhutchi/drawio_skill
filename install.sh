#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
echo "Installing enterprise-drawio-diagrammer into local Codex, Claude Code, and GitHub Copilot skills directories..."
python3 ./install.py --all-local --yes
echo ""
echo "Install complete. Restart Codex, Claude Code, or GitHub Copilot if needed."
