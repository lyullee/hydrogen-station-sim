param(
    [string]$InstallerPath = "$env:TEMP\EpicInstaller-18.12.1.msi",
    [string]$ExpectedSha256 = '8DC09359E3E33A3818A09432337D390DE5FB640400CC5E21FCABBFB2E02BEC91'
)
$ErrorActionPreference = 'Stop'

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Run this script from an Administrator PowerShell session.'
}

$installer = (Resolve-Path -LiteralPath $InstallerPath).Path
$signature = Get-AuthenticodeSignature -LiteralPath $installer
if ($signature.Status -ne 'Valid' -or
    $signature.SignerCertificate.Subject -notlike '*Epic Games Inc.*') {
    throw 'The legacy Launcher installer does not have a valid Epic Games Inc. signature.'
}
$actualHash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash
if ($actualHash -ne $ExpectedSha256) {
    throw "Legacy Launcher installer hash mismatch: $actualHash"
}

$savedInput = Join-Path $env:LOCALAPPDATA 'EpicGamesLauncher\Saved'
if (Test-Path -LiteralPath $savedInput) {
    $saved = (Resolve-Path -LiteralPath $savedInput).Path
    # Keep the backup outside EpicGamesLauncher's own directory. The MSI
    # uninstaller may remove that complete directory, including unknown files.
    $backupRoot = Join-Path $env:LOCALAPPDATA 'EpicLauncherStateBackups'
    New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
    $backupRoot = (Resolve-Path -LiteralPath $backupRoot).Path
    $backup = Join-Path $backupRoot ('Saved-before-legacy-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    $prefix = $backupRoot.TrimEnd('\') + '\'
    if (-not [IO.Path]::GetFullPath($backup).StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Epic Launcher backup path escaped the intended backup directory.'
    }
    Copy-Item -LiteralPath $saved -Destination $backup -Recurse -Force
    Write-Output "Preserved Epic Launcher state: $backup"
}

Get-Process EpicGamesLauncher, EpicWebHelper -ErrorAction SilentlyContinue |
    Stop-Process -Force

$uninstallEntries = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
$current = Get-ItemProperty $uninstallEntries -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -eq 'Epic Games Launcher' } |
    Select-Object -First 1
if ($current) {
    $match = [regex]::Match($current.UninstallString, '\{[0-9A-Fa-f-]{36}\}')
    if (-not $match.Success) { throw 'Unable to read the installed Launcher product code.' }
    $uninstallLog = Join-Path $env:TEMP 'EpicLauncherCurrentUninstall-elevated.log'
    $uninstall = Start-Process -FilePath 'msiexec.exe' -ArgumentList @(
        '/x', $match.Value, '/qn', '/norestart', "/L*v `"$uninstallLog`""
    ) -Wait -PassThru -WindowStyle Hidden
    if ($uninstall.ExitCode -notin @(0, 3010)) {
        throw "Current Launcher uninstall failed with code $($uninstall.ExitCode). Log: $uninstallLog"
    }
}

$installLog = Join-Path $env:TEMP 'EpicLauncherLegacyInstall-elevated.log'
$install = Start-Process -FilePath 'msiexec.exe' -ArgumentList @(
    '/i', "`"$installer`"", '/qn', '/norestart', "/L*v `"$installLog`""
) -Wait -PassThru -WindowStyle Hidden
if ($install.ExitCode -notin @(0, 3010)) {
    throw "Legacy Launcher install failed with code $($install.ExitCode). Log: $installLog"
}

$launcherCandidates = @(
    'C:\Program Files\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe',
    'C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe',
    'C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe'
)
$launcher = $launcherCandidates | Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1
if (-not $launcher) {
    throw 'Legacy Launcher installer completed but the executable is missing.'
}
Write-Output "Epic legacy Launcher installed and verified: $launcher"
Write-Output 'No reboot was requested. Start the Launcher normally, sign in if required, then open the UE 5.6 installer.'
