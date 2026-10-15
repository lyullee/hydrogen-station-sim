param(
    [Parameter(Mandatory=$true)][string]$EngineRoot,
    [ValidateSet('Development','Shipping')][string]$Configuration = 'Development',
    [string]$ArchiveDirectory = '',
    [switch]$SkipReferenceAssets
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$engineDir = (Resolve-Path -LiteralPath $EngineRoot).Path
$project = Join-Path $repoRoot 'unreal\HRSUnreal\HRSUnreal.uproject'
$runUat = Join-Path $engineDir 'Engine\Build\BatchFiles\RunUAT.bat'
$pilot = Join-Path $PSScriptRoot 'start_unreal_pilot.ps1'
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
$assetValidation = Join-Path $repoRoot 'output\unreal\assets\validation.json'

foreach ($required in @($project, $runUat, $pilot, $python)) {
    if (-not (Test-Path -LiteralPath $required)) { throw "Required path is missing: $required" }
}
if ([string]::IsNullOrWhiteSpace($ArchiveDirectory)) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $ArchiveDirectory = Join-Path $repoRoot "output\unreal\packages\$stamp"
}
$archive = [IO.Path]::GetFullPath($ArchiveDirectory)
New-Item -ItemType Directory -Path $archive -Force | Out-Null

function Get-ArchiveRelativePath([string]$Root, [string]$Path) {
    $rootWithSeparator = $Root.TrimEnd([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    $fullPath = [IO.Path]::GetFullPath($Path)
    if (-not $fullPath.StartsWith($rootWithSeparator, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Packaged file is outside archive directory: $fullPath"
    }
    return $fullPath.Substring($rootWithSeparator.Length).Replace('\','/')
}

& $python (Join-Path $PSScriptRoot 'check_unreal_source_contract.py')
if ($LASTEXITCODE -ne 0) { throw 'Unreal source contract validation failed' }

$prepare = @{
    EngineRoot = $engineDir
    Build = $true
    Bootstrap = $true
}
if (-not $SkipReferenceAssets) {
    if (-not (Test-Path -LiteralPath $assetValidation)) {
        throw "Reference asset validation is missing: $assetValidation"
    }
    $assetReport = Get-Content -LiteralPath $assetValidation -Raw | ConvertFrom-Json
    if ($assetReport.status -ne 'PASS') { throw 'Reference GLB validation must be PASS before import' }
    $prepare.ImportAssets = $true
    $prepare.PlaceAssets = $true
}
& $pilot @prepare

$uatArgs = @(
    'BuildCookRun',
    "-project=$project",
    '-noP4', '-utf8output', '-platform=Win64', '-target=HRSUnreal',
    "-clientconfig=$Configuration", '-build', '-cook', '-stage', '-pak',
    '-archive', "-archivedirectory=$archive"
)
& $runUat @uatArgs
if ($LASTEXITCODE -ne 0) { throw "Unreal packaging failed: $LASTEXITCODE" }

$executables = @(Get-ChildItem -LiteralPath $archive -Filter '*.exe' -File -Recurse |
    Where-Object { $_.Name -notmatch 'CrashReportClient|UnrealPrereq' })
$launchers = @($executables | Where-Object {
    $_.Name -eq 'HRSUnreal.exe' -and $_.FullName -notmatch '[\\/]Binaries[\\/]'
})
$runtimeName = "HRSUnreal-Win64-$Configuration.exe"
$runtimes = @($executables | Where-Object {
    $_.Name -eq $runtimeName -and $_.FullName -match '[\\/]Binaries[\\/]Win64[\\/]'
})
if ($launchers.Count -ne 1 -or $runtimes.Count -ne 1) {
    throw "Expected one bootstrap launcher and one $runtimeName; found launchers=$($launchers.Count), runtimes=$($runtimes.Count), executables=$($executables.Count)"
}
$launcher = $launchers[0]
$exe = $runtimes[0]
$manifest = [ordered]@{
    schema_version = 2
    created_at = (Get-Date).ToUniversalTime().ToString('o')
    configuration = $Configuration
    executable = Get-ArchiveRelativePath $archive $exe.FullName
    executable_sha256 = (Get-FileHash -LiteralPath $exe.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    bootstrap_executable = Get-ArchiveRelativePath $archive $launcher.FullName
    bootstrap_sha256 = (Get-FileHash -LiteralPath $launcher.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    reference_assets = if ($SkipReferenceAssets) { 'skipped' } else { 'validated_imported_and_placed' }
    source_commit = (git -C $repoRoot rev-parse HEAD).Trim()
    verification = 'PACKAGE_CREATED_NOT_RUNTIME_VERIFIED'
}
$manifestPath = Join-Path $archive 'hrs-unreal-build.json'
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestPath -Encoding utf8
Write-Output "Unreal package runtime created: $($exe.FullName)"
Write-Output "Unreal package bootstrap created: $($launcher.FullName)"
Write-Output "Build manifest: $manifestPath"
