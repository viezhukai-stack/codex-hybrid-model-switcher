@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\windows-provider-menu.ps1" -Config "%USERPROFILE%\.codex-hybrid-model-switcher\config.json"
echo.
pause
