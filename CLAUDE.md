# CLAUDE.md

Always use context7 when I need code generation, setup or configuration steps, or
library/API documentation. This means you should automatically use the Context7 MCP
tools to resolve library id and get library docs without me having to explicitly ask.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Trading Engine** built on a **Directed Acyclic Graph (DAG)** architecture for deterministic, event-driven trading logic. The system processes market data through NATS message streams and persists to TimescaleDB.

**Current Implementation Status**: The codebase currently implements the **data ingestion and aggregation layer** with these working components:
- Ingestion Gateway (FastAPI service receiving data from NinjaTrader)
- Candle Aggregator (ticks → candles for multiple timeframes)
- TimescaleDB Persistence Sink
- Query API (REST API for fetching historical candles)
- NATS messaging infrastructure

**Not yet implemented**: The full DAG engine, indicators, strategies, and market structure detection described in README.md are part of the planned architecture but not yet built.

## Core Architecture

### Data Flow
```
NinjaTrader (HTTP POST)
    → Ingestion Gateway (FastAPI on port 8000)
    → NATS topic: ticks.raw.{symbol}
    → Candle Aggregator
    → NATS topics: candles.{symbol}.{timeframe}
    → TimescaleDB Sink
    → TimescaleDB (PostgreSQL on port 5432)
    ← Query API (FastAPI on port 8001) - Read-only access
```

### Message Types
All events use strongly-typed Python dataclasses in `schemas/market_data.py`:
- **Tick**: Raw tick data (symbol, timestamp, price, volume, bid, ask)
- **Candle**: OHLCV candles with timeframe metadata (1m, 5m, 15m, etc.)
- **Quote**: Bid/ask/spread quote data

All types support `.to_json()`, `.from_json()`, `.to_dict()`, `.from_dict()` for serialization.

### NATS Topic Patterns
Defined in `dataflow/adapters/nats_client.py` via the `Topics` class:
- `ticks.raw.{symbol}` - Raw tick ingestion
- `candles.{symbol}.{timeframe}` - Aggregated candles
- `indicators.{symbol}.{indicator_id}` - Indicator outputs (future)
- `strategies.signals.{symbol}` - Strategy signals (future)

Wildcards:
- `ticks.raw.*` - All ticks
- `candles.>` - All candles (all symbols, all timeframes)

### TimescaleDB Schema
Located in `dataflow/persistence/schema.sql`:
- **ticks**: Raw tick data (hypertable on `time`)
- **candles**: OHLCV candles with unique constraint on (symbol, timeframe, time)
- **market_structure**: Future table for swing points, FVGs, order blocks
- **indicators**: Future table for indicator outputs
- **strategy_signals**: Future table for trading signals

Helper functions: `get_latest_candle()`, `get_candles()`

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Running Infrastructure
```bash
# Start NATS and TimescaleDB only (for local development)
make dev

# Start all services with Docker Compose
make up

# Stop all services
make down

# View logs
make logs                # All services
make logs-gateway        # Ingestion gateway only
make logs-aggregator     # Candle aggregator only
make logs-sink          # Database sink only
make logs-query         # Query API only
```

### Running Services Locally (for development/debugging)
These run services directly with Python instead of Docker:
```bash
# Run ingestion gateway locally
make gateway
# or: PYTHONPATH=. python -m dataflow.ingestion.gateway.main

# Run candle aggregator locally
make aggregator
# or: PYTHONPATH=. python -m dataflow.candle_aggregation.aggregator

# Run database sink locally
make sink
# or: PYTHONPATH=. python -m dataflow.persistence.sink

# Run query API locally
make query
# or: PYTHONPATH=. python -m dataflow.query.api.main
```

### Testing
```bash
# Run tests (when tests are implemented)
make test
# or: PYTHONPATH=. pytest tests/ -v
```

### Database Management
```bash
# Initialize/reset TimescaleDB schema
make init-db

# Connect to database
docker-compose exec timescaledb psql -U postgres -d trading
```

### Monitoring
```bash
# Open NATS monitoring UI at http://localhost:8222
make nats-monitor
```

### Cleanup
```bash
# Clean containers, volumes, and Python cache
make clean
```

## Code Structure

```
dataflow/
├── adapters/
│   └── nats_client.py         # NATS client wrapper with NatsClient, NatsConfig, Topics
├── candle_aggregation/
│   └── aggregator.py          # CandleAggregator: ticks → candles (1m, 5m, 15m, etc.)
├── ingestion/
│   └── gateway/
│       └── main.py            # FastAPI endpoints: POST /data, POST /candle, GET /health
├── persistence/
│   ├── schema.sql             # TimescaleDB schema with hypertables
│   └── sink.py                # TimescaleDBSink: NATS → database persistence
└── query/
    └── api/
        └── main.py            # Query API: GET /candles/{symbol}/{timeframe}

schemas/
└── market_data.py             # Core types: Tick, Candle, Quote

docker/
├── Dockerfile.gateway         # Ingestion gateway container
├── Dockerfile.aggregator      # Candle aggregator container
├── Dockerfile.sink            # DB sink container
└── Dockerfile.query           # Query API container
```

