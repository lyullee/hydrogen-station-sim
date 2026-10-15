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
$editorLog = Join-Path $repoRoot 'unreal\HRSUnreal\Saved\Logs\HRSUnreal.log'
if (-not (Test-Path -LiteralPath $editor)) { throw 'EngineRoot must contain Engine\Binaries\Win64\UnrealEditor.exe' }
function Invoke-UnrealPython([string]$ScriptPath, [string]$StepName, [string]$SuccessPattern) {
    & $editorCmd $projectPath "-ExecutePythonScript=$ScriptPath" -unattended -stdout -FullStdOutLogOutput
    if ($LASTEXITCODE -ne 0) { throw "Unreal $StepName failed: $LASTEXITCODE" }
    if (-not (Test-Path -LiteralPath $editorLog)) { throw "Unreal $StepName produced no editor log" }
    $logText = Get-Content -LiteralPath $editorLog -Raw
    if ($logText -match 'LogPython: Error:' -or $logText -notmatch [regex]::Escape($SuccessPattern)) {
        $pythonErrors = Select-String -LiteralPath $editorLog -Pattern 'LogPython: Error:' |
            Select-Object -Last 12 | ForEach-Object { $_.Line }
        throw "Unreal $StepName reported a Python error or omitted its success marker.`n$($pythonErrors -join "`n")"
    }
}
if ($Build) {
    & $buildScript HRSUnrealEditor Win64 Development "-Project=$projectPath" -WaitMutex -NoHotReloadFromIDE
    if ($LASTEXITCODE -ne 0) { throw "Unreal build failed: $LASTEXITCODE" }
}
if ($Bootstrap) {
    Invoke-UnrealPython $bootstrapScript 'asset bootstrap' 'HRS reference scene assets ready'
}
if ($ImportAssets) {
    Invoke-UnrealPython $importScript 'reference asset import' 'HRS reference model import complete'
}
if ($PlaceAssets) {
    Invoke-UnrealPython $placeScript 'reference scene placement' 'HRS reference scene placement complete'
}
if ($Run) {
    # Runs hidden until the user deliberately opens the pilot window.
    $arguments = @('"' + $projectPath + '"', '-game', '-windowed', '-ForceRes', '-ResX=1920', '-ResY=1080',
        '-RenderOffscreen', '-AudioMixer', '-PixelStreamingURL=' + $SignallingUrl,
        '-HRSApi=' + $ApiUrl, '-HRSRenderer=default')
    Start-Process -FilePath $editor -ArgumentList $arguments -WindowStyle Hidden
}
if (-not ($Build -or $Bootstrap -or $ImportAssets -or $PlaceAssets -or $Run)) {
    Write-Output 'Engine and project paths verified. Add -Build -Bootstrap -ImportAssets -PlaceAssets -Run to prepare and run the pilot.'
}
