$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")
$launcher = Join-Path $desktop "Codex Model Switcher.cmd"
$hotRouterLauncher = Join-Path $desktop "Start Codex Hot Router.cmd"
$enableHotRouterLauncher = Join-Path $desktop "Enable Codex Hot Router Mode.cmd"
$restoreHotRouterLauncher = Join-Path $desktop "Restore Codex 19030 Mode.cmd"
$restoreLauncher = Join-Path $desktop "Restore Official Codex.cmd"
$orchestrateUpdateLauncher = Join-Path $desktop "Repair Codex Update and Plugins.cmd"
$repairUpdateLauncher = Join-Path $desktop "Repair Codex Browser and CLI.cmd"
$repairLiveAudioLauncher = Join-Path $desktop "Repair Codex Live Audio.cmd"
$changeAccountLauncher = Join-Path $desktop "Change Codex Account.cmd"

$body = @"
@echo off
cd /d "$repo"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-provider-menu.ps1 -Config "%USERPROFILE%\.codex-hybrid-model-switcher\config.json"
pause
"@

Set-Content -LiteralPath $launcher -Value $body -Encoding ASCII
Write-Output "Installed: $launcher"

$hotRouterBody = @"
@echo off
cd /d "$repo"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-hot-router-start.ps1 -Config "%USERPROFILE%\.codex-hybrid-model-switcher\config.json"
echo.
echo Router stopped. Press any key to close.
pause >nul
"@

Set-Content -LiteralPath $hotRouterLauncher -Value $hotRouterBody -Encoding ASCII
Write-Output "Installed: $hotRouterLauncher"

$enableHotRouterBody = @"
@echo off
cd /d "$repo"
echo Enabling Codex Hot Router Mode...
echo Quit Codex Desktop completely before running this.
echo The hot router must already be running on 127.0.0.1:19032.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-hot-router-mode.ps1 -Action enable -Config "%USERPROFILE%\.codex-hybrid-model-switcher\config.json"
echo.
echo Press any key to close.
pause >nul
"@

Set-Content -LiteralPath $enableHotRouterLauncher -Value $enableHotRouterBody -Encoding ASCII
Write-Output "Installed: $enableHotRouterLauncher"

$restoreHotRouterBody = @"
@echo off
cd /d "$repo"
echo Restoring Codex 19030 Mode...
echo Quit Codex Desktop completely before running this.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-hot-router-mode.ps1 -Action restore -Config "%USERPROFILE%\.codex-hybrid-model-switcher\config.json"
echo.
echo Press any key to close.
pause >nul
"@

Set-Content -LiteralPath $restoreHotRouterLauncher -Value $restoreHotRouterBody -Encoding ASCII
Write-Output "Installed: $restoreHotRouterLauncher"

$restoreBody = @"
@echo off
cd /d "$repo"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-restore-official.ps1 -Config "%USERPROFILE%\.codex-hybrid-model-switcher\config.json"
pause
"@

Set-Content -LiteralPath $restoreLauncher -Value $restoreBody -Encoding ASCII
Write-Output "Installed: $restoreLauncher"

$orchestrateUpdateBody = @"
@echo off
cd /d "$repo"
echo Codex must be fully closed before this repair.
echo This will register a staged official update and refresh the current Browser/Chrome bundle.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-update-orchestrate.ps1 -Config "%USERPROFILE%\.codex-hybrid-model-switcher\config.json" -Apply
echo.
echo Press any key to close.
pause >nul
"@

Set-Content -LiteralPath $orchestrateUpdateLauncher -Value $orchestrateUpdateBody -Encoding ASCII
Write-Output "Installed: $orchestrateUpdateLauncher"

$repairUpdateBody = @"
@echo off
cd /d "$repo"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-update-repair.ps1 -Config "%USERPROFILE%\.codex-hybrid-model-switcher\config.json" -Apply
echo.
echo Press any key to close.
pause >nul
"@

Set-Content -LiteralPath $repairUpdateLauncher -Value $repairUpdateBody -Encoding ASCII
Write-Output "Installed: $repairUpdateLauncher"

$repairLiveAudioBody = @"
@echo off
cd /d "$repo"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-live-audio.ps1 -Action Doctor
echo.
echo Fully quit Codex before applying or restoring Live audio settings.
echo Type REPAIR to create a backup and apply the recommended repair.
echo Type RESTORE to restore the newest Live audio backup.
echo Press Enter to leave settings unchanged.
set /p LIVE_AUDIO_ACTION=Choice:
if /I "%LIVE_AUDIO_ACTION%"=="REPAIR" powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-live-audio.ps1 -Action Repair -Confirm REPAIR
if /I "%LIVE_AUDIO_ACTION%"=="RESTORE" powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-live-audio.ps1 -Action Restore -Confirm RESTORE
echo.
echo Press any key to close.
pause >nul
"@

Set-Content -LiteralPath $repairLiveAudioLauncher -Value $repairLiveAudioBody -Encoding ASCII
Write-Output "Installed: $repairLiveAudioLauncher"

$changeAccountBody = @"
@echo off
cd /d "$repo"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-change-account.ps1 -Config "%USERPROFILE%\.codex-hybrid-model-switcher\config.json" -Apply
echo.
echo Press any key to close.
pause >nul
"@

Set-Content -LiteralPath $changeAccountLauncher -Value $changeAccountBody -Encoding ASCII
Write-Output "Installed: $changeAccountLauncher"
