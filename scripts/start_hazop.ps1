param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path $PSScriptRoot -Parent
$pythonExecutable = Join-Path $projectDirectory '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExecutable)) { throw 'Project .venv is missing.' }
& $pythonExecutable -m uvicorn h2station.api:app --app-dir (Join-Path $projectDirectory 'src') --host 127.0.0.1 --port $Port
