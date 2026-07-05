@echo off
setlocal
cd /d "%~dp0.."
echo Enabling Codex Hot Router Mode...
echo Quit Codex Desktop completely before running this.
echo The hot router must already be running on 127.0.0.1:19032.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\windows-hot-router-mode.ps1" -Action enable -Config "%USERPROFILE%\.codex-hybrid-model-switcher\config.json"
echo.
echo Press any key to close.
pause >nul
