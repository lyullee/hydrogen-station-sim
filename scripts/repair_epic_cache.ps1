# Reversible version of Epic's documented webcache refresh. No accounts or games removed.
$ErrorActionPreference='Stop'
if(Get-Process EpicGamesLauncher,EpicWebHelper -ErrorAction SilentlyContinue){
    throw 'Close Epic Games Launcher completely before refreshing its cache.'
}
$savedInput=Join-Path $env:LOCALAPPDATA 'EpicGamesLauncher\Saved'
$saved=(Resolve-Path -LiteralPath $savedInput).Path
$backup=Join-Path $saved ('cache-backup-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
$targets=Get-ChildItem -LiteralPath $saved -Directory | Where-Object {$_.Name -match '^webcache(?:_\d+)?$'}
if(-not $targets){Write-Output 'No Launcher webcache directory found.';exit 0}
$prefix=$saved.TrimEnd('\')+'\'
if(-not [IO.Path]::GetFullPath($backup).StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){throw 'Cache backup outside intended Saved directory'}
New-Item -ItemType Directory -Path $backup | Out-Null
foreach($target in $targets){
    $source=(Resolve-Path -LiteralPath $target.FullName).Path
    $destination=Join-Path $backup $target.Name
    if(-not $source.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase) -or
       -not [IO.Path]::GetFullPath($destination).StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)){
        throw 'Cache path outside intended Saved directory'
    }
    Move-Item -LiteralPath $source -Destination $destination
    Write-Output ('Preserved cache: '+$target.Name)
}
Write-Output 'Launcher cache preserved in a dated backup. Restart Launcher after unlocking the desktop.'
