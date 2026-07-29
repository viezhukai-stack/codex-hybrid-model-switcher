@echo off
setlocal
cd /d "%~dp0"

set "PACKAGE_VERSION="
if exist "%~dp0VERSION.txt" set /p PACKAGE_VERSION=<"%~dp0VERSION.txt"
set "PROJECT_TOML=%~dp0payload\codex-hybrid-model-switcher\pyproject.toml"
if not exist "%PROJECT_TOML%" set "PROJECT_TOML=%~dp0..\..\pyproject.toml"
if not defined PACKAGE_VERSION if exist "%PROJECT_TOML%" for /f "tokens=2 delims==" %%V in ('findstr /B /C:"version = " "%PROJECT_TOML%"') do set "PACKAGE_VERSION=%%V"
if defined PACKAGE_VERSION set "PACKAGE_VERSION=%PACKAGE_VERSION: =%"
if defined PACKAGE_VERSION set "PACKAGE_VERSION=%PACKAGE_VERSION:"=%"
if not defined PACKAGE_VERSION (
  echo Package version could not be read from VERSION.txt or pyproject.toml.
  pause
  exit /b 1
)

set "PAYLOAD_SCRIPT=%~dp0payload\codex-hybrid-model-switcher\scripts\windows-live-audio.ps1"
set "INSTALLED_SCRIPT=%LOCALAPPDATA%\CodexHybridModelSwitcher\releases\v%PACKAGE_VERSION%\project\scripts\windows-live-audio.ps1"
set "LIVE_AUDIO_SCRIPT="
if exist "%INSTALLED_SCRIPT%" set "LIVE_AUDIO_SCRIPT=%INSTALLED_SCRIPT%"
if not defined LIVE_AUDIO_SCRIPT if exist "%PAYLOAD_SCRIPT%" set "LIVE_AUDIO_SCRIPT=%PAYLOAD_SCRIPT%"

if not defined LIVE_AUDIO_SCRIPT (
  echo Codex Live audio repair script was not found.
  echo Run Install Codex Hybrid.cmd first, then try again.
  goto :finish
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%LIVE_AUDIO_SCRIPT%" -Action Doctor
echo.
echo Fully quit Codex before applying or restoring Live audio settings.
echo Type REPAIR to create a backup and apply the recommended repair.
echo Type RESTORE to restore the newest Live audio backup.
echo Press Enter to leave settings unchanged.
set /p LIVE_AUDIO_ACTION=Choice:

if /I "%LIVE_AUDIO_ACTION%"=="REPAIR" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%LIVE_AUDIO_SCRIPT%" -Action Repair -Confirm REPAIR
) else if /I "%LIVE_AUDIO_ACTION%"=="RESTORE" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%LIVE_AUDIO_SCRIPT%" -Action Restore -Confirm RESTORE
) else (
  echo No audio setting was changed.
)

:finish
echo.
echo Press any key to close this window.
pause >nul
