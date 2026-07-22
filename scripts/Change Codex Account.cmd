@echo off
setlocal
cd /d "%~dp0\.."
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\windows-change-account.ps1" -Config "%USERPROFILE%\.codex-hybrid-model-switcher\config.json" -Apply %*
echo.
echo Press any key to close.
pause >nul
