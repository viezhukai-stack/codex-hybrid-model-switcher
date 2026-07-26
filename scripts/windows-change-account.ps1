param(
    [string]$Config = "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json",
    [switch]$Apply,
    [switch]$RecoverLast,
    [string]$ProxyUrl
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-StrictMode -Version Latest
$repoRoot = Split-Path -Parent $PSScriptRoot

function Initialize-PortablePythonPath {
    $helper = Join-Path $PSScriptRoot "windows-portable-python-path.ps1"
    if (-not (Test-Path -LiteralPath $helper)) {
        throw "Portable Python path helper is missing: $helper"
    }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $helper -ProjectRoot $repoRoot -Quiet
    if ($LASTEXITCODE -ne 0) {
        throw "Portable Python path repair failed."
    }
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
    throw "This account entry is for Windows only."
}

Initialize-PortablePythonPath

$arguments = @("change-account", "--config", $Config)
if ($Apply) { $arguments += "--apply" }
if ($RecoverLast) { $arguments += "--recover-last" }
if ($ProxyUrl) { $arguments += @("--proxy-url", $ProxyUrl) }
$exitCode = Invoke-Switcher -ArgsList $arguments
if ($exitCode -eq 3) {
    exit 0
}
if ($exitCode -eq 0 -and $Apply -and -not $RecoverLast) {
    $launcher = Join-Path ([Environment]::GetFolderPath("Desktop")) "Start Codex Hot Router.cmd"
    if (Test-Path -LiteralPath $launcher) {
        Start-Process -FilePath $launcher
    }
    else {
        Write-Host "Account login completed. Start Codex through the normal Hot Router entry."
    }
}
exit $exitCode
