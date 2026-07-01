param(
    [string]$ProviderId = "cloud-gpt-main",
    [string]$Config = "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json",
    [switch]$Apply,
    [switch]$AllowLocal,
    [switch]$SkipLocalSmoke
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
        $portablePython = Join-Path $env:LOCALAPPDATA "CodexHybridModelSwitcher\python\python.exe"
        $portablePythonNested = Join-Path $env:LOCALAPPDATA "CodexHybridModelSwitcher\python\python\python.exe"
        if (Test-Path $portablePython) {
            & $portablePython -m codex_hybrid_switcher @ArgsList
        }
        elseif (Test-Path $portablePythonNested) {
            & $portablePythonNested -m codex_hybrid_switcher @ArgsList
        }
        elseif (Get-Command py -ErrorAction SilentlyContinue) {
            & py -m codex_hybrid_switcher @ArgsList
        }
        elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -m codex_hybrid_switcher @ArgsList
        }
        else {
            Fail "Python is required."
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

function Assert-CodexStopped() {
    $running = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ProcessName -like "Codex*" -or $_.ProcessName -eq "codex"
    }
    if ($running) {
        Fail "Codex appears to be running. Quit Codex completely before applying the switch."
    }
}

function Get-ProviderKind($ConfigPath, $Id) {
    $json = Get-Content -LiteralPath $ConfigPath -Raw | ConvertFrom-Json
    $provider = @($json.providers | Where-Object { $_.id -eq $Id }) | Select-Object -First 1
    if (!$provider) {
        Fail "Provider not found in private config: $Id"
    }
    return [string]$provider.kind
}

if ($env:OS -ne "Windows_NT") {
    Fail "This provider switch script is for Windows only."
}

$resolvedConfig = Expand-PrivatePath $Config
$kind = Get-ProviderKind $resolvedConfig $ProviderId
$argsList = @("guarded-switch", $ProviderId, "--config", $resolvedConfig)

if ($kind -eq "local") {
    if (!$AllowLocal) {
        Fail "Local provider switches require -AllowLocal. Run local-smoke first if this is the first local validation."
    }
    $argsList += "--allow-local"
    if ($SkipLocalSmoke) {
        $argsList += "--skip-local-smoke"
    }
}

Write-Host "Windows provider switch"
Write-Host "provider: $ProviderId"
Write-Host "kind: $kind"
Write-Host "config: <private-config>"
Write-Host ""

Invoke-Switcher -ArgsList @("validate-config", "--config", $resolvedConfig)
Write-Host ""

Invoke-Switcher -ArgsList ($argsList + "--dry-run")
Write-Host ""

if (!$Apply) {
    Write-Host "Dry-run complete. No files were changed."
    Write-Host "After quitting Codex, rerun with -Apply to perform the guarded switch."
    exit 0
}

Assert-CodexStopped
Invoke-Switcher -ArgsList $argsList
Write-Host ""
Write-Host "Provider switch applied. Open Codex manually and verify account, plugins, project conversations, and one new test chat."
