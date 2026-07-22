param(
    [string]$Config = "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json",
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

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
            & py -3 -m codex_hybrid_switcher @ArgsList
        }
        elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -m codex_hybrid_switcher @ArgsList
        }
        else {
            throw "Python is required. Run Install Codex Hybrid.cmd first."
        }
        return $LASTEXITCODE
    }
    finally {
        $env:PYTHONPATH = $oldPythonPath
    }
}

if ($env:OS -ne "Windows_NT") {
    throw "This repair entry is for Windows only."
}

$arguments = @("windows-update-repair", "--config", $Config)
if ($Apply) { $arguments += "--apply" }
$exitCode = Invoke-Switcher -ArgsList $arguments
exit $exitCode
