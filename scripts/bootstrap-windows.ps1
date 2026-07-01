param(
    [string]$ReleaseTag = "v2.12.2",
    [string]$ProviderId = "cloud-gpt-main",
    [string]$BaseUrl,
    [string]$Model,
    [string]$ApiKeyEnv,
    [ValidateSet("bridge", "direct")]
    [string]$CloudRoute = "bridge",
    [string]$ConfigPath = "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json",
    [string]$CodexHome = "$env:USERPROFILE\.codex",
    [switch]$SkipPythonInstall,
    [switch]$DownloadRelease
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Find-Python {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:ProgramFiles\Python311\python.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return @($candidate)
        }
    }
    try {
        $null = & py -3 -c "import sys; print(sys.version)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return @("py", "-3")
        }
    } catch {}
    try {
        $null = & python -c "import sys; print(sys.version)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return @("python")
        }
    } catch {}
    return @()
}

function Invoke-Python {
    param([string[]]$PythonCommand, [string[]]$Arguments)
    if ($PythonCommand.Count -eq 0) {
        throw "Python is not available."
    }
    $exe = $PythonCommand[0]
    $prefix = @()
    if ($PythonCommand.Count -gt 1) {
        $prefix = $PythonCommand[1..($PythonCommand.Count - 1)]
    }
    & $exe @prefix @Arguments
}

function Install-Python {
    if ($SkipPythonInstall) {
        throw "Python is missing and -SkipPythonInstall was provided."
    }
    Write-Step "Python not found; installing Python 3.12 with winget"
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "Python is missing and winget is not available. Install Python 3.12 from python.org, then rerun this script."
    }
    winget install --id Python.Python.3.12 --exact --silent --accept-package-agreements --accept-source-agreements
}

function Resolve-Repo {
    if ($PSScriptRoot) {
        $candidate = Split-Path -Parent $PSScriptRoot
        if (Test-Path (Join-Path $candidate "bootstrap.py")) {
            if (-not $DownloadRelease) {
                return $candidate
            }
        }
    }

    Write-Step "Downloading fixed release $ReleaseTag"
    $versionName = $ReleaseTag.TrimStart("v")
    $workRoot = Join-Path $env:USERPROFILE "codex-hybrid-model-switcher"
    $releaseRoot = Join-Path $workRoot $ReleaseTag
    $zipPath = Join-Path $releaseRoot "$ReleaseTag.zip"
    $extractRoot = Join-Path $releaseRoot "src"
    $repo = Join-Path $extractRoot "codex-hybrid-model-switcher-$versionName"
    New-Item -ItemType Directory -Force -Path $releaseRoot, $extractRoot | Out-Null
    if (-not (Test-Path $zipPath)) {
        Invoke-WebRequest -Uri "https://github.com/viezhukai-stack/codex-hybrid-model-switcher/archive/refs/tags/$ReleaseTag.zip" -OutFile $zipPath -UseBasicParsing -TimeoutSec 120
    }
    if (-not (Test-Path $repo)) {
        Expand-Archive -Path $zipPath -DestinationPath $extractRoot -Force
    }
    if (-not (Test-Path (Join-Path $repo "bootstrap.py"))) {
        throw "Downloaded repository is missing bootstrap.py: $repo"
    }
    return $repo
}

if (-not $BaseUrl -or -not $Model -or -not $ApiKeyEnv) {
    Write-Host "Usage:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\bootstrap-windows.ps1 -BaseUrl https://example.com/v1 -Model provider-gpt-main -ApiKeyEnv OPENAI_COMPATIBLE_API_KEY -CloudRoute bridge"
    Write-Host ""
    Write-Host "This script does not read, print, or store API keys. Put the key in the named environment variable."
    exit 2
}

Write-Step "Checking Python"
$python = Find-Python
if ($python.Count -eq 0) {
    Install-Python
    $python = Find-Python
}
if ($python.Count -eq 0) {
    throw "Python install finished, but Python still was not found."
}
Invoke-Python -PythonCommand $python -Arguments @("--version")

$repo = Resolve-Repo
Write-Step "Using repository"
Write-Host $repo

Push-Location $repo
try {
    Write-Step "Running bootstrap dry-run setup"
    Invoke-Python -PythonCommand $python -Arguments @(
        "-I",
        "bootstrap.py",
        "--non-interactive",
        "--config", $ConfigPath,
        "--codex-home", $CodexHome,
        "--provider-id", $ProviderId,
        "--base-url", $BaseUrl,
        "--model", $Model,
        "--api-key-env", $ApiKeyEnv,
        "--cloud-route", $CloudRoute
    )
    if ($LASTEXITCODE -ne 0) {
        throw "bootstrap.py failed with exit code $LASTEXITCODE"
    }

    $env:PYTHONPATH = Join-Path $repo "src"

    Write-Step "Validating private config"
    Invoke-Python -PythonCommand $python -Arguments @("-m", "codex_hybrid_switcher", "validate-config", "--config", $ConfigPath)
    if ($LASTEXITCODE -ne 0) {
        throw "validate-config failed with exit code $LASTEXITCODE"
    }

    if (-not [Environment]::GetEnvironmentVariable($ApiKeyEnv, "Process") -and -not [Environment]::GetEnvironmentVariable($ApiKeyEnv, "User")) {
        Write-Step "API key environment variable is not set; printing safe setup help"
        Invoke-Python -PythonCommand $python -Arguments @("-m", "codex_hybrid_switcher", "env-help", "--platform", "windows", "--config", $ConfigPath)
    }

    if ($CloudRoute -eq "bridge") {
        Write-Step "Checking bridge health"
        Invoke-Python -PythonCommand $python -Arguments @("-m", "codex_hybrid_switcher", "bridge-health", "--config", $ConfigPath)
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "Bridge health reported a setup gap. This is expected before the API key is set or before the bridge is started."
        }
    }

    Write-Step "Running guarded dry-run"
    Invoke-Python -PythonCommand $python -Arguments @("-m", "codex_hybrid_switcher", "guarded-switch", $ProviderId, "--dry-run", "--config", $ConfigPath)
    if ($LASTEXITCODE -ne 0) {
        throw "guarded-switch --dry-run failed with exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Bootstrap dry-run complete."
Write-Host "No real Codex switch was applied."
Write-Host "Next: review the dry-run, set $ApiKeyEnv if needed, start/check the bridge, then fully quit Codex Desktop before any real guarded switch."
