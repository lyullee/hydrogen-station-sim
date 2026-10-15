param(
    [string]$EngineRoot = '',
    [int]$TargetProcessId = 0,
    [ValidateRange(60,7200)][int]$DurationSeconds = 3600,
    [ValidateRange(2,60)][int]$IntervalSeconds = 10,
    [ValidateRange(0,600)][int]$WarmupSeconds = 0,
    [switch]$RequireGpuMemory,
    [string]$OutputPath = 'output\unreal\ue-process-soak.json'
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$targetPath = $null
if ($TargetProcessId -gt 0) {
    $target = Get-Process -Id $TargetProcessId -ErrorAction Stop
    if (-not $target.Path) { throw "Process $TargetProcessId does not expose an executable path" }
    $targetPath = (Resolve-Path -LiteralPath $target.Path).Path
}
elseif ($EngineRoot) {
    $engineDir = (Resolve-Path -LiteralPath $EngineRoot).Path
    $editorPath = (Join-Path $engineDir 'Engine\Binaries\Win64\UnrealEditor.exe')
    if (-not (Test-Path -LiteralPath $editorPath)) { throw 'EngineRoot does not contain UnrealEditor.exe' }
    $targetPath = (Resolve-Path -LiteralPath $editorPath).Path
    $target = Get-Process -Name UnrealEditor -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -and ((Resolve-Path -LiteralPath $_.Path).Path -eq $targetPath) } |
        Select-Object -First 1
    if (-not $target) { throw 'The HRS Unreal Editor process is not running from the selected EngineRoot' }
}
else {
    throw 'Specify either TargetProcessId for a packaged runtime or EngineRoot for UnrealEditor'
}

function Get-GpuMemory([int]$ProcessId) {
    try {
        $pattern = "^pid_$ProcessId(?:_|$)"
        $dedicated = (Get-Counter '\GPU Process Memory(*)\Dedicated Usage' -ErrorAction Stop).CounterSamples |
            Where-Object { $_.InstanceName -match $pattern } |
            Measure-Object -Property CookedValue -Sum
        $shared = (Get-Counter '\GPU Process Memory(*)\Shared Usage' -ErrorAction Stop).CounterSamples |
            Where-Object { $_.InstanceName -match $pattern } |
            Measure-Object -Property CookedValue -Sum
        $adapter = (Get-Counter '\GPU Adapter Memory(*)\Dedicated Usage' -ErrorAction Stop).CounterSamples |
            Measure-Object -Property CookedValue -Sum
        $processMb = [math]::Round([double]$dedicated.Sum / 1MB, 2)
        $adapterMb = [math]::Round([double]$adapter.Sum / 1MB, 2)
        # The Windows per-process counter can report impossible cumulative values
        # when NVENC maps D3D12 resources through CUDA. Reject it when it exceeds
        # the complete adapter allocation and use the adapter counter instead.
        $processCounterValid = $dedicated.Count -gt 0 -and $processMb -le [math]::Max(256.0, $adapterMb * 1.25)
        return [ordered]@{
            available = $processCounterValid -or $adapter.Count -gt 0
            dedicated_mb = if ($processCounterValid) { $processMb } else { $adapterMb }
            shared_mb = [math]::Round([double]$shared.Sum / 1MB, 2)
            source = if ($processCounterValid) { 'windows_process_counter' } else { 'windows_adapter_counter' }
            process_counter_raw_mb = $processMb
            adapter_dedicated_mb = $adapterMb
        }
    }
    catch {
        return [ordered]@{available=$false; dedicated_mb=$null; shared_mb=$null; source='unavailable';
            process_counter_raw_mb=$null; adapter_dedicated_mb=$null}
    }
}

