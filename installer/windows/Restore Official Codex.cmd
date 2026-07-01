@echo off
setlocal
cd /d "%~dp0"

set "PAYLOAD_RESTORE=%~dp0payload\codex-hybrid-model-switcher\scripts\windows-restore-official.ps1"
set "INSTALLED_ROOT=%LOCALAPPDATA%\CodexHybridModelSwitcher\releases\v2.14.0\project"
set "INSTALLED_RESTORE=%INSTALLED_ROOT%\scripts\windows-restore-official.ps1"

if exist "%INSTALLED_RESTORE%" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%INSTALLED_RESTORE%" %*
) else if exist "%PAYLOAD_RESTORE%" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%PAYLOAD_RESTORE%" %*
) else (
  echo Restore script was not found.
  echo Run Install Codex Hybrid.cmd first, then try again.
)

echo.
echo Press any key to close this window.
pause >nul
