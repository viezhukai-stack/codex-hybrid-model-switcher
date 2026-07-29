@echo off
setlocal
cd /d "%~dp0\.."

powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\windows-live-audio.ps1" -Action Doctor
echo.
echo Fully quit Codex before applying or restoring Live audio settings.
echo Type REPAIR to create a backup and apply the recommended repair.
echo Type RESTORE to restore the newest Live audio backup.
echo Press Enter to leave settings unchanged.
set /p LIVE_AUDIO_ACTION=Choice:

if /I "%LIVE_AUDIO_ACTION%"=="REPAIR" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\windows-live-audio.ps1" -Action Repair -Confirm REPAIR
) else if /I "%LIVE_AUDIO_ACTION%"=="RESTORE" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\windows-live-audio.ps1" -Action Restore -Confirm RESTORE
) else (
  echo No audio setting was changed.
)

echo.
echo Press any key to close.
pause >nul
