param(
    [ValidateSet("Doctor", "Repair", "Restore")]
    [string]$Action = "Doctor",
    [string]$Confirm = "",
    [string]$EndpointId = "",
    [switch]$Json
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
Set-StrictMode -Version Latest

if ($env:OS -ne "Windows_NT") {
    throw "This maintenance entry is for Windows only."
}

$script:ConsentRoot = "HKCU:\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
$script:ConsentNativeRoot = "HKCU\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
$script:CaptureRegistryRoot = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Capture"
$script:BackupParent = Join-Path $env:USERPROFILE ".codex-hybrid-model-switcher\backups"
$script:RoleOrder = @("Console", "Multimedia", "Communications")

function Initialize-AudioInterop {
    if ("CodexHybridAudio.AudioPolicy" -as [type]) {
        return
    }

    $source = @'
using System;
using System.Runtime.InteropServices;

namespace CodexHybridAudio {
    public enum ERole {
        Console = 0,
        Multimedia = 1,
        Communications = 2
    }

    [ComImport, Guid("F8679F50-850A-41CF-9C72-430F290290C8"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IPolicyConfig {
        [PreserveSig] int GetMixFormat([MarshalAs(UnmanagedType.LPWStr)] string name, IntPtr format);
        [PreserveSig] int GetDeviceFormat([MarshalAs(UnmanagedType.LPWStr)] string name, bool defaultValue, IntPtr format);
        [PreserveSig] int ResetDeviceFormat([MarshalAs(UnmanagedType.LPWStr)] string name);
        [PreserveSig] int SetDeviceFormat([MarshalAs(UnmanagedType.LPWStr)] string name, IntPtr endpointFormat, IntPtr mixFormat);
        [PreserveSig] int GetProcessingPeriod([MarshalAs(UnmanagedType.LPWStr)] string name, bool defaultValue, IntPtr defaultPeriod, IntPtr minimumPeriod);
        [PreserveSig] int SetProcessingPeriod([MarshalAs(UnmanagedType.LPWStr)] string name, IntPtr period);
        [PreserveSig] int GetShareMode([MarshalAs(UnmanagedType.LPWStr)] string name, IntPtr mode);
        [PreserveSig] int SetShareMode([MarshalAs(UnmanagedType.LPWStr)] string name, IntPtr mode);
        [PreserveSig] int GetPropertyValue([MarshalAs(UnmanagedType.LPWStr)] string name, IntPtr key, IntPtr value);
        [PreserveSig] int SetPropertyValue([MarshalAs(UnmanagedType.LPWStr)] string name, IntPtr key, IntPtr value);
        [PreserveSig] int SetDefaultEndpoint([MarshalAs(UnmanagedType.LPWStr)] string name, ERole role);
        [PreserveSig] int SetEndpointVisibility([MarshalAs(UnmanagedType.LPWStr)] string name, bool visible);
    }

    [ComImport, Guid("870AF99C-171D-4F9E-AF0D-E63DF40C2BC9")]
    class PolicyConfigClient { }

    [ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDeviceEnumerator {
        [PreserveSig] int EnumAudioEndpoints(int flow, int stateMask, out IntPtr devices);
        [PreserveSig] int GetDefaultAudioEndpoint(int flow, ERole role, out IMMDevice device);
        [PreserveSig] int GetDevice([MarshalAs(UnmanagedType.LPWStr)] string id, out IMMDevice device);
        [PreserveSig] int RegisterEndpointNotificationCallback(IntPtr client);
        [PreserveSig] int UnregisterEndpointNotificationCallback(IntPtr client);
    }

    [ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDevice {
        [PreserveSig] int Activate(ref Guid iid, int context, IntPtr activation, [MarshalAs(UnmanagedType.IUnknown)] out object instance);
        [PreserveSig] int OpenPropertyStore(int access, out IntPtr store);
        [PreserveSig] int GetId([MarshalAs(UnmanagedType.LPWStr)] out string id);
        [PreserveSig] int GetState(out int state);
    }

    [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
    class MMDeviceEnumeratorComObject { }

    public static class AudioPolicy {
        public static string GetDefault(int role) {
            IMMDeviceEnumerator enumerator = null;
            IMMDevice device = null;
            try {
                enumerator = (IMMDeviceEnumerator)(new MMDeviceEnumeratorComObject());
                int hr = enumerator.GetDefaultAudioEndpoint(1, (ERole)role, out device);
                if (hr != 0 || device == null) return null;
                string id;
                hr = device.GetId(out id);
                return hr == 0 ? id : null;
            }
            finally {
                if (device != null && Marshal.IsComObject(device)) Marshal.ReleaseComObject(device);
                if (enumerator != null && Marshal.IsComObject(enumerator)) Marshal.ReleaseComObject(enumerator);
            }
        }

        public static void SetDefault(string id, int role) {
            IPolicyConfig policy = null;
            try {
                policy = (IPolicyConfig)(new PolicyConfigClient());
                int hr = policy.SetDefaultEndpoint(id, (ERole)role);
                if (hr != 0) Marshal.ThrowExceptionForHR(hr);
            }
            finally {
                if (policy != null && Marshal.IsComObject(policy)) Marshal.ReleaseComObject(policy);
            }
        }

        public static void SetVisible(string id, bool visible) {
            IPolicyConfig policy = null;
            try {
                policy = (IPolicyConfig)(new PolicyConfigClient());
                int hr = policy.SetEndpointVisibility(id, visible);
                if (hr != 0) Marshal.ThrowExceptionForHR(hr);
            }
            finally {
                if (policy != null && Marshal.IsComObject(policy)) Marshal.ReleaseComObject(policy);
            }
        }
    }
}
'@

    Add-Type -TypeDefinition $source -Language CSharp
}

function Get-CodexPackageFamily {
    $package = Get-AppxPackage -Name "OpenAI.Codex" -ErrorAction SilentlyContinue |
        Sort-Object Version -Descending |
        Select-Object -First 1
    if ($package -and $package.PackageFamilyName) {
        return [string]$package.PackageFamilyName
    }
    return "OpenAI.Codex_2p2nqsd0c76g0"
}

function Get-CodexDesktopProcesses {
    return @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -eq "ChatGPT.exe" -or
                ($_.Name -eq "codex.exe" -and [string]$_.CommandLine -match "app-server")
            }
    )
}

function Test-CodexDesktopRunning {
    return @(Get-CodexDesktopProcesses).Count -gt 0
}

function Get-CodexConsentState {
    param([string]$PackageFamily)

    $key = Join-Path $script:ConsentRoot $PackageFamily
    $exists = Test-Path -LiteralPath $key
    $value = $null
    if ($exists) {
        $value = (Get-ItemProperty -LiteralPath $key -ErrorAction SilentlyContinue).Value
    }
    $globalValue = $null
    if (Test-Path -LiteralPath $script:ConsentRoot) {
        $globalValue = (Get-ItemProperty -LiteralPath $script:ConsentRoot -ErrorAction SilentlyContinue).Value
    }
    return [ordered]@{
        PackageFamily = $PackageFamily
        KeyPath = $key
        KeyExisted = $exists
        Value = $value
        GlobalValue = $globalValue
    }
}

function Get-DefaultCaptureEndpoints {
    Initialize-AudioInterop
    $result = [ordered]@{}
    for ($index = 0; $index -lt $script:RoleOrder.Count; $index++) {
        $value = [CodexHybridAudio.AudioPolicy]::GetDefault($index)
        if ([string]::IsNullOrWhiteSpace($value)) {
            $value = $null
        }
        $result[$script:RoleOrder[$index]] = $value
    }
    return $result
}

function Get-CaptureEndpoints {
    $items = @()
    if (-not (Test-Path -LiteralPath $script:CaptureRegistryRoot)) {
        return $items
    }
    foreach ($key in Get-ChildItem -LiteralPath $script:CaptureRegistryRoot -ErrorAction SilentlyContinue) {
        $device = Get-ItemProperty -LiteralPath $key.PSPath -ErrorAction SilentlyContinue
        if (-not $device) { continue }
        $properties = Get-ItemProperty -LiteralPath (Join-Path $key.PSPath "Properties") -ErrorAction SilentlyContinue
        $name = $null
        $description = $null
        if ($properties) {
            $name = $properties.'{a45c254e-df1c-4efd-8020-67d146a850e0},2'
            $description = $properties.'{b3f8fa53-0004-438e-9003-51a46e139bfc},6'
        }
        if ([string]::IsNullOrWhiteSpace([string]$name)) { $name = $description }
        if ([string]::IsNullOrWhiteSpace([string]$name)) { $name = $key.PSChildName }
        $state = [int64]$device.DeviceState
        $kind = "unavailable"
        if ($state -eq 1) { $kind = "active" }
        elseif ($state -eq 268435457) { $kind = "hidden" }
        $items += [pscustomobject]@{
            Id = "{0.0.1.00000000}.$($key.PSChildName)"
            RegistryId = $key.PSChildName
            Name = [string]$name
            Description = [string]$description
            DeviceState = $state
            Kind = $kind
        }
    }
    return @($items | Sort-Object Kind, Name, Id)
}

function Get-ProtectedHashes {
    $paths = @(
        (Join-Path $env:USERPROFILE ".codex\config.toml"),
        (Join-Path $env:USERPROFILE ".codex\auth.json"),
        (Join-Path $env:USERPROFILE ".codex\models_cache.json"),
        (Join-Path $env:USERPROFILE ".codex\state_5.sqlite")
    )
    $result = [ordered]@{}
    foreach ($path in $paths) {
        if (-not (Test-Path -LiteralPath $path)) {
            $result[$path] = "MISSING"
            continue
        }
        try {
            $result[$path] = (Get-FileHash -LiteralPath $path -Algorithm SHA256 -ErrorAction Stop).Hash
        }
        catch {
            $result[$path] = "LOCKED_UNREADABLE"
        }
    }
    return $result
}

function Test-ProtectedHashes {
    param($Before, $After)
    $changed = @()
    $paths = @()
    if ($Before -is [System.Collections.IDictionary]) {
        $paths = @($Before.Keys)
    }
    else {
        $paths = @($Before.PSObject.Properties.Name)
    }
    foreach ($path in $paths) {
        $beforeValue = if ($Before -is [System.Collections.IDictionary]) { $Before[$path] } else { $Before.PSObject.Properties[$path].Value }
        $afterValue = if ($After -is [System.Collections.IDictionary]) { $After[$path] } else { $After.PSObject.Properties[$path].Value }
        if ($beforeValue -ne $afterValue) {
            $changed += $path
        }
    }
    return @($changed)
}

function Get-StableProtectedHashes {
    # Windows may flush Codex's SQLite file a few seconds after the last
    # app-server process exits. Require a bounded quiet window before writing
    # any audio setting so that this normal shutdown flush is not mistaken for
    # a maintenance-script change.
    Start-Sleep -Seconds 4
    $first = Get-ProtectedHashes
    Start-Sleep -Seconds 4
    $second = Get-ProtectedHashes
    $changed = @(Test-ProtectedHashes -Before $first -After $second)
    $unreadable = @($second.Keys | Where-Object { $second[$_] -eq "LOCKED_UNREADABLE" })
    if ($changed.Count -gt 0 -or $unreadable.Count -gt 0) {
        throw "Codex protected state is still settling or locked. Wait a few seconds after fully quitting Codex, then rerun this entry."
    }
    return $second
}

function Get-LiveAudioReport {
    $family = Get-CodexPackageFamily
    $consent = Get-CodexConsentState -PackageFamily $family
    $defaults = Get-DefaultCaptureEndpoints
    $endpoints = @(Get-CaptureEndpoints)
    $missingRoles = @($script:RoleOrder | Where-Object { [string]::IsNullOrWhiteSpace([string]$defaults[$_]) })
    $eligible = @($endpoints | Where-Object { $_.Kind -in @("active", "hidden") })
    $healthy = ($consent.Value -eq "Allow" -and $missingRoles.Count -eq 0)
    return [ordered]@{
        Status = $(if ($healthy) { "healthy" } else { "repair-recommended" })
        CodexRunning = Test-CodexDesktopRunning
        Consent = $consent
        Defaults = $defaults
        MissingRoles = $missingRoles
        EligibleEndpoints = $eligible
        EndpointCount = $eligible.Count
    }
}

function Write-LiveAudioReport {
    param($Report)
    if ($Json) {
        $Report | ConvertTo-Json -Depth 8
        return
    }
    Write-Host "Codex Live audio status: $($Report.Status)"
    Write-Host "Codex running: $($Report.CodexRunning)"
    Write-Host "Codex microphone consent: $($Report.Consent.Value)"
    foreach ($role in $script:RoleOrder) {
        $value = $Report.Defaults[$role]
        if ([string]::IsNullOrWhiteSpace([string]$value)) { $value = "missing" }
        Write-Host "Default capture $role`: $value"
    }
    if ($Report.EligibleEndpoints.Count -gt 0) {
        Write-Host "Eligible recording endpoints:"
        $number = 1
        foreach ($endpoint in $Report.EligibleEndpoints) {
            Write-Host "  [$number] $($endpoint.Name) [$($endpoint.Kind)] $($endpoint.Id)"
            $number++
        }
    }
    else {
        Write-Host "Eligible recording endpoints: none"
    }
}

function Select-CaptureEndpoint {
    param($Report, [string]$RequestedId)

    $existingDefaults = @($script:RoleOrder | ForEach-Object { $Report.Defaults[$_] } | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
    if ($existingDefaults.Count -gt 0 -and [string]::IsNullOrWhiteSpace($RequestedId)) {
        return [string]$existingDefaults[0]
    }

    $candidates = @($Report.EligibleEndpoints)
    if (-not [string]::IsNullOrWhiteSpace($RequestedId)) {
        $match = @($candidates | Where-Object { $_.Id -eq $RequestedId })
        if ($match.Count -ne 1) {
            throw "Requested capture endpoint is not eligible: $RequestedId"
        }
        return [string]$match[0].Id
    }
    if ($candidates.Count -eq 0) {
        throw "No usable recording endpoint was found. Connect or enable a microphone, headset, USB audio input, or Stereo Mix, then rerun this entry."
    }
    if ($candidates.Count -eq 1) {
        return [string]$candidates[0].Id
    }

    Write-Host "Multiple recording endpoints are available."
    for ($index = 0; $index -lt $candidates.Count; $index++) {
        Write-Host "  [$($index + 1)] $($candidates[$index].Name) [$($candidates[$index].Kind)]"
    }
    $selection = Read-Host "Select an endpoint number"
    $number = 0
    if (-not [int]::TryParse($selection, [ref]$number) -or $number -lt 1 -or $number -gt $candidates.Count) {
        throw "No valid endpoint was selected. No audio setting was changed."
    }
    return [string]$candidates[$number - 1].Id
}

function New-LiveAudioBackup {
    param($Report, [string]$SelectedEndpointId)

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $directory = Join-Path $script:BackupParent "live-audio-$stamp"
    New-Item -ItemType Directory -Path $directory -Force | Out-Null
    $regBackup = Join-Path $directory "microphone-consent-before.reg"
    if (Test-Path -LiteralPath $script:ConsentRoot) {
        & reg.exe export $script:ConsentNativeRoot $regBackup /y | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Failed to export microphone consent registry backup." }
    }
    $endpoint = @($Report.EligibleEndpoints | Where-Object { $_.Id -eq $SelectedEndpointId } | Select-Object -First 1)
    $state = [ordered]@{
        SchemaVersion = 1
        CreatedAt = (Get-Date).ToString("o")
        Consent = $Report.Consent
        Defaults = $Report.Defaults
        SelectedEndpointId = $SelectedEndpointId
        SelectedEndpointName = $(if ($endpoint.Count -eq 1) { $endpoint[0].Name } else { $null })
        SelectedEndpointWasHidden = $(if ($endpoint.Count -eq 1) { $endpoint[0].Kind -eq "hidden" } else { $false })
        ProtectedBefore = Get-StableProtectedHashes
        Applied = $false
    }
    $state | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $directory "state.json") -Encoding UTF8
    return [pscustomobject]@{ Directory = $directory; State = $state }
}

function Save-BackupState {
    param([string]$Directory, $State)
    $State | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $Directory "state.json") -Encoding UTF8
}

function Set-CodexMicrophoneConsent {
    param([string]$PackageFamily)
    if (-not (Test-Path -LiteralPath $script:ConsentRoot)) {
        New-Item -Path $script:ConsentRoot -Force | Out-Null
    }
    $key = Join-Path $script:ConsentRoot $PackageFamily
    New-Item -Path $key -Force | Out-Null
    New-ItemProperty -Path $key -Name "Value" -PropertyType String -Value "Allow" -Force | Out-Null
}

function Restore-ConsentFromBackup {
    param([string]$Directory, $State)
    $key = [string]$State.Consent.KeyPath
    if (-not [bool]$State.Consent.KeyExisted -and (Test-Path -LiteralPath $key)) {
        Remove-Item -LiteralPath $key -Recurse -Force
    }
    $regBackup = Join-Path $Directory "microphone-consent-before.reg"
    if (Test-Path -LiteralPath $regBackup) {
        & reg.exe import $regBackup | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Failed to restore microphone consent registry backup." }
    }
}

function Restore-AudioDefaults {
    param($State)
    Initialize-AudioInterop
    for ($index = 0; $index -lt $script:RoleOrder.Count; $index++) {
        $role = $script:RoleOrder[$index]
        $priorId = [string]$State.Defaults.$role
        if (-not [string]::IsNullOrWhiteSpace($priorId)) {
            [CodexHybridAudio.AudioPolicy]::SetDefault($priorId, $index)
        }
    }
    if ([bool]$State.SelectedEndpointWasHidden -and -not [string]::IsNullOrWhiteSpace([string]$State.SelectedEndpointId)) {
        [CodexHybridAudio.AudioPolicy]::SetVisible([string]$State.SelectedEndpointId, $false)
    }
}

function Invoke-LiveAudioRepair {
    if ($Confirm -cne "REPAIR") {
        throw "Type REPAIR exactly in the desktop entry before applying changes."
    }
    if (Test-CodexDesktopRunning) {
        throw "Codex Desktop is running. Fully quit Codex, then rerun this entry."
    }

    $report = Get-LiveAudioReport
    Write-LiveAudioReport -Report $report
    $selectedId = Select-CaptureEndpoint -Report $report -RequestedId $EndpointId
    $backup = New-LiveAudioBackup -Report $report -SelectedEndpointId $selectedId
    $state = $backup.State
    try {
        Set-CodexMicrophoneConsent -PackageFamily ([string]$report.Consent.PackageFamily)
        $selected = @($report.EligibleEndpoints | Where-Object { $_.Id -eq $selectedId } | Select-Object -First 1)
        if ($selected.Count -eq 1 -and $selected[0].Kind -eq "hidden") {
            Initialize-AudioInterop
            [CodexHybridAudio.AudioPolicy]::SetVisible($selectedId, $true)
            Start-Sleep -Milliseconds 750
        }
        Initialize-AudioInterop
        for ($index = 0; $index -lt $script:RoleOrder.Count; $index++) {
            $role = $script:RoleOrder[$index]
            if ([string]::IsNullOrWhiteSpace([string]$report.Defaults[$role])) {
                [CodexHybridAudio.AudioPolicy]::SetDefault($selectedId, $index)
            }
        }

        Start-Sleep -Milliseconds 500
        $afterReport = Get-LiveAudioReport
        if ($afterReport.Consent.Value -ne "Allow" -or $afterReport.MissingRoles.Count -ne 0) {
            throw "Live audio verification failed after repair."
        }
        $state.Applied = $true
        $state.AppliedAt = (Get-Date).ToString("o")
        $state.ProtectedAfter = Get-ProtectedHashes
        $changed = @(Test-ProtectedHashes -Before $state.ProtectedBefore -After $state.ProtectedAfter)
        $state.ProtectedChanged = $changed
        Save-BackupState -Directory $backup.Directory -State $state
        if ($changed.Count -gt 0) {
            throw "A protected Codex file changed during the repair window: $($changed -join ', ')"
        }
        Write-Host "Codex Live audio repair completed."
        Write-Host "Backup: $($backup.Directory)"
        Write-LiveAudioReport -Report $afterReport
    }
    catch {
        try {
            Restore-AudioDefaults -State $state
            Restore-ConsentFromBackup -Directory $backup.Directory -State $state
        }
        catch {
            Write-Warning "Automatic rollback also reported an error: $($_.Exception.Message)"
        }
        throw
    }
}

function Get-LatestLiveAudioBackup {
    if (-not (Test-Path -LiteralPath $script:BackupParent)) { return $null }
    return Get-ChildItem -LiteralPath $script:BackupParent -Directory -Filter "live-audio-*" -ErrorAction SilentlyContinue |
        Where-Object { Test-Path -LiteralPath (Join-Path $_.FullName "state.json") } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Invoke-LiveAudioRestore {
    if ($Confirm -cne "RESTORE") {
        throw "Type RESTORE exactly in the desktop entry before restoring settings."
    }
    if (Test-CodexDesktopRunning) {
        throw "Codex Desktop is running. Fully quit Codex, then rerun this entry."
    }
    $backup = Get-LatestLiveAudioBackup
    if (-not $backup) { throw "No Live audio backup was found." }
    $state = Get-Content -LiteralPath (Join-Path $backup.FullName "state.json") -Raw | ConvertFrom-Json
    Restore-AudioDefaults -State $state
    Restore-ConsentFromBackup -Directory $backup.FullName -State $state
    $after = Get-ProtectedHashes
    $changed = @(Test-ProtectedHashes -Before $state.ProtectedBefore -After $after)
    if ($changed.Count -gt 0) {
        throw "A protected Codex file differs from the repair baseline: $($changed -join ', ')"
    }
    Write-Host "Codex Live audio settings restored from: $($backup.FullName)"
    Write-LiveAudioReport -Report (Get-LiveAudioReport)
}

switch ($Action) {
    "Doctor" {
        $report = Get-LiveAudioReport
        Write-LiveAudioReport -Report $report
        if ($report.Status -eq "healthy") { exit 0 }
        exit 2
    }
    "Repair" {
        Invoke-LiveAudioRepair
        exit 0
    }
    "Restore" {
        Invoke-LiveAudioRestore
        exit 0
    }
}
