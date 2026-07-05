param(
    [string]$Config = "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json",
    [int]$Port = 19032
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Fail($Message) {
    Write-Error $Message
    exit 1
}

function Invoke-Switcher($ArgsList, [switch]$AllowFailure) {
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
        if ($LASTEXITCODE -ne 0 -and !$AllowFailure) {
            exit $LASTEXITCODE
        }
    }
    finally {
        $env:PYTHONPATH = $oldPythonPath
    }
}

function Test-HotRouter() {
    try {
        $url = "http://127.0.0.1:$Port/health"
        $json = (Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2).Content | ConvertFrom-Json
        return ($json.router -eq "codex-hot-router")
    }
    catch {
        return $false
    }
}

function Open-CodexDesktop() {
    Start-Process "shell:AppsFolder\OpenAI.Codex_2p2nqsd0c76g0!App"
}

if ($env:OS -ne "Windows_NT") {
    Fail "This launcher is for Windows only."
}

Write-Host "Checking local bridge on 127.0.0.1:19030..."
Invoke-Switcher -ArgsList @("ensure-bridge", "--config", $Config) -AllowFailure
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: local bridge did not become healthy. Cloud models can still work, but local models will fail until the bridge is fixed."
}

Write-Host "Checking Codex hot router on 127.0.0.1:$Port..."
if (Test-HotRouter) {
    Write-Host "Codex hot router is already running. Opening Codex..."
    Open-CodexDesktop
    exit 0
}

Write-Host "Starting Codex hot router on 127.0.0.1:$Port..."
Write-Host "Codex will open automatically after the router is healthy."
Write-Host "Keep this window open. Closing it stops the router."
Write-Host ""

$watcher = @"
`$url = 'http://127.0.0.1:$Port/health'
for (`$i = 0; `$i -lt 30; `$i++) {
    try {
        `$json = (Invoke-WebRequest -UseBasicParsing -Uri `$url -TimeoutSec 2).Content | ConvertFrom-Json
        if (`$json.router -eq 'codex-hot-router') {
            Start-Process 'shell:AppsFolder\OpenAI.Codex_2p2nqsd0c76g0!App'
            exit 0
        }
    } catch {}
    Start-Sleep -Seconds 1
}
"@

Start-Process powershell -WindowStyle Hidden -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $watcher)
Invoke-Switcher -ArgsList @("hot-router", "--config", $Config, "--port", "$Port")
