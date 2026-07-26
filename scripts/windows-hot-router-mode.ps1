param(
    [ValidateSet("enable", "restore", "status")]
    [string]$Action = "status",
    [string]$Config = "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json",
    [string]$RouterUrl
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-StrictMode -Version Latest
$repoRoot = Split-Path -Parent $PSScriptRoot

function Initialize-PortablePythonPath {
    $helper = Join-Path $PSScriptRoot "windows-portable-python-path.ps1"
    if (-not (Test-Path -LiteralPath $helper)) {
        Fail "Portable Python path helper is missing: $helper"
    }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $helper -ProjectRoot $repoRoot -Quiet
    if ($LASTEXITCODE -ne 0) {
        Fail "Portable Python path repair failed."
    }
}

function Fail($Message) {
    Write-Error $Message
    exit 1
}

function Invoke-Switcher($ArgsList) {
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

if ($env:OS -ne "Windows_NT") {
    Fail "This helper is for Windows only."
}

Initialize-PortablePythonPath

$argsList = @("hot-router-mode", $Action, "--config", $Config)
if ($Action -eq "enable" -and $RouterUrl) {
    $argsList += @("--router-url", $RouterUrl)
}

Invoke-Switcher -ArgsList $argsList
