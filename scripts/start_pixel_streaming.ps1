param([int]$PlayerPort=18080, [int]$StreamerPort=18888)
$ErrorActionPreference='Stop'
$repoRoot=Split-Path -Parent $PSScriptRoot
$infra=Join-Path $repoRoot 'unreal\PixelStreamingInfrastructure'
$nodeExe=Join-Path $repoRoot 'unreal\.tooling\node-v22.14.0-win-x64\node.exe'
$entry=Join-Path $infra 'SignallingWebServer\dist\index.js'
$www=Join-Path $infra 'SignallingWebServer\www'
$wrapper=Join-Path $PSScriptRoot 'pixel_streaming_local.cjs'
if(-not(Test-Path -LiteralPath $nodeExe)){throw 'Node 22.14.0 portable runtime is not installed. See unreal/README.md.'}
if(-not(Test-Path -LiteralPath $entry)){throw 'Build the pinned Pixel Streaming infrastructure first. See unreal/README.md.'}
Copy-Item -LiteralPath (Join-Path $repoRoot 'unreal\player\hrs-player.html') -Destination $www -Force
Copy-Item -LiteralPath (Join-Path $repoRoot 'unreal\player\hrs-player.js') -Destination $www -Force
& $nodeExe $wrapper $entry --no_config --serve --player_port $PlayerPort --streamer_port $StreamerPort --sfu_port 18889 --http_root $www --homepage hrs-player.html
