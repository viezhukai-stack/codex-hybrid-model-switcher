param(
    [string]$ReleaseTag = "v2.13.0",
    [string]$ProjectRepo = "viezhukai-stack/codex-hybrid-model-switcher",
    [string]$ProviderId = "cloud-gpt-main",
    [string]$ProviderLabel = "Cloud GPT Main",
    [string]$BaseUrl,
    [string]$Model,
    [string]$ApiKeyEnv = "OPENAI_COMPATIBLE_API_KEY",
    [ValidateSet("auto", "cuda13", "cuda12", "cpu")]
    [string]$LlamaBackend = "auto",
    [string]$ModelPath,
    [string]$MmprojPath,
    [string]$ConfigPath = "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json",
    [switch]$DryRunOnly,
    [switch]$Apply,
    [switch]$NonInteractive,
    [switch]$SkipCodexCheck,
    [switch]$SkipLocal,
    [switch]$SkipLocalSmoke,
    [switch]$SkipLlamaDownload
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$CodexDownloadUrl = "https://developers.openai.com/codex/app"
$InstallRoot = Join-Path $env:LOCALAPPDATA "CodexHybridModelSwitcher"
$ReleaseRoot = Join-Path $InstallRoot "releases\$ReleaseTag"
$ProjectZip = Join-Path $ReleaseRoot "$ReleaseTag.zip"
$ExtractRoot = Join-Path $ReleaseRoot "src"
$ProjectPath = Join-Path $ExtractRoot "codex-hybrid-model-switcher-$($ReleaseTag.TrimStart('v'))"
$LlamaRoot = Join-Path $InstallRoot "llama.cpp"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Fail {
    param([string]$Message, [int]$Code = 1)
    Write-Host ""
    Write-Host "ERROR: $Message"
    exit $Code
}

function Read-Required {
    param([string]$Prompt, [string]$Default = "")
    if ($NonInteractive) {
        if ($Default) {
            return $Default
        }
        Fail "$Prompt is required in -NonInteractive mode." 2
    }
    $suffix = ""
    if ($Default) {
        $suffix = " [$Default]"
    }
    $value = Read-Host "$Prompt$suffix"
    if (-not $value -and $Default) {
        return $Default
    }
    if (-not $value) {
        Fail "$Prompt is required." 2
    }
    return $value
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
        Fail "Python is not available." 2
    }
    $exe = $PythonCommand[0]
    $prefix = @()
    if ($PythonCommand.Count -gt 1) {
        $prefix = $PythonCommand[1..($PythonCommand.Count - 1)]
    }
    & $exe @prefix @Arguments
}

function Ensure-Python {
    Write-Step "Checking Python"
    $python = Find-Python
    if ($python.Count -gt 0) {
        Invoke-Python -PythonCommand $python -Arguments @("--version")
        return $python
    }

    Write-Step "Python not found; installing Python 3.12 with winget"
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        Fail "Python is missing and winget is not available. Install Python 3.12 from python.org, then rerun this installer." 2
    }
    winget install --id Python.Python.3.12 --exact --silent --accept-package-agreements --accept-source-agreements
    $python = Find-Python
    if ($python.Count -eq 0) {
        Fail "Python install finished, but Python still was not found. Close this window, open a new one, and rerun the installer." 2
    }
    Invoke-Python -PythonCommand $python -Arguments @("--version")
    return $python
}

function Test-CodexReady {
    $codexHome = Join-Path $env:USERPROFILE ".codex"
    $authPath = Join-Path $codexHome "auth.json"
    $installCandidates = @(
        "$env:LOCALAPPDATA\OpenAI\Codex",
        "$env:LOCALAPPDATA\Programs\Codex",
        "$env:ProgramFiles\Codex",
        "$env:USERPROFILE\.codex"
    )
    $installed = $false
    foreach ($candidate in $installCandidates) {
        if ($candidate -and (Test-Path $candidate)) {
            $installed = $true
            break
        }
    }
    if (-not $installed) {
        $shortcuts = @(
            "$env:APPDATA\Microsoft\Windows\Start Menu\Programs",
            "$env:USERPROFILE\Desktop"
        )
        foreach ($root in $shortcuts) {
            if ($root -and (Test-Path $root)) {
                $match = Get-ChildItem -LiteralPath $root -Filter "*Codex*.lnk" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($match) {
                    $installed = $true
                    break
                }
            }
        }
    }
    return ($installed -and (Test-Path $authPath))
}

