# Trading Engine - Unified Architecture Specification

## 1. Core Concept

This system implements a **Directed Acyclic Graph (DAG)** of computation nodes for deterministic, event-driven trading logic.

**Key Principles:**
- Each node (indicator/strategy) computes **exactly once** per triggering event
- Execution follows strict topological order
- No race conditions, no duplicate computations
- Supports arbitrary cross-timeframe and cross-indicator dependencies

**Event Flow:**
1. Event arrives (Tick, Candle, or derived data)
2. System identifies impacted nodes via reverse dependency graph
3. Nodes execute in topological order
4. Outputs published to NATS and persisted to TimescaleDB

---

## 2. Typed Message Catalog

All events flowing through the system use **strongly-typed message schemas**.

### Core Message Types

```
types/
├── market_data.py          # Base market data types
│   ├── Tick                # Raw tick data
│   ├── Candle              # OHLCV with timeframe metadata
│   └── Quote               # Bid/Ask/Spread
│
├── market_structure.py     # Technical analysis primitives
│   ├── SwingPoint          # Higher high, lower low, etc.
│   ├── FairValueGap        # Imbalance/gap detection
│   ├── OrderBlock          # Supply/demand zones
│   ├── LiquidityLevel      # Support/resistance clusters
│   └── BreakOfStructure    # BOS/CHoCH events
│
├── volume_analysis.py      # Volume-based signals
│   ├── VolumeProfile       # Distribution by price level
│   ├── DeltaVolume         # Buy vs sell volume
│   ├── Footprint           # Bid/ask ladder snapshot
│   └── CumulativeDelta     # Running delta accumulation
│
├── indicators.py           # Standard indicator outputs
│   ├── MovingAverage       # SMA, EMA, WMA outputs
│   ├── VWAP                # Volume-weighted average price
│   ├── RSI                 # Relative strength
│   └── ATR                 # Average true range
│
└── strategy_signals.py     # Strategy outputs
    ├── TradeSignal         # Entry/exit recommendations
    ├── PositionUpdate      # Live position status
    └── RiskMetric          # Stop loss, take profit levels
```

### Message Schema Structure

Every message includes:
- **symbol**: Instrument identifier
- **timestamp**: Event time (ISO 8601)
- **timeframe**: Applicable TF (for candles/indicators)
- **type**: Message discriminator
- **data**: Type-specific payload
- **metadata**: Optional context (source, version, etc.)

Example:
```python
@dataclass
class SwingPoint:
    symbol: str
    timestamp: datetime
    timeframe: str
    type: Literal["higher_high", "lower_low", "equal_high", "equal_low"]
    price: float
    bar_index: int
    strength: int  # How many bars confirmed this swing
    metadata: dict
```

---

## 3. NATS Usage Patterns

### External NATS (Public Interface)

**Purpose:** Ingest raw market data and publish final outputs

**Topics:**
```
# INGESTION (External → System)
ticks.raw.{symbol}                    # From NinjaTrader, IB, etc.
candles.external.{symbol}.{tf}        # Pre-aggregated candles

# PUBLICATION (System → External)
indicators.public.{symbol}.{id}       # For dashboards, alerts
strategies.signals.{symbol}           # Trade signals
strategies.positions.{symbol}         # Position updates
market_structure.{symbol}.{type}      # SwingPoints, FVGs, etc.
```

### Internal NATS (Within Engine Network)

**Purpose:** Coordinate DAG execution and state propagation

**Topics:**
```
# INTERNAL EVENTS
candles.internal.{symbol}.{tf}        # Aggregated candles (1m→5m→15m)
indicators.internal.{symbol}.{id}     # Indicator outputs for dependencies
dag.trigger.{symbol}                  # DAG execution requests
state.snapshot.{symbol}               # State persistence events
```

**Why Two Layers?**
- **External**: Contract with outside world (stable API, versioned)
- **Internal**: Implementation detail (can change freely, optimized for throughput)

**Connection Point:** `dataflow/ingestion/` consumes external NATS, feeds internal DAG

---

## 4. TimescaleDB Placement & Schema

### Location in Architecture

TimescaleDB sits as a **sink service** in the engine layer, consuming from internal NATS streams.

```
External Data → NATS (external) → Ingestion Layer → NATS (internal)
                                                          ↓
                                                    ┌─────────────┐
                                                    │ DAG Engine  │
                                                    │ (Indicators)│
                                                    └─────────────┘
                                                          ↓
                                        ┌─────────────────┴─────────────────┐
                                        ↓                                   ↓
                                 ┌──────────────┐                  ┌─────────────┐
                                 │ DB Sink      │                  │ Publishers  │
                                 │ (TimescaleDB)│                  │ (External)  │
                                 └──────────────┘                  └─────────────┘
```

