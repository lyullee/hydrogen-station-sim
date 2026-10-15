param(
    [ValidatePattern('^\d+\.\d+$')][string]$Version = '5.6',
    [switch]$PrintOnly
)
$ErrorActionPreference = 'Stop'

$engineRoot = "C:\Program Files\Epic Games\UE_$Version"
$editor = Join-Path $engineRoot 'Engine\Binaries\Win64\UnrealEditor.exe'
if (Test-Path -LiteralPath $editor) {
    Write-Output "Unreal Engine $Version is already installed: $engineRoot"
    exit 0
}

$launcherCandidates = @(
    'C:\Program Files\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe',
    'C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win64\EpicGamesLauncher.exe',
    'C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe'
)
$launcher = $launcherCandidates | Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1
$catalog = 'C:\ProgramData\Epic\EpicGamesLauncher\Data\EMS\EpicGamesLauncher\ue.v9product'
if (-not $launcher) {
    throw "Epic Games Launcher is missing. Checked: $($launcherCandidates -join ', ')"
}
if (-not (Test-Path -LiteralPath $catalog)) {
    throw "Required Epic catalog is missing: $catalog"
}

$product = Get-Content -LiteralPath $catalog -Raw | ConvertFrom-Json
$appId = "UE_$Version"
$app = @($product.Apps | Where-Object { $_.AppId -eq $appId }) | Select-Object -First 1
if (-not $app) { throw "Epic's local catalog does not list $appId. Restart or update Launcher first." }
if ([string]::IsNullOrWhiteSpace($app.ItemId)) { throw "$appId has no Epic catalog item ID." }

# Epic's documented protocol action=installer bypasses the unreliable generic
# Install Engine button and opens the options dialog for this exact artifact.
$uri = "com.epicgames.launcher://apps/ue%3A$($app.ItemId)%3A$($app.AppId)?action=installer"
if ($PrintOnly) {
    Write-Output $uri
    exit 0
}
Write-Output "Opening the exact $appId installer from Epic's refreshed local catalog."
Start-Process -FilePath $uri
