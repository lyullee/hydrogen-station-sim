param(
    [Parameter(Mandatory=$true)][string]$EngineRoot,
    [ValidateRange(60,7200)][int]$DurationSeconds = 3600,
    [ValidateRange(2,60)][int]$IntervalSeconds = 10,
    [string]$OutputPath = 'output\unreal\ue-process-soak.json'
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$engineDir = (Resolve-Path -LiteralPath $EngineRoot).Path
$editorPath = (Join-Path $engineDir 'Engine\Binaries\Win64\UnrealEditor.exe')
if (-not (Test-Path -LiteralPath $editorPath)) { throw 'EngineRoot does not contain UnrealEditor.exe' }
$editorPath = (Resolve-Path -LiteralPath $editorPath).Path
$target = Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and ((Resolve-Path -LiteralPath $_.Path).Path -eq $editorPath) } |
    Select-Object -First 1
if (-not $target) { throw 'The HRS Unreal Editor process is not running from the selected EngineRoot' }

$started = Get-Date
$deadline = $started.AddSeconds($DurationSeconds)
$samples = @()
while ((Get-Date) -lt $deadline) {
    $target.Refresh()
    if ($target.HasExited) { break }
    $samples += [ordered]@{
        observed_at = (Get-Date).ToUniversalTime().ToString('o')
        working_set_mb = [math]::Round($target.WorkingSet64 / 1MB, 2)
        private_memory_mb = [math]::Round($target.PrivateMemorySize64 / 1MB, 2)
        handle_count = $target.HandleCount
        total_processor_s = [math]::Round($target.TotalProcessorTime.TotalSeconds, 3)
    }
    Start-Sleep -Seconds $IntervalSeconds
}
$ended = Get-Date
$observedSeconds = ($ended - $started).TotalSeconds
$first = $samples | Select-Object -First 1
$last = $samples | Select-Object -Last 1
$growth = if ($first -and $last) { $last.working_set_mb - $first.working_set_mb } else { $null }
$allowedGrowth = if ($first) { [math]::Max(256.0, $first.working_set_mb * .2) } else { 0.0 }
$passed = $samples.Count -ge 2 -and $observedSeconds -ge ($DurationSeconds - $IntervalSeconds) -and
    $growth -le $allowedGrowth -and -not $target.HasExited
$report = [ordered]@{
    status = if ($passed) { 'PASS' } else { 'FAIL' }
    process_id = $target.Id
    executable = $editorPath
    requested_duration_s = $DurationSeconds
    observed_duration_s = [math]::Round($observedSeconds, 1)
    interval_s = $IntervalSeconds
    sample_count = $samples.Count
    working_set_growth_mb = if ($null -eq $growth) { $null } else { [math]::Round($growth, 2) }
    allowed_growth_mb = [math]::Round($allowedGrowth, 2)
    maximum_working_set_mb = if ($samples.Count) { ($samples.working_set_mb | Measure-Object -Maximum).Maximum } else { $null }
    maximum_private_memory_mb = if ($samples.Count) { ($samples.private_memory_mb | Measure-Object -Maximum).Maximum } else { $null }
    process_exited = $target.HasExited
    claim_boundary = 'UnrealEditor CPU process memory only; GPU memory and browser decoding are reported separately.'
    samples = $samples
}
$destination = if ([IO.Path]::IsPathRooted($OutputPath)) { $OutputPath } else { Join-Path $repoRoot $OutputPath }
$parent = Split-Path -Parent $destination
New-Item -ItemType Directory -Path $parent -Force | Out-Null
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $destination -Encoding utf8
$report | ConvertTo-Json -Depth 3
if (-not $passed) { exit 1 }
