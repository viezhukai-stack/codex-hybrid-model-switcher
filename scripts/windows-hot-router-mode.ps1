param(
    [ValidateSet("enable", "restore", "status")]
    [string]$Action = "status",
    [string]$Config = "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json",
    [string]$RouterUrl = "http://127.0.0.1:19032/v1"
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

if ($env:OS -ne "Windows_NT") {
    Fail "This helper is for Windows only."
}

$argsList = @("hot-router-mode", $Action, "--config", $Config)
if ($Action -eq "enable") {
    $argsList += @("--router-url", $RouterUrl)
}

Invoke-Switcher -ArgsList $argsList
