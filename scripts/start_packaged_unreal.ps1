param(
    [Parameter(Mandatory=$true)][string]$PackageDirectory,
    [string]$ApiUrl = 'http://127.0.0.1:8000',
    [string]$SignallingUrl = 'ws://127.0.0.1:18888',
    [string]$RendererId = 'default',
    [ValidateRange(15,60)][int]$FrameRate = 30,
    [ValidateRange(1000000,100000000)][int]$TargetBitrate = 20000000,
    [bool]$UseNvEncD3D12Cuda = $true,
    [switch]$AllowMultipleInstances,
    [switch]$Visible
)
$ErrorActionPreference = 'Stop'
$package = (Resolve-Path -LiteralPath $PackageDirectory).Path
$manifestPath = Join-Path $package 'hrs-unreal-build.json'
if (-not (Test-Path -LiteralPath $manifestPath)) { throw "Build manifest is missing: $manifestPath" }
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.schema_version -notin @(1, 2)) { throw 'Unsupported Unreal build manifest schema' }
$exe = Join-Path $package ([string]$manifest.executable).Replace('/', '\')
if (-not (Test-Path -LiteralPath $exe)) { throw "Packaged executable is missing: $exe" }
$actualHash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $manifest.executable_sha256) { throw 'Packaged executable hash does not match its build manifest' }
if ($ApiUrl -notmatch '^https?://') { throw 'ApiUrl must use HTTP or HTTPS' }
if ($SignallingUrl -notmatch '^wss?://') { throw 'SignallingUrl must use WS or WSS' }
if ($RendererId -notmatch '^[A-Za-z0-9_-]{1,64}$') { throw 'RendererId contains unsupported characters' }

$running = @(Get-Process -Name ([IO.Path]::GetFileNameWithoutExtension($exe)) -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and ([IO.Path]::GetFullPath($_.Path) -eq [IO.Path]::GetFullPath($exe)) })
if ($running.Count -and -not $AllowMultipleInstances) {
    throw "Packaged Unreal runtime is already running from this package (PID $($running[0].Id)). Stop it first or pass -AllowMultipleInstances."
}

$arguments = @(
    '-windowed', '-ForceRes', '-ResX=1920', '-ResY=1080', '-RenderOffscreen', '-AudioMixer',
    '-PixelStreamingIP=127.0.0.1', '-PixelStreamingPort=18888',
    "-PixelStreamingURL=$SignallingUrl", "-PixelStreamingWebRTCFps=$FrameRate",
    "-PixelStreamingEncoderTargetBitrate=$TargetBitrate", '-PixelStreamingEncoderMultipass=DISABLED',
    '-PixelStreamingEncoderMaxSessions=1', "-ExecCmds=`"t.MaxFPS $FrameRate`"",
    "-HRSApi=$ApiUrl", "-HRSRenderer=$RendererId"
)
if ($UseNvEncD3D12Cuda) { $arguments += '-AVCodecs.NvEnc.D3D12UsesCUDA=true' }
$windowStyle = if ($Visible) { 'Normal' } else { 'Hidden' }
$process = Start-Process -FilePath $exe -ArgumentList $arguments -WindowStyle $windowStyle -PassThru
Write-Output ([ordered]@{process_id=$process.Id; executable=$exe; renderer_id=$RendererId;
    signalling_url=$SignallingUrl; api_url=$ApiUrl; frame_rate=$FrameRate;
    target_bitrate=$TargetBitrate; nvenc_d3d12_cuda=$UseNvEncD3D12Cuda} | ConvertTo-Json -Compress)
