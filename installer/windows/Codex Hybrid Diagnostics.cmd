@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-CodexHybrid.ps1" -DiagnosticsOnly %*
echo.
echo Press any key to close this window.
pause >nul