### Repository Location

```
dataflow/
├── ingestion/
│   ├── ninjatrader/          # Your existing FastAPI receiver
│   ├── ib_gateway/
│   └── nats_publisher/       # Pushes to external NATS
│
├── persistence/              # ← NEW: TimescaleDB sink
│   ├── sink_service/
│   │   ├── main.py          # NATS consumer → TimescaleDB writer
│   │   ├── schema.sql       # Hypertable definitions
│   │   ├── migrations/
│   │   └── config.yaml
│   │
│   ├── queries/             # Common query patterns
│   └── models/              # ORM models (SQLAlchemy)
│
└── candle_aggregation/      # 1m → 5m → 15m aggregator
```

### TimescaleDB Schema

```sql
-- Raw ticks (hypertable)
CREATE TABLE ticks (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    price       NUMERIC(12,4),
    volume      NUMERIC(12,2),
    bid         NUMERIC(12,4),
    ask         NUMERIC(12,4)
);
SELECT create_hypertable('ticks', 'time');

-- OHLCV candles (hypertable)
CREATE TABLE candles (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    timeframe   TEXT NOT NULL,  -- '1m', '5m', '15m', etc.
    open        NUMERIC(12,4),
    high        NUMERIC(12,4),
    low         NUMERIC(12,4),
    close       NUMERIC(12,4),
    volume      NUMERIC(12,2),
    UNIQUE(symbol, timeframe, time)
);
SELECT create_hypertable('candles', 'time');

-- Market structure events
CREATE TABLE market_structure (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    timeframe   TEXT NOT NULL,
    type        TEXT NOT NULL,  -- 'swing_point', 'fvg', 'order_block'
    data        JSONB NOT NULL  -- Type-specific payload
);
SELECT create_hypertable('market_structure', 'time');

-- Indicator outputs
CREATE TABLE indicators (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    indicator_id TEXT NOT NULL,
    timeframe   TEXT NOT NULL,
    value       JSONB NOT NULL
);
SELECT create_hypertable('indicators', 'time');

-- Strategy signals
CREATE TABLE strategy_signals (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    strategy_id TEXT NOT NULL,
    signal_type TEXT NOT NULL,  -- 'entry', 'exit', 'stop'
    data        JSONB NOT NULL
);
SELECT create_hypertable('strategy_signals', 'time');
```

---

## 5. Repository Structure (Detailed)

```
trading-engine/                      # Monorepo root
│
├── types/                           # ← Typed message catalog
│   ├── __init__.py
│   ├── market_data.py
│   ├── market_structure.py
│   ├── volume_analysis.py
│   ├── indicators.py
│   ├── strategy_signals.py
│   └── schemas/                     # JSON schemas for validation
│       ├── tick.schema.json
│       ├── candle.schema.json
│       └── ...
│
├── engine/                          # Core DAG runtime
│   ├── dag/
│   │   ├── node.py                  # Base node interface
│   │   ├── graph.py                 # DAG construction
│   │   └── executor.py              # Topological execution
│   ├── scheduler/
│   │   ├── event_router.py          # Event → impacted nodes
│   │   └── coordinator.py           # Main execution loop
│   ├── state/
│   │   ├── manager.py               # Per-node state persistence
│   │   └── snapshot.py              # State serialization
│   └── runtime/
│       ├── symbol_executor.py       # Per-symbol DAG runner
│       └── config_loader.py         # Load pipelines from YAML
│
├── indicators/                      # Indicator implementations
│   ├── base.py                      # BaseIndicator class
│   ├── moving_average/
│   │   ├── __init__.py
│   │   ├── sma.py
│   │   ├── ema.py
│   │   └── wma.py
│   ├── vwap/
│   │   └── vwap.py
│   ├── volume/
│   │   ├── delta.py
│   │   ├── footprint.py
│   │   └── profile.py
│   ├── market_structure/           # ← Technical primitives
│   │   ├── swing_points.py
│   │   ├── fvg_detector.py
│   │   ├── order_blocks.py
│   │   └── liquidity.py
│   └── ... (many more)
│
├── strategies/                      # Strategy nodes
│   ├── base.py                      # BaseStrategy class
│   ├── breakout/
│   │   └── liquidity_breakout.py
│   ├── mean_reversion/
│   │   └── structure_reversion.py
│   └── confluence/
│       └── multi_tf_confluence.py
│
├── dataflow/                        # Event I/O layer
│   ├── ingestion/
│   │   ├── ninjatrader/
│   │   │   ├── DataFeederIndicator.cs
│   │   │   └── backend/             # Your FastAPI service
│   │   │       ├── main.py
│   │   │       └── requirements.txt
│   │   ├── ib_gateway/
│   │   └── nats_publisher/
│   │       └── publisher.py         # External NATS writer
│   │
│   ├── persistence/                 # ← TimescaleDB sink
│   │   ├── sink_service/
│   │   │   ├── main.py
│   │   │   ├── config.yaml
│   │   │   ├── schema.sql
│   │   │   └── models.py
│   │   └── queries/
│   │
│   ├── candle_aggregation/
│   │   ├── aggregator_1m.py
│   │   ├── aggregator_5m.py
│   │   └── config.yaml
│   │
│   ├── adapters/
│   │   ├── nats_internal.py         # Internal NATS client
│   │   ├── nats_external.py         # External NATS client
│   │   └── websocket.py
│   │
│   └── publishers/
│       ├── indicator_publisher.py
│       ├── strategy_publisher.py
│       └── dashboard_stream.py
│
├── config/                          # Declarative pipeline defs
│   ├── types_registry.yaml          # Message type catalog
│   ├── indicators.yaml              # Indicator node defs
│   ├── strategies.yaml              # Strategy node defs
│   └── pipelines/
│       ├── es_futures.yaml          # Symbol-specific DAG
│       ├── nq_futures.yaml
│       └── template.yaml
│
├── infra/                           # K3s deployment (optional)
│   ├── helm/
│   │   ├── trading-engine/
│   │   ├── nats/
│   │   └── timescaledb/
│   ├── k8s/
│   │   ├── engine-executor.yaml
│   │   ├── db-sink.yaml
│   │   └── ingestion.yaml
│   └── kustomize/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── replay/                      # Deterministic replay tests
│   │   ├── datasets/
│   │   └── replay_runner.py
│   └── e2e/
│
├── tools/
│   ├── dagviz/                      # Visualize DAG graphs
│   ├── type_codegen/                # Generate type stubs
│   └── nats_monitor/                # Debug NATS streams
│
├── docs/
│   ├── architecture.md
│   ├── message_catalog.md
│   └── deployment.md
│
└── README.md                        # This file
```

