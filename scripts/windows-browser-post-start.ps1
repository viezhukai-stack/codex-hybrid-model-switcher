param(
    [string]$Config = "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json",
    [int]$WaitSeconds = 90
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$logRoot = Join-Path $env:LOCALAPPDATA "CodexHybridModelSwitcher\logs"
$logPath = Join-Path $logRoot "browser-post-start.log"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
Set-Content -LiteralPath $logPath -Value ("[{0}] Browser post-start check" -f (Get-Date -Format "s")) -Encoding UTF8

$portablePython = Join-Path $env:LOCALAPPDATA "CodexHybridModelSwitcher\python\python.exe"
$portablePythonNested = Join-Path $env:LOCALAPPDATA "CodexHybridModelSwitcher\python\python\python.exe"
$python = $null
$pythonPrefix = @()
if (Test-Path -LiteralPath $portablePython) {
    $python = $portablePython
}
elseif (Test-Path -LiteralPath $portablePythonNested) {
    $python = $portablePythonNested
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $python = "py"
    $pythonPrefix = @("-3")
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $python = "python"
}
else {
    Add-Content -LiteralPath $logPath -Value "Python is unavailable; Browser post-start check did not run."
    exit 20
}

$oldPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = "$repoRoot\src"
try {
    $arguments = @($pythonPrefix) + @(
        "-m", "codex_hybrid_switcher",
        "windows-browser-ensure",
        "--config", $Config,
        "--wait-seconds", "$WaitSeconds"
    )
    & $python @arguments 2>&1 | Out-File -LiteralPath $logPath -Append -Encoding UTF8
    $exitCode = $LASTEXITCODE
    Add-Content -LiteralPath $logPath -Value ("[{0}] exit={1}" -f (Get-Date -Format "s"), $exitCode)
    exit $exitCode
}
finally {
    $env:PYTHONPATH = $oldPythonPath
}