## Key Implementation Details

### Candle Aggregation Logic
The `CandleAggregator` (in `dataflow/candle_aggregation/aggregator.py`):
- Uses `CandleBuilder` to accumulate ticks into candles
- Aligns candles to epoch boundaries using `_get_candle_start()`
- Returns completed candles when a new candle period begins (via `_get_or_create_builder()`)
- Has a backup mechanism (`_check_and_publish_candles()`) that periodically publishes candles that have exceeded their time window
- Supports multiple timeframes defined in `TIMEFRAMES` dict: 1m (60s), 5m (300s), 15m (900s), 30m, 1h, 4h, 1d

### Database Sink Batching
The `TimescaleDBSink` (in `dataflow/persistence/sink.py`):
- Buffers incoming ticks and candles in memory
- Flushes to database when batch size is reached (default: 100) or on interval (default: 1.0s)
- Uses `executemany()` for efficient batch inserts
- Candle inserts use `ON CONFLICT ... DO UPDATE` to handle duplicates
- Supports queue groups for load balancing across multiple instances

### Environment Variables
Services use these environment variables (see `docker-compose.yaml`):
- `NATS_SERVERS`: Comma-separated NATS server URLs (default: `nats://localhost:4222`)
- `NATS_CLIENT_NAME`: Client identifier for NATS connection
- `DATABASE_URL`: PostgreSQL connection string (format: `postgresql://user:pass@host:port/dbname`)
- `BATCH_SIZE`: Number of records to batch before flushing (default: 100)
- `FLUSH_INTERVAL`: Seconds between periodic flushes (default: 1.0)
- `TIMEFRAMES`: Comma-separated timeframes for candle aggregation (default: `1m,5m,15m`)
- `HOST`: FastAPI host (default: `0.0.0.0`)
- `PORT`: FastAPI port (default: `8000`)

### NATS Client Usage Pattern
```python
from dataflow.adapters.nats_client import NatsClient, NatsConfig, Topics

# Initialize and connect
config = NatsConfig.from_env()
nats_client = NatsClient(config)
await nats_client.connect()

# Publishing
tick = Tick(symbol="ES", timestamp=datetime.now(), price=4500.0)
await nats_client.publish_json(Topics.ticks_raw("ES"), tick.to_json())

# Subscribing
async def handle_tick(msg):
    tick = Tick.from_json(msg.data.decode())
    # Process tick...

await nats_client.subscribe(Topics.all_ticks(), handle_tick, queue="my-service")

# Cleanup
await nats_client.close()
```

## Important Coding Patterns

### Timestamps
- All timestamps use Python's `datetime` objects with timezone awareness
- ISO 8601 format for serialization: `.isoformat()` and `.fromisoformat()`
- Handle both `Z` suffix and `+00:00` timezone formats when parsing

### Error Handling
- Services log errors but continue running (resilient to transient failures)
- Database sink retries failed batches by re-adding to buffer
- NATS client has automatic reconnection enabled (`max_reconnect_attempts: -1`)

### Logging
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
```

### Path Management
Many modules add project root to `sys.path` for imports:
```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

## Testing the System

### Send Test Tick via HTTP
```bash
curl -X POST http://localhost:8000/data \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "ES",
    "timestamp": "2024-12-05T10:30:00Z",
    "price": 4500.25,
    "volume": 10,
    "bid": 4500.00,
    "ask": 4500.50
  }'
```

### Query Candles via REST API
```bash
# Get last 100 candles (default)
curl http://localhost:8001/candles/ES/1m

# Get last 50 candles
curl http://localhost:8001/candles/ES/5m?limit=50

# Health check
curl http://localhost:8001/health

# Response format (JSON):
# {
#   "symbol": "ES",
#   "timeframe": "1m",
#   "count": 100,
#   "candles": [
#     {
#       "symbol": "ES",
#       "timestamp": "2024-12-05T10:30:00+00:00",
#       "timeframe": "1m",
#       "open": 4500.25,
#       "high": 4502.50,
#       "low": 4499.75,
#       "close": 4501.00,
#       "volume": 1250.0,
#       "tick_count": 45
#     },
#     ...
#   ]
# }
```

### Query TimescaleDB
```sql
-- View recent ticks
SELECT * FROM ticks ORDER BY time DESC LIMIT 10;

-- View recent candles
SELECT * FROM candles WHERE symbol = 'ES' ORDER BY time DESC LIMIT 10;

-- Get latest 1m candle
SELECT * FROM get_latest_candle('ES', '1m');

-- Get candles in time range
SELECT * FROM get_candles('ES', '5m', NOW() - INTERVAL '1 hour', NOW());
```

## Platform Notes

- Development on **Windows** - use `run.bat` or `run.ps1` for convenience scripts
- Uses **asyncio** throughout for async I/O
- All services are containerized with Docker for consistent deployment
- Production deployment planned for K3s (see README.md section 6 for future architecture)
