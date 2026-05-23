@echo off
setlocal
cd /d "%~dp0"
echo Installing enterprise-drawio-diagrammer into local Codex, Claude Code, and GitHub Copilot skills directories...
py -3 install.py --all-local --yes
if errorlevel 1 (
  echo.
  echo Install failed. If Python Launcher is unavailable, try:
  echo python install.py --all-local --yes
  pause
  exit /b 1
)
echo.
echo Install complete. Restart Codex, Claude Code, or GitHub Copilot if needed.
pause
