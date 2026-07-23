<#
.SYNOPSIS
    Set up (first run) and start the ss3 gesture-analysis microservice on the
    host at port 8001 — the port the Dockerized backend's Interview Studio
    proxy (CSA_SERVICE_URL) expects.

.DESCRIPTION
    ss3 uses MediaPipe, which needs Python 3.11 (wheels aren't stable on 3.13).
    This script creates a local .venv under ss3/ on first run, installs ss3 in
    editable mode, then launches uvicorn bound to 127.0.0.1:8001.

    The Dockerized backend reaches this host service via host.docker.internal,
    configured in docker-compose.yml.

.EXAMPLE
    ./scripts/run-ss3-local.ps1
#>

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$ss3Dir = Join-Path $repoRoot "ss3"
$venvDir = Join-Path $ss3Dir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $ss3Dir)) {
    throw "ss3 directory not found at $ss3Dir"
}

# Find a Python 3.11 interpreter. MediaPipe wheels don't ship for 3.13.
function Get-Python311 {
    $candidates = @("py -3.11", "python3.11", "python")
    foreach ($c in $candidates) {
        try {
            $parts = $c.Split(" ")
            $ver = & $parts[0] $parts[1..($parts.Length - 1)] --version 2>&1
            if ($ver -match "3\.11") { return $c }
        } catch { }
    }
    return $null
}

if (-not (Test-Path $venvPython)) {
    $py = Get-Python311
    if (-not $py) {
        throw "Python 3.11 not found. Install it (MediaPipe needs 3.11, not 3.13) and retry. See ss3/README.md."
    }
    Write-Host "Creating ss3 virtual environment with $py ..." -ForegroundColor Cyan
    $parts = $py.Split(" ")
    & $parts[0] $parts[1..($parts.Length - 1)] -m venv $venvDir
    Write-Host "Installing ss3 (editable) ..." -ForegroundColor Cyan
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -e "$ss3Dir[dev]"
}

Write-Host "Starting ss3 gesture service on http://127.0.0.1:8001 ..." -ForegroundColor Green
Push-Location $ss3Dir
try {
    & $venvPython -m uvicorn backend.main:app --host 127.0.0.1 --port 8001
} finally {
    Pop-Location
}
