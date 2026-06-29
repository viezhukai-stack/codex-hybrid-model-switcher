param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$SwitcherArgs
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$oldPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = if ($oldPythonPath) { "$repoRoot\src;$oldPythonPath" } else { "$repoRoot\src" }

try {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -m codex_hybrid_switcher local-smoke @SwitcherArgs
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m codex_hybrid_switcher local-smoke @SwitcherArgs
    }
    else {
        Write-Error "Python is required."
        exit 1
    }
    exit $LASTEXITCODE
}
finally {
    $env:PYTHONPATH = $oldPythonPath
}
