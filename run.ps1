# Trading Engine - Windows Development Scripts
# Usage: .\run.ps1 [command]

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "Trading Engine - Available Commands:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  .\run.ps1 dev          Start NATS and TimescaleDB only (for local dev)"
    Write-Host "  .\run.ps1 up           Start all services with Docker Compose"
    Write-Host "  .\run.ps1 down         Stop all services"
    Write-Host "  .\run.ps1 logs         View logs for all services"
    Write-Host ""
    Write-Host "  .\run.ps1 gateway      Run ingestion gateway locally"
    Write-Host "  .\run.ps1 aggregator   Run candle aggregator locally"
    Write-Host "  .\run.ps1 sink         Run DB sink locally"
    Write-Host ""
}

function Start-Dev {
    docker-compose up -d nats timescaledb
    Write-Host ""
    Write-Host "Development environment started!" -ForegroundColor Green
    Write-Host "  NATS:        nats://localhost:4222"
    Write-Host "  NATS UI:     http://localhost:8222"
    Write-Host "  TimescaleDB: postgresql://postgres:postgres@localhost:5432/trading"
}

function Start-All {
    docker-compose up -d --build
    Write-Host ""
    Write-Host "All services started!" -ForegroundColor Green
    Write-Host "  Gateway:     http://localhost:8000"
    Write-Host "  NATS:        nats://localhost:4222"
    Write-Host "  TimescaleDB: postgresql://postgres:postgres@localhost:5432/trading"
}

function Stop-All {
    docker-compose down
}

function Show-Logs {
    docker-compose logs -f
}

function Start-Gateway {
    $env:PYTHONPATH = $PWD
    python -m dataflow.ingestion.gateway.main
}

function Start-Aggregator {
    $env:PYTHONPATH = $PWD
    python -m dataflow.candle_aggregation.aggregator
}

function Start-Sink {
    $env:PYTHONPATH = $PWD
    python -m dataflow.persistence.sink
}

switch ($Command) {
    "help"       { Show-Help }
    "dev"        { Start-Dev }
    "up"         { Start-All }
    "down"       { Stop-All }
    "logs"       { Show-Logs }
    "gateway"    { Start-Gateway }
    "aggregator" { Start-Aggregator }
    "sink"       { Start-Sink }
    default      { Show-Help }
}
