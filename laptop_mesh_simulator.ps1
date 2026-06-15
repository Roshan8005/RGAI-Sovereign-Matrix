<#
.SYNOPSIS
RGAI Sovereign Matrix - Laptop End-to-End Mesh Simulator

.DESCRIPTION
This script binds and launches the RGAI Orchestrator, simulated Android node swarm on local loopback ports, and automatically triggers the mock DICOM injection tool to demonstrate offline Ternary compression mesh in a single terminal.
#>


Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " 🌐 BOOTING RGAI LAPTOP MESH SIMULATOR " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$Jobs = @()
$WorkingDir = $PSScriptRoot

# Cleanup function
function Cleanup {
    Write-Host "`n[RGAI] Terminating all simulated mesh nodes..." -ForegroundColor Red
    $Jobs | Stop-Job -ErrorAction SilentlyContinue
    $Jobs | Remove-Job -ErrorAction SilentlyContinue
    Write-Host "[RGAI] Simulation shut down safely." -ForegroundColor Red
}



# 1. Start Orchestrator
Write-Host "[1/3] Starting Master Orchestrator (Port 8080)..." -ForegroundColor Yellow
$Jobs += Start-Job -ScriptBlock {
    Set-Location $using:WorkingDir
    python -u rgai_orchestrator.py
}

Start-Sleep -Seconds 3

# 2. Start Phone Nodes
Write-Host "[2/3] Bootstrapping Simulated Android Swarm..." -ForegroundColor Yellow

$nodes = @(
    @{ ID="LAPTOP_SIM_NODE_ALPHA"; Port=9999 },
    @{ ID="LAPTOP_SIM_NODE_BETA"; Port=10000 },
    @{ ID="LAPTOP_SIM_NODE_GAMMA"; Port=10001 }
)

foreach ($node in $nodes) {
    Write-Host "  -> Launching $($node.ID) on UDP Port $($node.Port)" -ForegroundColor DarkGray
    $job = Start-Job -ScriptBlock {
        Set-Location $using:WorkingDir
        $env:RGAI_NODE_ID = $using:node.ID
        $env:RGAI_NODE_PORT = $using:node.Port
        $env:RGAI_HEARTBEAT_INTERVAL = "3"
        # Discovery directed to local Orchestrator
        $env:DISCOVERY_SERVER_URL = "http://127.0.0.1:8080"
        python -u rgai_phone_node.py
    }
    $Jobs += $job
    Start-Sleep -Seconds 1
}

Write-Host "Waiting 5 seconds for mesh topology to stabilize..." -ForegroundColor Cyan
Start-Sleep -Seconds 5

# 3. Trigger Mock Clinical Run
Write-Host "[3/3] Injecting Mock TCIA MRI DICOM Payload..." -ForegroundColor Magenta
$Jobs += Start-Job -ScriptBlock {
    Set-Location $using:WorkingDir
    python -u mock_clinical_run.py --phantom-size 2
}

Write-Host "==========================================================" -ForegroundColor Green
Write-Host "✅ RGAI LAPTOP MESH SIMULATION RUNNING!" -ForegroundColor Green
Write-Host "Press Ctrl+C to terminate the simulation at any time." -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Green

try {
    while ($true) {
        foreach ($job in $Jobs) {
            Receive-Job -Job $job | Write-Host
        }
        Start-Sleep -Milliseconds 500
    }
} finally {
    Cleanup
}