function Ensure-CodexReady {
    if ($SkipCodexCheck) {
        return
    }
    Write-Step "Checking Codex Desktop"
    if (Test-CodexReady) {
        Write-Host "Codex Desktop state found."
        return
    }
    Write-Host "Codex Desktop is not installed, not opened yet, or not signed in."
    Write-Host "Opening the official Codex app page."
    Start-Process $CodexDownloadUrl
    Write-Host ""
    Write-Host "Install Codex Desktop, sign in, fully close Codex Desktop, then run this installer again."
    exit 20
}

function Ensure-ProjectRelease {
    Write-Step "Downloading fixed project release $ReleaseTag"
    New-Item -ItemType Directory -Force -Path $ReleaseRoot, $ExtractRoot | Out-Null
    if (-not (Test-Path $ProjectZip)) {
        Invoke-WebRequest -Uri "https://github.com/$ProjectRepo/archive/refs/tags/$ReleaseTag.zip" -OutFile $ProjectZip -UseBasicParsing -TimeoutSec 120
    }
    if (-not (Test-Path $ProjectPath)) {
        Expand-Archive -Path $ProjectZip -DestinationPath $ExtractRoot -Force
    }
    if (-not (Test-Path (Join-Path $ProjectPath "bootstrap.py"))) {
        Fail "Downloaded project release is missing bootstrap.py: $ProjectPath"
    }
    return $ProjectPath
}

function Ensure-ApiKeyEnvironment {
    param([string]$Name)
    $processValue = [Environment]::GetEnvironmentVariable($Name, "Process")
    $userValue = [Environment]::GetEnvironmentVariable($Name, "User")
    if ($processValue -or $userValue) {
        if ($userValue -and -not $processValue) {
            [Environment]::SetEnvironmentVariable($Name, $userValue, "Process")
        }
        Write-Host "API key environment variable is set: $Name"
        return
    }
    if ($NonInteractive) {
        Write-Host "API key environment variable is not set: $Name"
        Write-Host "The installer will continue to dry-run and print env-help."
        return
    }
    Write-Host ""
    Write-Host "Paste the provider API key for environment variable $Name."
    Write-Host "Input is hidden. Leave blank to skip and set it later."
    $secure = Read-Host "API key" -AsSecureString
    if ($secure.Length -eq 0) {
        Write-Host "No API key was entered. You can set it later with env-help."
        return
    }
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        if ($plain) {
            [Environment]::SetEnvironmentVariable($Name, $plain, "User")
            [Environment]::SetEnvironmentVariable($Name, $plain, "Process")
            Write-Host "API key stored in the Windows User environment variable: $Name"
        }
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

function Select-FileOrNull {
    param([string]$Title, [string]$Filter)
    if ($NonInteractive) {
        return $null
    }
    try {
        Add-Type -AssemblyName System.Windows.Forms
        $dialog = New-Object System.Windows.Forms.OpenFileDialog
        $dialog.Title = $Title
        $dialog.Filter = $Filter
        $dialog.CheckFileExists = $true
        if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
            return $dialog.FileName
        }
    } catch {
        Write-Host "File picker is unavailable. You can rerun with -ModelPath and -MmprojPath."
    }
    return $null
}

function Resolve-LocalModelSelection {
    if ($SkipLocal) {
        return $null
    }
    Write-Step "Checking optional local model files"
    $chosenModel = $ModelPath
    $chosenMmproj = $MmprojPath
    if (-not $chosenModel) {
        $chosenModel = Select-FileOrNull -Title "Choose local GGUF model file" -Filter "GGUF model (*.gguf)|*.gguf|All files (*.*)|*.*"
    }
    if (-not $chosenMmproj) {
        $chosenMmproj = Select-FileOrNull -Title "Choose local mmproj GGUF file" -Filter "GGUF mmproj (*.gguf)|*.gguf|All files (*.*)|*.*"
    }
    if (-not $chosenModel -or -not $chosenMmproj) {
        Write-Host "Local model files were not both selected. Local provider will remain pending."
        return $null
    }
    if (-not (Test-Path $chosenModel)) {
        Write-Host "Local GGUF model file does not exist. Local provider will remain pending."
        return $null
    }
    if (-not (Test-Path $chosenMmproj)) {
        Write-Host "Local mmproj file does not exist. Local provider will remain pending."
        return $null
    }
    return @{
        ModelPath = (Resolve-Path $chosenModel).Path
        MmprojPath = (Resolve-Path $chosenMmproj).Path
    }
}

function Test-NvidiaGpu {
    try {
        $gpus = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue
        return [bool](@($gpus | Where-Object { $_.Name -match "NVIDIA" }).Count)
    } catch {
        return $false
    }
}

function Get-LlamaRelease {
    $headers = @{ "User-Agent" = "codex-hybrid-model-switcher-installer" }
    return Invoke-RestMethod -Uri "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest" -Headers $headers -TimeoutSec 60
}

