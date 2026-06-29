param(
    [string]$ProviderId = "cloud-gpt-main",
    [string]$Config = "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Fail($Message) {
    Write-Error $Message
    exit 1
}

function Invoke-Switcher($ArgsList) {
    $repoRoot = Split-Path -Parent $PSScriptRoot
    $oldPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = "$repoRoot\src"
    try {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -m codex_hybrid_switcher @ArgsList
        }
        elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -m codex_hybrid_switcher @ArgsList
        }
        elseif (Get-Command codex-hybrid-switcher -ErrorAction SilentlyContinue) {
            & codex-hybrid-switcher @ArgsList
        }
        else {
            Fail "Python or codex-hybrid-switcher is required."
        }
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
    }
    finally {
        $env:PYTHONPATH = $oldPythonPath
    }
}

function Expand-PrivatePath($Value) {
    $expanded = [Environment]::ExpandEnvironmentVariables([string]$Value)
    if ($expanded.StartsWith("~")) {
        $tail = $expanded.Substring(1).TrimStart([char[]]@("\", "/"))
        return Join-Path $HOME $tail
    }
    return $expanded
}

function Get-CodexHome($ConfigPath) {
    if (!(Test-Path -LiteralPath $ConfigPath)) {
        Fail "Private config not found: $ConfigPath"
    }
    $json = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    if ($json.PSObject.Properties.Name -contains "codex_home") {
        return Expand-PrivatePath $json.codex_home
    }
    return Join-Path $env:USERPROFILE ".codex"
}

function Get-ProtectedHashes($CodexHome) {
    $result = [ordered]@{}
    foreach ($name in @("auth.json", "models_cache.json", "state_5.sqlite")) {
        $path = Join-Path $CodexHome $name
        if (Test-Path -LiteralPath $path) {
            $result[$name] = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        }
        else {
            $result[$name] = "missing"
        }
    }
    return $result
}

function Write-HashSummary($Title, $Hashes) {
    Write-Host $Title
    foreach ($name in $Hashes.Keys) {
        $value = $Hashes[$name]
        if ($value -eq "missing") {
            Write-Host "  - ${name}: missing"
        }
        else {
            Write-Host "  - ${name}: $($value.Substring(0, 12))"
        }
    }
}

function Assert-CodexStopped() {
    $running = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ProcessName -like "Codex*" -or $_.ProcessName -eq "codex"
    }
    if ($running) {
        Fail "Codex appears to be running. Quit Codex completely before applying the canary switch."
    }
}

if ($env:OS -ne "Windows_NT") {
    Fail "This canary script is for Windows only."
}

$resolvedConfig = Expand-PrivatePath $Config
$codexHome = Get-CodexHome $resolvedConfig

Write-Host "Windows cloud canary"
Write-Host "provider: $ProviderId"
Write-Host "config: <private-config>"
Write-Host "codex_home: configured"
Write-Host ""

Invoke-Switcher -ArgsList @("validate-config", "--config", $resolvedConfig)
Write-Host ""

Invoke-Switcher -ArgsList @("guarded-switch", $ProviderId, "--dry-run", "--config", $resolvedConfig)
Write-Host ""

if (!$Apply) {
    Write-Host "Dry-run complete. No files were changed."
    Write-Host "After quitting Codex, rerun with -Apply to perform the guarded canary switch."
    exit 0
}

Assert-CodexStopped

$before = Get-ProtectedHashes $codexHome
Write-HashSummary "Protected hashes before apply:" $before
Write-Host ""

Invoke-Switcher -ArgsList @("guarded-switch", $ProviderId, "--config", $resolvedConfig)
Write-Host ""

$after = Get-ProtectedHashes $codexHome
Write-HashSummary "Protected hashes after apply:" $after

$changed = @()
foreach ($name in $before.Keys) {
    if ($before[$name] -ne $after[$name]) {
        $changed += $name
    }
}

if ($changed.Count -gt 0) {
    Fail "Protected Codex files changed unexpectedly: $($changed -join ', ')"
}

Write-Host ""
Write-Host "Windows cloud canary switch applied. Protected files are unchanged."
Write-Host "Open Codex manually, then verify account information, plugins, project conversations, and one new test chat."
