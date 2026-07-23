param(
    [string]$Config = "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json",
    [string]$RouterHost,
    [Nullable[int]]$Port
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
        $url = "http://$RouterHost`:$Port/health"
        $json = (Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2).Content | ConvertFrom-Json
        return ($json.router -eq "codex-hot-router")
    }
    catch {
        return $false
    }
}

function Get-CodexAppId() {
    $app = Get-StartApps -ErrorAction SilentlyContinue | Where-Object {
        $_.AppID -like "OpenAI.Codex_*!App" -or $_.Name -in @("ChatGPT", "Codex")
    } | Select-Object -First 1
    if ($app -and $app.AppID) {
        return $app.AppID
    }
    $package = Get-AppxPackage OpenAI.Codex -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($package) {
        try {
            $manifest = Get-AppxPackageManifest -Package $package
            $application = @($manifest.Package.Applications.Application) | Select-Object -First 1
            if ($application -and $application.Id -and $package.PackageFamilyName) {
                return "$($package.PackageFamilyName)!$($application.Id)"
            }
        }
        catch {
            Write-Host "WARNING: could not read the OpenAI.Codex package AppID from its manifest."
        }
    }
    return "OpenAI.Codex_2p2nqsd0c76g0!App"
}

function Open-CodexDesktop() {
    $appId = Get-CodexAppId
    Start-Process "shell:AppsFolder\$appId"
}

function Start-BrowserPostStartCheck() {
    $postStartScript = Join-Path $PSScriptRoot "windows-browser-post-start.ps1"
    if (!(Test-Path -LiteralPath $postStartScript)) {
        Write-Host "WARNING: Browser post-start helper was not found: $postStartScript"
        return
    }
    $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$postStartScript`" -Config `"$Config`""
    Start-Process -FilePath "powershell.exe" -WindowStyle Hidden -ArgumentList $arguments | Out-Null
}

function Test-CodexRunning() {
    $running = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ProcessName -like "Codex*" -or $_.ProcessName -like "ChatGPT*" -or $_.ProcessName -eq "codex"
    }
    return [bool]$running
}

function Test-HotRouterMode() {
    $codexConfig = Join-Path $env:USERPROFILE ".codex\config.toml"
    if (!(Test-Path -LiteralPath $codexConfig)) {
        return $false
    }
    $routerUrl = "http://$RouterHost`:$Port/v1"
    return [bool]((Get-Content -LiteralPath $codexConfig -Raw -Encoding UTF8) -match [regex]::Escape("base_url = `"$routerUrl`""))
}

function Enable-HotRouterMode() {
    if (Test-HotRouterMode) {
        return
    }
    if (Test-CodexRunning) {
        Fail "Codex/ChatGPT is running. Quit it completely before enabling 2.0 hot-router mode."
    }
    $modeScript = Join-Path $PSScriptRoot "windows-hot-router-mode.ps1"
    if (!(Test-Path -LiteralPath $modeScript)) {
        Fail "Hot-router mode helper was not found: $modeScript"
    }
    & powershell -NoProfile -ExecutionPolicy Bypass -File $modeScript -Action enable -Config $Config -RouterUrl "http://$RouterHost`:$Port/v1"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

if ($env:OS -ne "Windows_NT") {
    Fail "This launcher is for Windows only."
}

if (Test-Path -LiteralPath $Config) {
    try {
        $privateConfig = Get-Content -LiteralPath $Config -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not $RouterHost -and $privateConfig.hot_router.host) {
            $RouterHost = [string]$privateConfig.hot_router.host
        }
        if (-not $Port -and $privateConfig.hot_router.port) {
            $Port = [int]$privateConfig.hot_router.port
        }
    }
    catch {
        Write-Host "WARNING: could not read hot_router host/port from private config; using defaults."
    }
}
if (-not $RouterHost) { $RouterHost = "127.0.0.1" }
if (-not $Port) { $Port = 19032 }

Write-Host "Checking Codex Browser/CLI update compatibility..."
Invoke-Switcher -ArgsList @("windows-update-ensure", "--config", $Config) -AllowFailure
$updateExit = $LASTEXITCODE
if ($updateExit -ne 0) {
    Fail "Automatic Codex Browser/CLI refresh stopped. Quit Codex and run 'Repair Codex Browser and CLI.cmd', then start this launcher again."
}

Write-Host "Checking local bridge on 127.0.0.1:19030..."
Invoke-Switcher -ArgsList @("ensure-bridge", "--config", $Config) -AllowFailure
if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: local bridge did not become healthy. Cloud models can still work, but local models will fail until the bridge is fixed."
}

Write-Host "Checking Codex hot router on $RouterHost`:$Port..."
if (Test-HotRouter) {
    Write-Host "Codex hot router is already running."
    Enable-HotRouterMode
    Write-Host "Opening Codex..."
    Open-CodexDesktop
    Start-BrowserPostStartCheck
    exit 0
}

Write-Host "Starting Codex hot router on $RouterHost`:$Port..."
Write-Host "Codex will open automatically after the router is healthy."
Write-Host "Keep this window open. Closing it stops the router."
Write-Host ""

$appTarget = "shell:AppsFolder\$(Get-CodexAppId)"
$modeScript = Join-Path $PSScriptRoot "windows-hot-router-mode.ps1"
$routerUrl = "http://$RouterHost`:$Port/v1"
$codexConfigToml = Join-Path $env:USERPROFILE ".codex\config.toml"
$watcher = @"
`$url = 'http://$RouterHost`:$Port/health'
for (`$i = 0; `$i -lt 30; `$i++) {
    try {
        `$json = (Invoke-WebRequest -UseBasicParsing -Uri `$url -TimeoutSec 2).Content | ConvertFrom-Json
        if (`$json.router -eq 'codex-hot-router') {
            `$modeActive = `$false
            if (Test-Path -LiteralPath '$codexConfigToml') {
                `$modeActive = [bool]((Get-Content -LiteralPath '$codexConfigToml' -Raw -Encoding UTF8) -match [regex]::Escape('base_url = "$routerUrl"'))
            }
            if (-not `$modeActive) {
                `$running = Get-Process -ErrorAction SilentlyContinue | Where-Object { `$_.ProcessName -like 'Codex*' -or `$_.ProcessName -like 'ChatGPT*' -or `$_.ProcessName -eq 'codex' }
                if (`$running) { exit 2 }
                & powershell -NoProfile -ExecutionPolicy Bypass -File '$modeScript' -Action enable -Config '$Config' -RouterUrl '$routerUrl'
                if (`$LASTEXITCODE -ne 0) { exit `$LASTEXITCODE }
            }
            Start-Process '$appTarget'
            exit 0
        }
    } catch {}
    Start-Sleep -Seconds 1
}
"@

Start-Process powershell -WindowStyle Hidden -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $watcher)
Start-BrowserPostStartCheck
Invoke-Switcher -ArgsList @("hot-router", "--config", $Config, "--host", $RouterHost, "--port", "$Port")