function Select-Asset {
    param($Release, [string[]]$Patterns)
    foreach ($pattern in $Patterns) {
        $asset = @($Release.assets | Where-Object { $_.name -match $pattern }) | Select-Object -First 1
        if ($asset) {
            return $asset
        }
    }
    return $null
}

function Download-And-Expand {
    param($Asset, [string]$TargetDir)
    New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
    $zip = Join-Path $TargetDir $Asset.name
    if (-not (Test-Path $zip)) {
        Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $zip -UseBasicParsing -TimeoutSec 300
    }
    Expand-Archive -Path $zip -DestinationPath $TargetDir -Force
}

function Install-LlamaBackend {
    param($Release, [string]$Backend)
    $specs = @{
        cuda13 = @{
            Bin = @("^llama-.*-bin-win-cuda-13\.3-x64\.zip$", "^llama-.*-bin-win-cuda-13[^0-9].*-x64\.zip$")
            Dll = @("^cudart-llama-bin-win-cuda-13\.3-x64\.zip$", "^cudart-llama-bin-win-cuda-13[^0-9].*-x64\.zip$")
        }
        cuda12 = @{
            Bin = @("^llama-.*-bin-win-cuda-12\.4-x64\.zip$", "^llama-.*-bin-win-cuda-12[^0-9].*-x64\.zip$")
            Dll = @("^cudart-llama-bin-win-cuda-12\.4-x64\.zip$", "^cudart-llama-bin-win-cuda-12[^0-9].*-x64\.zip$")
        }
        cpu = @{
            Bin = @("^llama-.*-bin-win-cpu-x64\.zip$", "^llama-.*-bin-win-avx2-x64\.zip$")
            Dll = @()
        }
    }
    $spec = $specs[$Backend]
    $binAsset = Select-Asset -Release $Release -Patterns $spec.Bin
    if (-not $binAsset) {
        throw "No llama.cpp binary asset matched backend $Backend"
    }
    $target = Join-Path $LlamaRoot "$($Release.tag_name)-$Backend"
    Download-And-Expand -Asset $binAsset -TargetDir $target
    if ($spec.Dll.Count -gt 0) {
        $dllAsset = Select-Asset -Release $Release -Patterns $spec.Dll
        if ($dllAsset) {
            Download-And-Expand -Asset $dllAsset -TargetDir $target
        }
    }
    $server = Get-ChildItem -LiteralPath $target -Filter "llama-server.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $server) {
        throw "llama-server.exe was not found after extracting $Backend"
    }
    return $server.FullName
}

function Ensure-LlamaRuntime {
    if ($SkipLlamaDownload) {
        Write-Host "Skipping llama.cpp download because -SkipLlamaDownload was provided."
        return $null
    }
    Write-Step "Downloading official llama.cpp runtime"
    $release = Get-LlamaRelease
    $order = @()
    if ($LlamaBackend -eq "auto") {
        if (Test-NvidiaGpu) {
            $order = @("cuda13", "cuda12", "cpu")
        } else {
            $order = @("cpu")
        }
    } else {
        $order = @($LlamaBackend)
    }
    foreach ($backend in $order) {
        try {
            Write-Host "Trying llama.cpp backend: $backend"
            $server = Install-LlamaBackend -Release $release -Backend $backend
            Write-Host "llama-server: $server"
            return $server
        } catch {
            Write-Host "Backend $backend was not installed: $($_.Exception.Message)"
        }
    }
    return $null
}

function Backup-PrivateConfig {
    if (-not (Test-Path $ConfigPath)) {
        return
    }
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backup = "$ConfigPath.bak-codex-hybrid-$stamp"
    Copy-Item -LiteralPath $ConfigPath -Destination $backup -Force
    Write-Host "Backed up private config: $backup"
}

function Invoke-Switcher {
    param([string[]]$ArgsList, [switch]$AllowFailure)
    $oldPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = Join-Path $ProjectPath "src"
    try {
        $pythonArgs = @("-m", "codex_hybrid_switcher") + $ArgsList
        Invoke-Python -PythonCommand $script:Python -Arguments $pythonArgs
        $code = $LASTEXITCODE
        if ($code -ne 0 -and -not $AllowFailure) {
            Fail "codex_hybrid_switcher $($ArgsList -join ' ') failed with exit code $LASTEXITCODE"
        }
        return $code
    } finally {
        $env:PYTHONPATH = $oldPythonPath
    }
}

