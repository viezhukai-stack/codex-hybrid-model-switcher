@echo off
setlocal
cd /d "%~dp0.."
echo Restoring Codex 19030 Mode...
echo Quit Codex Desktop completely before running this.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\windows-hot-router-mode.ps1" -Action restore -Config "%USERPROFILE%\.codex-hybrid-model-switcher\config.json"
echo.
echo Press any key to close.
pause >nul
