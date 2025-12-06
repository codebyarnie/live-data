# Trading Engine - Development Makefile
#
# Usage:
#   make help          Show this help message
#   make dev           Start development environment
#   make up            Start all services with Docker Compose
#   make down          Stop all services
#   make logs          View logs
#   make test          Run tests
#   make clean         Clean up containers and volumes

.PHONY: help dev up down logs test clean gateway aggregator sink

help:
	@echo "Trading Engine - Available Commands:"
	@echo ""
	@echo "  make dev          Start NATS and TimescaleDB only (for local dev)"
	@echo "  make up           Start all services with Docker Compose"
	@echo "  make down         Stop all services"
	@echo "  make logs         View logs for all services"
	@echo "  make test         Run tests"
	@echo "  make clean        Clean up containers and volumes"
	@echo ""
	@echo "  make gateway      Run ingestion gateway locally"
	@echo "  make aggregator   Run candle aggregator locally"
	@echo "  make sink         Run DB sink locally"
	@echo "  make query        Run query API locally"
	@echo ""
	@echo "  make init-db      Initialize TimescaleDB schema"
	@echo "  make nats-monitor Open NATS monitoring UI"

# Development environment (infrastructure only)
dev:
	docker-compose up -d nats timescaledb
	@echo ""
	@echo "Development environment started!"
	@echo "  NATS:        nats://localhost:4222"
	@echo "  NATS UI:     http://localhost:8222"
	@echo "  TimescaleDB: postgresql://postgres:postgres@localhost:5432/trading"

# Start all services
up:
	docker-compose up -d --build
	@echo ""
	@echo "All services started!"
	@echo "  Gateway:     http://localhost:8000"
	@echo "  NATS:        nats://localhost:4222"
	@echo "  TimescaleDB: postgresql://postgres:postgres@localhost:5432/trading"

# Stop all services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

logs-gateway:
	docker-compose logs -f ingestion-gateway

logs-aggregator:
	docker-compose logs -f candle-aggregator

logs-sink:
	docker-compose logs -f db-sink

logs-query:
	docker-compose logs -f query-api

# Run services locally (for development)
gateway:
	PYTHONPATH=. python -m dataflow.ingestion.gateway.main

aggregator:
	PYTHONPATH=. python -m dataflow.candle_aggregation.aggregator

sink:
	PYTHONPATH=. python -m dataflow.persistence.sink

query:
	PYTHONPATH=. python -m dataflow.query.api.main

# Initialize database
init-db:
	docker-compose exec timescaledb psql -U postgres -d trading -f /docker-entrypoint-initdb.d/01-schema.sql

# Open NATS monitoring
nats-monitor:
	@echo "Opening NATS monitoring at http://localhost:8222"
	@which xdg-open > /dev/null && xdg-open http://localhost:8222 || open http://localhost:8222

# Run tests
test:
	PYTHONPATH=. pytest tests/ -v

# Clean up everything
clean:
	docker-compose down -v --remove-orphans
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Build Docker images
build:
	docker-compose build

# Rebuild specific service
rebuild-%:
	docker-compose up -d --build $*