---

## 6. K3s Deployment Model

### Services

```yaml
# Per-symbol DAG executor
Deployment: engine-executor-es
  - Runs all indicators + strategies for ES
  - Consumes: candles.internal.ES.*
  - Publishes: indicators.internal.ES.*, strategies.signals.ES

# Candle aggregator
Deployment: candle-aggregator
  - Consumes: ticks.raw.*
  - Publishes: candles.internal.*.1m, candles.internal.*.5m, etc.

# DB sink
Deployment: db-sink
  - Consumes: ticks.raw.*, candles.internal.*, indicators.internal.*, strategies.signals.*
  - Writes to: TimescaleDB

# Ingestion gateway
Deployment: ingestion-gateway
  - Receives: HTTP from NinjaTrader
  - Publishes: ticks.raw.*

# External publishers
Deployment: external-publisher
  - Consumes: indicators.internal.*, strategies.signals.*
  - Publishes: indicators.public.*, strategies.signals.* (external NATS)

# Infrastructure
StatefulSet: nats
StatefulSet: timescaledb
```

### Scaling Strategy

**Scale by symbol, not by component.**

Each `engine-executor` pod runs the full DAG for one symbol (or small group). This ensures:
- Local state (no cross-service latency)
- Strict ordering per symbol
- No distributed coordination overhead
- Simple failure isolation

---

## 7. Data Flow Summary

```
NinjaTrader
    ↓ HTTP POST
ingestion-gateway
    ↓ NATS: ticks.raw.ES
candle-aggregator
    ↓ NATS: candles.internal.ES.1m, candles.internal.ES.5m
engine-executor-ES
    ↓ (indicators compute in DAG order)
    ├─→ NATS: indicators.internal.ES.*
    └─→ NATS: strategies.signals.ES
        ↓
    ┌───┴─────────────────────┐
    ↓                         ↓
db-sink                  external-publisher
    ↓                         ↓
TimescaleDB          indicators.public.ES.*
                     (dashboards, alerts)
```

---

## 8. Key Design Decisions

### Why Typed Messages?
- Type safety across language boundaries
- Self-documenting event contracts
- Easy validation and versioning
- Enables code generation (TypeScript, Rust, etc.)

### Why Two NATS Layers?
- **Stability**: External API never breaks
- **Performance**: Internal can optimize without compatibility concerns
- **Security**: Internal topics not exposed externally

### Why TimescaleDB?
- Native time-series optimizations
- SQL interface for analytics
- Compression and retention policies
- Easy integration with Grafana/BI tools

### Why Per-Symbol Executors?
- Eliminates distributed state
- Minimizes latency
- Simplifies debugging
- Matches HFT best practices

