param(
    [Parameter(Mandatory=$true)][string]$EngineRoot,
    [string]$ApiUrl = 'http://127.0.0.1:8000',
    [string]$SignallingUrl = 'ws://127.0.0.1:18888',
    [switch]$Build,
    [switch]$Bootstrap,
    [switch]$ImportAssets,
    [switch]$PlaceAssets,
    [switch]$Run
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$projectPath = Join-Path $repoRoot 'unreal\HRSUnreal\HRSUnreal.uproject'
$engineDir = (Resolve-Path -LiteralPath $EngineRoot).Path
$editor = Join-Path $engineDir 'Engine\Binaries\Win64\UnrealEditor.exe'
$editorCmd = Join-Path $engineDir 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$buildScript = Join-Path $engineDir 'Engine\Build\BatchFiles\Build.bat'
$bootstrapScript = Join-Path $repoRoot 'unreal\HRSUnreal\Scripts\bootstrap_scene.py'
$importScript = Join-Path $repoRoot 'unreal\HRSUnreal\Scripts\import_reference_assets.py'
$placeScript = Join-Path $repoRoot 'unreal\HRSUnreal\Scripts\place_reference_scenes.py'
if (-not (Test-Path -LiteralPath $editor)) { throw 'EngineRoot must contain Engine\Binaries\Win64\UnrealEditor.exe' }
if ($Build) {
    & $buildScript HRSUnrealEditor Win64 Development "-Project=$projectPath" -WaitMutex -NoHotReloadFromIDE
    if ($LASTEXITCODE -ne 0) { throw "Unreal build failed: $LASTEXITCODE" }
}
if ($Bootstrap) {
    & $editorCmd $projectPath "-ExecutePythonScript=$bootstrapScript" -unattended -stdout -FullStdOutLogOutput
    if ($LASTEXITCODE -ne 0) { throw "Unreal asset bootstrap failed: $LASTEXITCODE" }
}
if ($ImportAssets) {
    & $editorCmd $projectPath "-ExecutePythonScript=$importScript" -unattended -stdout -FullStdOutLogOutput
    if ($LASTEXITCODE -ne 0) { throw "Unreal reference asset import failed: $LASTEXITCODE" }
}
if ($PlaceAssets) {
    & $editorCmd $projectPath "-ExecutePythonScript=$placeScript" -unattended -stdout -FullStdOutLogOutput
    if ($LASTEXITCODE -ne 0) { throw "Unreal reference scene placement failed: $LASTEXITCODE" }
}
if ($Run) {
    # Runs hidden until the user deliberately opens the pilot window.
    $arguments = @('"' + $projectPath + '"', '-game', '-windowed', '-ResX=1920', '-ResY=1080',
        '-RenderOffscreen', '-AudioMixer', '-PixelStreamingURL=' + $SignallingUrl,
        '-HRSApi=' + $ApiUrl, '-HRSRenderer=default')
    Start-Process -FilePath $editor -ArgumentList $arguments -WindowStyle Hidden
}
if (-not ($Build -or $Bootstrap -or $ImportAssets -or $PlaceAssets -or $Run)) {
    Write-Output 'Engine and project paths verified. Add -Build -Bootstrap -ImportAssets -PlaceAssets -Run to prepare and run the pilot.'
}
