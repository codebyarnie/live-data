@echo off
REM Trading Engine - Windows Development Scripts
REM Usage: run.bat [command]

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="dev" goto dev
if "%1"=="up" goto up
if "%1"=="down" goto down
if "%1"=="gateway" goto gateway
if "%1"=="aggregator" goto aggregator
if "%1"=="sink" goto sink
if "%1"=="logs" goto logs
goto help

:help
echo Trading Engine - Available Commands:
echo.
echo   run dev          Start NATS and TimescaleDB only (for local dev)
echo   run up           Start all services with Docker Compose
echo   run down         Stop all services
echo   run logs         View logs for all services
echo.
echo   run gateway      Run ingestion gateway locally
echo   run aggregator   Run candle aggregator locally
echo   run sink         Run DB sink locally
echo.
goto end

:dev
docker-compose up -d nats timescaledb
echo.
echo Development environment started!
echo   NATS:        nats://localhost:4222
echo   NATS UI:     http://localhost:8222
echo   TimescaleDB: postgresql://postgres:postgres@localhost:5432/trading
goto end

:up
docker-compose up -d --build
echo.
echo All services started!
echo   Gateway:     http://localhost:8000
echo   NATS:        nats://localhost:4222
echo   TimescaleDB: postgresql://postgres:postgres@localhost:5432/trading
goto end

:down
docker-compose down
goto end

:logs
docker-compose logs -f
goto end

:gateway
set PYTHONPATH=%CD%
python -m dataflow.ingestion.gateway.main
goto end

:aggregator
set PYTHONPATH=%CD%
python -m dataflow.candle_aggregation.aggregator
goto end

:sink
set PYTHONPATH=%CD%
python -m dataflow.persistence.sink
goto end

:end
