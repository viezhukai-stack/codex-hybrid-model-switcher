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
set "PAYLOAD_SCRIPT=%~dp0payload\codex-hybrid-model-switcher\scripts\windows-update-orchestrate.ps1"
set "INSTALLED_SCRIPT=%LOCALAPPDATA%\CodexHybridModelSwitcher\releases\v%PACKAGE_VERSION%\project\scripts\windows-update-orchestrate.ps1"

echo Fully quit Codex Desktop before continuing.
echo This entry may complete the official Store registration and refresh Browser/Chrome.
echo.
if exist "%INSTALLED_SCRIPT%" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%INSTALLED_SCRIPT%" -Apply %*
) else if exist "%PAYLOAD_SCRIPT%" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%PAYLOAD_SCRIPT%" -Apply %*
) else (
  echo Codex update orchestrator was not found.
  echo Run Install Codex Hybrid.cmd first, then try again.
)

echo.
echo Press any key to close this window.
pause >nul
