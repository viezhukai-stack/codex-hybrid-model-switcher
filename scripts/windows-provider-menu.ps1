param(
    [string]$Config = "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json",
    [string]$ProviderId = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Fail($Message) {
    Write-Error $Message
    exit 1
}

function Expand-PrivatePath($Value) {
    $expanded = [Environment]::ExpandEnvironmentVariables([string]$Value)
    if ($expanded.StartsWith("~")) {
        $tail = $expanded.Substring(1).TrimStart([char[]]@("\", "/"))
        return Join-Path $HOME $tail
    }
    return $expanded
}

function Get-Provider($ConfigPath, $Id) {
    $json = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    return @($json.providers | Where-Object { $_.id -eq $Id }) | Select-Object -First 1
}

function Get-OptionalString($Object, $Name) {
    $property = $Object.PSObject.Properties[$Name]
    if (!$property -or $null -eq $property.Value) {
        return ""
    }
    return [string]$property.Value
}

function Show-Providers($ConfigPath) {
    $json = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    $providers = @($json.providers)
    if ($providers.Count -eq 0) {
        Fail "No providers found in private config."
    }

    Write-Host ""
    Write-Host "Codex Model Switcher"
    Write-Host "===================="
    Write-Host "Codex Desktop must be fully closed before applying a switch."
    Write-Host "The bottom-right Codex model selector is not the source of truth."
    Write-Host ""

    for ($i = 0; $i -lt $providers.Count; $i++) {
        $provider = $providers[$i]
        $label = Get-OptionalString $provider "label"
        if (!$label) {
            $label = Get-OptionalString $provider "id"
        }
        $kind = Get-OptionalString $provider "kind"
        $model = Get-OptionalString $provider "model"
        Write-Host ("{0}. {1} [{2}] {3}" -f ($i + 1), $label, $kind, $model)
    }

    Write-Host ""
    $choice = Read-Host "Choose provider number, or Q to quit"
    if ($choice -match "^[Qq]$") {
        exit 0
    }
    $index = 0
    if (![int]::TryParse($choice, [ref]$index)) {
        Fail "Invalid selection."
    }
    if ($index -lt 1 -or $index -gt $providers.Count) {
        Fail "Invalid selection."
    }
    return $providers[$index - 1]
}

if ($env:OS -ne "Windows_NT") {
    Fail "This menu is for Windows only."
}

$resolvedConfig = Expand-PrivatePath $Config
if (!(Test-Path -LiteralPath $resolvedConfig)) {
    Fail "Private config not found: $resolvedConfig"
}

if ($ProviderId) {
    $provider = Get-Provider $resolvedConfig $ProviderId
    if (!$provider) {
        Fail "Provider not found in private config: $ProviderId"
    }
}
else {
    $provider = Show-Providers $resolvedConfig
}

$selectedId = [string]$provider.id
$kind = Get-OptionalString $provider "kind"
$switchScript = Join-Path $PSScriptRoot "windows-provider-switch.ps1"
$commonArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $switchScript, "-ProviderId", $selectedId, "-Config", $resolvedConfig)
if ($kind -eq "local") {
    $commonArgs += "-AllowLocal"
}

Write-Host ""
Write-Host "Selected provider: $selectedId [$kind]"
Write-Host "Step 1: guarded dry-run"
Write-Host ""

& powershell @commonArgs
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Dry-run finished. No files were changed."
Write-Host "Before applying, quit Codex Desktop completely."
Write-Host "To apply this switch, type APPLY exactly."
$confirm = Read-Host "Apply now"
if ($confirm -cne "APPLY") {
    Write-Host "Cancelled. No files were changed."
    exit 0
}

Write-Host ""
Write-Host "Step 2: guarded apply"
Write-Host ""

& powershell @($commonArgs + "-Apply")
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Done. Open Codex Desktop manually and verify account, plugins, project conversations, then start a new test chat."
