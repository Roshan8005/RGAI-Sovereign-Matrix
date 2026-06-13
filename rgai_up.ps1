<#
.SYNOPSIS
RGAI Sovereign Matrix - Version 1.0 Local Master Orchestrator

.DESCRIPTION
This script binds and launches the entire RGAI Sovereign Matrix backend and frontend.
It starts the React Command Center, Discovery Server, Fractal Router, and DICOM Proxy.
#>

# Removed ErrorActionPreference to prevent stderr from terminating the orchestrator

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " 🌐 BOOTING RGAI SOVEREIGN MATRIX ENGINE V1.0 " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Define background jobs
$Jobs = @()

Write-Host "[1/4] Starting React Command Center HUD..." -ForegroundColor Yellow
$Jobs += Start-Job -ScriptBlock {
    Set-Location "G:\projects\Kimi_Agent_RGAI-1 Admin Dashboard Blueprint\app"
    npm run dev
}

Write-Host "[2/4] Starting Discovery Server & Ledger..." -ForegroundColor Yellow
$Jobs += Start-Job -ScriptBlock {
    Set-Location "G:\projects\VirtualUniverse"
    python -u discovery_server.py
}

Start-Sleep -Seconds 2

Write-Host "[3/4] Starting Ternary Fractal Router..." -ForegroundColor Yellow
$Jobs += Start-Job -ScriptBlock {
    Set-Location "G:\projects\VirtualUniverse"
    $env:DISCOVERY_SERVER_URL = 'http://127.0.0.1:5002'
    python -u launcher.py
}

Write-Host "[4/4] Starting DICOM Ingestion Gateway..." -ForegroundColor Yellow
$Jobs += Start-Job -ScriptBlock {
    Set-Location "G:\projects\VirtualUniverse"
    $env:DISCOVERY_SERVER_URL = 'http://127.0.0.1:5002'
    python -u dicom_proxy_gateway.py
}

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "✅ RGAI MATRIX V1.0 IS LIVE!" -ForegroundColor Green
Write-Host " HUD: http://localhost:3000" -ForegroundColor Green
Write-Host " Discovery: http://127.0.0.1:5002" -ForegroundColor Green
Write-Host " Router: UDP 9999" -ForegroundColor Green
Write-Host " DICOM Proxy: Port 11112" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Press Ctrl+C to terminate the matrix." -ForegroundColor White

try {
    # Keep script alive and stream output from jobs
    while ($true) {
        foreach ($job in $Jobs) {
            Receive-Job -Job $job | Write-Host
        }
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "`n[RGAI] Terminating all matrix services..." -ForegroundColor Red
    $Jobs | Stop-Job
    $Jobs | Remove-Job
    Write-Host "[RGAI] Matrix shut down." -ForegroundColor Red
}
