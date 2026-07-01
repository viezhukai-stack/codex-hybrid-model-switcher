param(
    [string]$Config = "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Fail($Message) {
    Write-Error $Message
    exit 1
}

$switchScript = Join-Path $PSScriptRoot "windows-provider-switch.ps1"
if (!(Test-Path -LiteralPath $switchScript)) {
    Fail "Provider switch script was not found."
}

Write-Host ""
Write-Host "Restore Official Codex"
Write-Host "======================"
Write-Host "This restores Codex provider settings to the official OpenAI provider."
Write-Host "It still uses guarded dry-run first and will not touch auth.json, models_cache.json, or state_5.sqlite."
Write-Host ""

& powershell -NoProfile -ExecutionPolicy Bypass -File $switchScript -ProviderId "openai-official" -Config $Config
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Dry-run finished. No files were changed."
Write-Host "Before restoring, quit Codex Desktop completely."
Write-Host "To restore now, type APPLY exactly."
$confirm = Read-Host "Restore official Codex now"
if ($confirm -cne "APPLY") {
    Write-Host "Cancelled. No files were changed."
    exit 0
}

& powershell -NoProfile -ExecutionPolicy Bypass -File $switchScript -ProviderId "openai-official" -Config $Config -Apply
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Done. Open Codex Desktop manually and verify account, plugins, and project conversations."
