param(
    [string]$Config = "$env:USERPROFILE\.codex-hybrid-model-switcher\config.json",
    [string]$InstallRoot = "$env:LOCALAPPDATA\CodexHybridModelSwitcher"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-StrictMode -Version Latest

function Project-Version([string]$ProjectRoot) {
    $pyproject = Join-Path $ProjectRoot "pyproject.toml"
    if (-not (Test-Path -LiteralPath $pyproject)) {
        return [version]"0.0.0"
    }
    $match = [regex]::Match(
        (Get-Content -LiteralPath $pyproject -Raw -Encoding UTF8),
        '(?m)^version\s*=\s*"([0-9]+(?:\.[0-9]+){1,3})"'
    )
    if (-not $match.Success) {
        return [version]"0.0.0"
    }
    return [version]$match.Groups[1].Value
}

function Is-UsableProject([string]$ProjectRoot) {
    return [bool](
        $ProjectRoot -and
        (Test-Path -LiteralPath (Join-Path $ProjectRoot "pyproject.toml")) -and
        (Test-Path -LiteralPath (Join-Path $ProjectRoot "scripts\windows-hot-router-start.ps1"))
    )
}

function Installed-Projects {
    $releaseRoot = Join-Path $InstallRoot "releases"
    if (-not (Test-Path -LiteralPath $releaseRoot)) {
        return @()
    }
    $projects = New-Object System.Collections.Generic.List[string]
    Get-ChildItem -LiteralPath $releaseRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
        $bundled = Join-Path $_.FullName "project"
        if (Is-UsableProject $bundled) {
            $projects.Add($bundled)
        }
        $sourceRoot = Join-Path $_.FullName "src"
        Get-ChildItem -LiteralPath $sourceRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            if (Is-UsableProject $_.FullName) {
                $projects.Add($_.FullName)
            }
        }
    }
    return @($projects | Select-Object -Unique)
}

$pointer = Join-Path $InstallRoot "current-project.txt"
$candidates = New-Object System.Collections.Generic.List[string]
if (Test-Path -LiteralPath $pointer) {
    $pointed = (Get-Content -LiteralPath $pointer -Raw -Encoding UTF8).Trim()
    if (Is-UsableProject $pointed) {
        $candidates.Add($pointed)
    }
}
foreach ($project in @(Installed-Projects)) {
    if ($project -and -not $candidates.Contains($project)) {
        $candidates.Add($project)
    }
}
if ($candidates.Count -eq 0) {
    Write-Error "No installed Codex Hybrid release was found. Run Install Codex Hybrid.cmd."
    exit 20
}

$selected = @($candidates | Sort-Object @{Expression={Project-Version $_};Descending=$true}, @{Expression={$_};Descending=$true})[0]
$resolved = (Resolve-Path -LiteralPath $selected).Path
New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
$temporary = "$pointer.tmp-$PID"
[IO.File]::WriteAllText($temporary, $resolved + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $temporary -Destination $pointer -Force

$launcher = Join-Path $resolved "scripts\windows-hot-router-start.ps1"
Write-Host "Using Codex Hybrid release: $((Project-Version $resolved).ToString())"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $launcher -Config $Config | Out-Host
exit $LASTEXITCODE
