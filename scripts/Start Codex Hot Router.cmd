@echo off
setlocal
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\windows-hot-router-start.ps1" -Config "%USERPROFILE%\.codex-hybrid-model-switcher\config.json"
echo.
echo Router stopped. Press any key to close.
pause >nul