function Write-Config {
    param([bool]$IncludeLocal, [string]$LlamaServerPath, [string]$LocalModelPath, [string]$LocalMmprojPath)
    $args = @(
        "setup",
        "--output", $ConfigPath,
        "--platform", "windows",
        "--codex-home", "$env:USERPROFILE\.codex",
        "--provider-id", $ProviderId,
        "--provider-label", $ProviderLabel,
        "--base-url", $BaseUrl,
        "--model", $Model,
        "--api-key-env", $ApiKeyEnv,
        "--wire-api", "responses",
        "--cloud-route", "bridge",
        "--non-interactive",
        "--force"
    )
    if ($IncludeLocal) {
        $args += @(
            "--include-local",
            "--llama-server-path", $LlamaServerPath,
            "--model-path", $LocalModelPath,
            "--mmproj-path", $LocalMmprojPath
        )
    }
    Invoke-Switcher -ArgsList $args
}

if ($env:OS -ne "Windows_NT") {
    Fail "This installer is for Windows only." 2
}
if ($Apply -and $DryRunOnly) {
    Fail "Use either -Apply or -DryRunOnly, not both." 2
}

Write-Host "Codex Hybrid Model Switcher Windows one-click setup"
Write-Host "Release: $ReleaseTag"
Write-Host "Default mode: dry-run only. No real Codex switch is applied unless -Apply is provided."

Ensure-CodexReady
$script:Python = Ensure-Python
$ProjectPath = Ensure-ProjectRelease

$BaseUrl = Read-Required -Prompt "OpenAI-compatible base_url" -Default $BaseUrl
$modelDefault = "provider-gpt-main"
if ($Model) {
    $modelDefault = $Model
}
$Model = Read-Required -Prompt "Cloud model id" -Default $modelDefault
$ApiKeyEnv = Read-Required -Prompt "API key environment variable name" -Default $ApiKeyEnv
Ensure-ApiKeyEnvironment -Name $ApiKeyEnv

$localSelection = Resolve-LocalModelSelection
$includeLocal = $false
$llamaServer = $null
if ($localSelection) {
    $llamaServer = Ensure-LlamaRuntime
    if ($llamaServer) {
        $includeLocal = $true
    } else {
        Write-Host "llama.cpp runtime was not installed. Local provider will remain pending."
    }
}

Write-Step "Creating private config"
Backup-PrivateConfig
if ($includeLocal) {
    Write-Config -IncludeLocal $true -LlamaServerPath $llamaServer -LocalModelPath $localSelection.ModelPath -LocalMmprojPath $localSelection.MmprojPath
} else {
    Write-Config -IncludeLocal $false -LlamaServerPath "" -LocalModelPath "" -LocalMmprojPath ""
}

Write-Step "Validating private config"
$validateArgs = @("validate-config", "--config", $ConfigPath)
if ($includeLocal) {
    $validateArgs += "--check-paths"
}
Invoke-Switcher -ArgsList $validateArgs

Write-Step "Installing desktop switcher launcher"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectPath "scripts\install-windows-launcher.ps1")
if ($LASTEXITCODE -ne 0) {
    Fail "Failed to install desktop switcher launcher."
}

Write-Step "Checking bridge health"
$bridgeCode = Invoke-Switcher -ArgsList @("bridge-health", "--config", $ConfigPath) -AllowFailure
if ($bridgeCode -ne 0) {
    Write-Host "Bridge health reported a setup gap. This can be expected before final apply or when the API key is not set."
}

if ($includeLocal -and -not $SkipLocalSmoke) {
    Write-Step "Running local llama.cpp smoke test"
    $smokeCode = Invoke-Switcher -ArgsList @("local-smoke", "--config", $ConfigPath) -AllowFailure
    if ($smokeCode -ne 0) {
        Write-Host "Local smoke failed. Rewriting config without the local provider."
        Write-Config -IncludeLocal $false -LlamaServerPath "" -LocalModelPath "" -LocalMmprojPath ""
        $includeLocal = $false
    }
}

Write-Step "Running guarded cloud dry-run"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectPath "scripts\windows-provider-switch.ps1") -ProviderId $ProviderId -Config $ConfigPath
if ($LASTEXITCODE -ne 0) {
    Fail "Cloud guarded dry-run failed."
}

if ($Apply) {
    Write-Step "Applying guarded cloud switch"
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectPath "scripts\windows-provider-switch.ps1") -ProviderId $ProviderId -Config $ConfigPath -Apply
    if ($LASTEXITCODE -ne 0) {
        Fail "Guarded apply failed."
    }
} else {
    Write-Host ""
    Write-Host "INSTALLER DRY-RUN COMPLETE"
    Write-Host "No real Codex switch was applied."
    Write-Host "Next: review the dry-run, fully quit Codex Desktop, then rerun with -Apply only when you are ready."
    if (-not $includeLocal) {
        Write-Host "Local provider status: pending. Provide GGUF + mmproj files and a working llama.cpp runtime to enable it."
    } else {
        Write-Host "Local provider status: configured."
    }
}
