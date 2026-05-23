$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
Write-Host "Installing enterprise-drawio-diagrammer into local Codex, Claude Code, and GitHub Copilot skills directories..."
python .\install.py --all-local --yes
Write-Host ""
Write-Host "Install complete. Restart Codex, Claude Code, or GitHub Copilot if needed."
