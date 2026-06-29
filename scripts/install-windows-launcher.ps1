$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")
$launcher = Join-Path $desktop "Codex Model Switcher.cmd"

$body = @"
@echo off
cd /d "$repo"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\windows-provider-menu.ps1 -Config "%USERPROFILE%\.codex-hybrid-model-switcher\config.json"
pause
"@

Set-Content -LiteralPath $launcher -Value $body -Encoding ASCII
Write-Output "Installed: $launcher"