if ($WarmupSeconds -gt 0) { Start-Sleep -Seconds $WarmupSeconds }
$started = Get-Date
$deadline = $started.AddSeconds($DurationSeconds)
$samples = @()
while ((Get-Date) -lt $deadline) {
    $target.Refresh()
    if ($target.HasExited) { break }
    $gpu = Get-GpuMemory $target.Id
    $samples += [ordered]@{
        observed_at = (Get-Date).ToUniversalTime().ToString('o')
        working_set_mb = [math]::Round($target.WorkingSet64 / 1MB, 2)
        private_memory_mb = [math]::Round($target.PrivateMemorySize64 / 1MB, 2)
        handle_count = $target.HandleCount
        total_processor_s = [math]::Round($target.TotalProcessorTime.TotalSeconds, 3)
        gpu_dedicated_mb = $gpu.dedicated_mb
        gpu_shared_mb = $gpu.shared_mb
        gpu_memory_source = $gpu.source
        gpu_process_counter_raw_mb = $gpu.process_counter_raw_mb
        gpu_adapter_dedicated_mb = $gpu.adapter_dedicated_mb
    }
    Start-Sleep -Seconds $IntervalSeconds
}
$ended = Get-Date
$observedSeconds = ($ended - $started).TotalSeconds
$first = $samples | Select-Object -First 1
$last = $samples | Select-Object -Last 1
$growth = if ($first -and $last) { $last.working_set_mb - $first.working_set_mb } else { $null }
$privateGrowth = if ($first -and $last) { $last.private_memory_mb - $first.private_memory_mb } else { $null }
$handleGrowth = if ($first -and $last) { $last.handle_count - $first.handle_count } else { $null }
$gpuGrowth = if ($first -and $last -and $null -ne $first.gpu_dedicated_mb -and $null -ne $last.gpu_dedicated_mb) {
    $last.gpu_dedicated_mb - $first.gpu_dedicated_mb
} else { $null }
$allowedGrowth = if ($first) { [math]::Max(256.0, $first.working_set_mb * .2) } else { 0.0 }
$allowedPrivateGrowth = if ($first) { 512.0 } else { 0.0 }
$allowedGpuGrowth = if ($first -and $null -ne $first.gpu_dedicated_mb) {
    [math]::Max(256.0, $first.gpu_dedicated_mb * .2)
} else { 0.0 }
$gpuAvailable = [bool]($samples | Where-Object { $null -ne $_.gpu_dedicated_mb } | Select-Object -First 1)
$maximumWorkingSet = if ($samples.Count) { ($samples.working_set_mb | Measure-Object -Maximum).Maximum } else { $null }
$maximumPrivateMemory = if ($samples.Count) { ($samples.private_memory_mb | Measure-Object -Maximum).Maximum } else { $null }
$maximumHandles = if ($samples.Count) { ($samples.handle_count | Measure-Object -Maximum).Maximum } else { $null }
$maximumGpuDedicated = if ($samples.Count) { ($samples.gpu_dedicated_mb | Measure-Object -Maximum).Maximum } else { $null }
$maximumGpuShared = if ($samples.Count) { ($samples.gpu_shared_mb | Measure-Object -Maximum).Maximum } else { $null }
$gpuSources = @($samples.gpu_memory_source | Sort-Object -Unique)
$peakWorkingGrowth = if ($first -and $null -ne $maximumWorkingSet) { $maximumWorkingSet - $first.working_set_mb } else { $null }
$peakPrivateGrowth = if ($first -and $null -ne $maximumPrivateMemory) { $maximumPrivateMemory - $first.private_memory_mb } else { $null }
$peakHandleGrowth = if ($first -and $null -ne $maximumHandles) { $maximumHandles - $first.handle_count } else { $null }
$peakGpuGrowth = if ($first -and $null -ne $maximumGpuDedicated) { $maximumGpuDedicated - $first.gpu_dedicated_mb } else { $null }
$passed = $samples.Count -ge 2 -and $observedSeconds -ge ($DurationSeconds - $IntervalSeconds) -and
    $peakWorkingGrowth -le $allowedGrowth -and $peakPrivateGrowth -le $allowedPrivateGrowth -and
    $peakHandleGrowth -le 512 -and -not $target.HasExited
if ($RequireGpuMemory) {
    $passed = $passed -and $gpuAvailable -and $null -ne $peakGpuGrowth -and $peakGpuGrowth -le $allowedGpuGrowth
}
$report = [ordered]@{
    status = if ($passed) { 'PASS' } else { 'FAIL' }
    process_id = $target.Id
    executable = $targetPath
    requested_duration_s = $DurationSeconds
    warmup_s = $WarmupSeconds
    observed_duration_s = [math]::Round($observedSeconds, 1)
    interval_s = $IntervalSeconds
    sample_count = $samples.Count
    working_set_growth_mb = if ($null -eq $growth) { $null } else { [math]::Round($growth, 2) }
    peak_working_set_growth_mb = if ($null -eq $peakWorkingGrowth) { $null } else { [math]::Round($peakWorkingGrowth, 2) }
    allowed_growth_mb = [math]::Round($allowedGrowth, 2)
    private_memory_growth_mb = if ($null -eq $privateGrowth) { $null } else { [math]::Round($privateGrowth, 2) }
    peak_private_memory_growth_mb = if ($null -eq $peakPrivateGrowth) { $null } else { [math]::Round($peakPrivateGrowth, 2) }
    allowed_private_memory_growth_mb = [math]::Round($allowedPrivateGrowth, 2)
    handle_growth = $handleGrowth
    peak_handle_growth = $peakHandleGrowth
    allowed_handle_growth = 512
    maximum_working_set_mb = $maximumWorkingSet
    maximum_private_memory_mb = $maximumPrivateMemory
    gpu_process_memory_available = $gpuAvailable
    gpu_process_memory_required = [bool]$RequireGpuMemory
    gpu_dedicated_growth_mb = if ($null -eq $gpuGrowth) { $null } else { [math]::Round($gpuGrowth, 2) }
    peak_gpu_dedicated_growth_mb = if ($null -eq $peakGpuGrowth) { $null } else { [math]::Round($peakGpuGrowth, 2) }
    allowed_gpu_dedicated_growth_mb = [math]::Round($allowedGpuGrowth, 2)
    maximum_gpu_dedicated_mb = $maximumGpuDedicated
    maximum_gpu_shared_mb = $maximumGpuShared
    gpu_memory_sources = $gpuSources
    process_exited = $target.HasExited
    claim_boundary = 'Selected Unreal process memory plus Windows GPU memory counters. The adapter counter is used when the per-process counter is physically impossible under CUDA interop; browser decoding is reported separately.'
    samples = $samples
}
$destination = if ([IO.Path]::IsPathRooted($OutputPath)) { $OutputPath } else { Join-Path $repoRoot $OutputPath }
$parent = Split-Path -Parent $destination
New-Item -ItemType Directory -Path $parent -Force | Out-Null
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $destination -Encoding utf8
$report | ConvertTo-Json -Depth 3
if (-not $passed) { exit 1 }
