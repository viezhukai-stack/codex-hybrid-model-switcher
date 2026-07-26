param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,
    [string]$PythonExe,
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-StrictMode -Version Latest

function Find-InstalledPortablePython {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "CodexHybridModelSwitcher\python\python.exe"),
        (Join-Path $env:LOCALAPPDATA "CodexHybridModelSwitcher\python\python\python.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    return $null
}

if (-not $PythonExe) {
    $PythonExe = Find-InstalledPortablePython
}
if (-not $PythonExe -or -not (Test-Path -LiteralPath $PythonExe)) {
    if (-not $Quiet) {
        Write-Host "Portable Python is not installed; using the normal Python path."
    }
    exit 0
}

$portableRoot = Join-Path $env:LOCALAPPDATA "CodexHybridModelSwitcher\python"
$pythonFull = [IO.Path]::GetFullPath($PythonExe)
$portableFull = [IO.Path]::GetFullPath($portableRoot).TrimEnd('\') + '\'
if (-not $pythonFull.StartsWith($portableFull, [StringComparison]::OrdinalIgnoreCase)) {
    exit 0
}

$src = Join-Path ([IO.Path]::GetFullPath($ProjectRoot)) "src"
if (-not (Test-Path -LiteralPath $src)) {
    Write-Error "Current release src directory is missing: $src"
    exit 20
}

$pythonDir = Split-Path -Parent $pythonFull
$pth = Get-ChildItem -LiteralPath $pythonDir -Filter "python*._pth" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $pth) {
    if (-not $Quiet) {
        Write-Host "Portable Python has no ._pth file; no path repair was needed."
    }
    exit 0
}

$original = @([IO.File]::ReadAllLines($pth.FullName))
$updated = New-Object System.Collections.Generic.List[string]
foreach ($line in $original) {
    $trimmed = $line.Trim()
    $normalized = $trimmed.Replace('\', '/').ToLowerInvariant()
    $isManagedSrc = (
        ($normalized -like "*codexhybridmodelswitcher/releases/*/project/src") -or
        ($normalized -like "*codexhybridmodelswitcher/project/src") -or
        ($normalized -like "*codex-hybrid-model-switcher*/src")
    )
    if ($isManagedSrc) {
        continue
    }
    if ($trimmed -eq "#import site") {
        $updated.Add("import site")
    }
    else {
        $updated.Add($line)
    }
}
$updated.Add($src)

$before = $original -join "`n"
$after = $updated.ToArray() -join "`n"
if ($before -ceq $after) {
    if (-not $Quiet) {
        Write-Host "Portable Python already points to the current release."
    }
    exit 0
}

$temporary = "$($pth.FullName).tmp-$PID"
try {
    [IO.File]::WriteAllLines($temporary, $updated.ToArray(), [Text.Encoding]::ASCII)
    Move-Item -LiteralPath $temporary -Destination $pth.FullName -Force
}
finally {
    if (Test-Path -LiteralPath $temporary) {
        Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    }
}

if (-not $Quiet) {
    Write-Host "Portable Python path now points to: $src"
}
exit 0
