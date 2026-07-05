@echo off
setlocal
cd /d "%~dp0"

set "PAYLOAD_START=%~dp0payload\codex-hybrid-model-switcher\scripts\windows-hot-router-start.ps1"
set "INSTALLED_ROOT=%LOCALAPPDATA%\CodexHybridModelSwitcher\releases\v2.17.5\project"
set "INSTALLED_START=%INSTALLED_ROOT%\scripts\windows-hot-router-start.ps1"

if exist "%INSTALLED_START%" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%INSTALLED_START%" %*
) else if exist "%PAYLOAD_START%" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%PAYLOAD_START%" %*
) else (
  echo Hot router start script was not found.
  echo Run Install Codex Hybrid.cmd first, then try again.
)

echo.
echo Press any key to close this window.
pause >nul
