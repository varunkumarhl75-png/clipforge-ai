# ClipForge AI - Startup Script for Windows PowerShell
# This script starts both the backend and frontend in separate windows

param(
    [switch]$SkipBrowser = $false,
    [switch]$BackendOnly = $false,
    [switch]$FrontendOnly = $false
)

$projectRoot = "c:\Users\varun\OneDrive\Desktop\yt video editer"
$backendPath = Join-Path $projectRoot "backend"
$frontendPath = Join-Path $projectRoot "frontend"

Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       ClipForge AI - Local Setup       ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Start Backend
if (-not $FrontendOnly) {
    Write-Host "▶ Starting Backend on http://localhost:8000" -ForegroundColor Green
    $backendCmd = {
        cd $args[0]
        .\venv\Scripts\Activate.ps1
        python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    }
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendPath'; .\venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    Start-Sleep -Seconds 3
}

# Start Frontend
if (-not $BackendOnly) {
    Write-Host "▶ Starting Frontend on http://localhost:3000" -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendPath'; npm run dev"
    Start-Sleep -Seconds 3
}

Write-Host ""
Write-Host "═════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "✓ Backend:   http://localhost:8000" -ForegroundColor Green
Write-Host "✓ Frontend:  http://localhost:3000" -ForegroundColor Green
Write-Host "✓ API Docs:  http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "═════════════════════════════════════════" -ForegroundColor Cyan

# Open browser
if (-not $SkipBrowser) {
    Write-Host ""
    Write-Host "Opening dashboard in browser..." -ForegroundColor Yellow
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:3000"
}

Write-Host ""
Write-Host "Press Ctrl+C in the server windows to stop." -ForegroundColor Yellow
