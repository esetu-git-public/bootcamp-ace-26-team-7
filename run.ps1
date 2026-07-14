#!/usr/bin/env pwsh
param()

$RootDir = Split-Path -Parent $PSCommandPath
$BackendPort = 8501
$FrontendPort = 5173

# -- 1. Python backend ---------------------------------
$VenvDir = "$RootDir/venv"
if (-not (Test-Path "$VenvDir/Scripts/python.exe")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
    python -m venv $VenvDir
}

Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
& "$VenvDir/Scripts/pip" install -r "$RootDir/requirements.txt"
if ($LASTEXITCODE -ne 0) {
    Write-Host "pip install failed -- recreating venv and retrying..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $VenvDir -ErrorAction SilentlyContinue
    python -m venv $VenvDir
    & "$VenvDir/Scripts/pip" install -r "$RootDir/requirements.txt"
}

# -- 2. Node frontend ----------------------------------
$FrontendDir = "$RootDir/frontend"
if (Test-Path $FrontendDir) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Cyan
    Push-Location $FrontendDir
    npm install
    Pop-Location
} else {
    Write-Warning "Frontend directory not found at $FrontendDir"
}

# -- 3. Start both services ----------------------------
Write-Host "`n==============================================" -ForegroundColor Green
Write-Host " Starting Surface Crack Detection App" -ForegroundColor Green
Write-Host "==============================================`n" -ForegroundColor Green

$apiJob = Start-Job -ScriptBlock {
    param($VenvDir, $RootDir, $BackendPort)
    Set-Location $RootDir
    & "$VenvDir/Scripts/python" -m uvicorn backend.main:app --host 0.0.0.0 --port $BackendPort
} -ArgumentList $VenvDir, $RootDir, $BackendPort

Write-Host " * API running at http://localhost:$BackendPort" -ForegroundColor Yellow

if (Test-Path $FrontendDir) {
    $frontendJob = Start-Job -ScriptBlock {
        param($FrontendDir)
        Set-Location $FrontendDir
        npm run dev
    } -ArgumentList $FrontendDir
    Write-Host " * Frontend starting at http://localhost:$FrontendPort" -ForegroundColor Yellow
}

Write-Host "`n Press Ctrl+C to stop both services`n" -ForegroundColor Cyan

try {
    while ($true) {
        Start-Sleep -Seconds 1
        $running = $false
        if ($apiJob.State -eq 'Running') { $running = $true }
        if ($frontendJob -and $frontendJob.State -eq 'Running') { $running = $true }
        if (-not $running) { break }
    }
} finally {
    Write-Host "`nShutting down..." -ForegroundColor Yellow
    if ($apiJob) { Stop-Job $apiJob -ErrorAction SilentlyContinue; Remove-Job $apiJob -Force -ErrorAction SilentlyContinue }
    if ($frontendJob) { Stop-Job $frontendJob -ErrorAction SilentlyContinue; Remove-Job $frontendJob -Force -ErrorAction SilentlyContinue }
}
