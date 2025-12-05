# Trading Engine Architecture and Repository Structure

This repository contains the complete event-driven trading engine, including the multi-timeframe DAG computation model, indicators, strategies, dataflow components, and deployment configuration for K3s.

The design supports:

* Deterministic, event-driven indicator computation
* Cross-timeframe and cross-indicator dependencies
* High-performance DAG execution per symbol
* NATS-based ingestion and publication
* Clean scaling and predictable operational behavior

---

## 1. Core Concept

The system implements a **Directed Acyclic Graph (DAG)** of computation nodes. Each node represents:

* An indicator
* A strategy component
* A TF candle stream
* A transformation in the price-action pipeline

Nodes may depend on:

* Tick events
* Candle events of any timeframe
* Outputs from other indicators (any TF)
* Mixed inputs (ticks + candles + indicators)

When an event arrives, the system:

1. Identifies all impacted nodes
2. Executes them *once* in topological order
3. Emits outputs (indicators, strategy signals, dashboard streams)

This guarantees deterministic behavior, prevents race conditions, and supports complex dependency graphs.

---

## 2. Node Model

Each indicator or strategy node follows a uniform definition:

```
id: string
inputs: [Tick | Candle(TF) | Indicator(ID)]
state: persistent dict
compute(state, inputs) → output
output_schema: arbitrary
```

Inputs may include outputs from other indicators. This allows arbitrary fan-in and fan-out patterns.

---

## 3. Repository Structure (Monorepo)

This repo follows a hybrid monorepo pattern. All domain logic and the complete trading engine live in one repository. Infrastructure, dashboards, and DevOps tooling live in separate repos.

```
repo-root/
│
├── engine/                         # Core DAG engine
│   ├── dag/
│   ├── scheduler/
│   ├── state/
│   └── runtime/
│
├── indicators/                     # Indicator implementations
│   ├── moving_average/
│   ├── vwap/
│   ├── imbalance/
│   └── ...
│
├── strategies/                     # Strategy components
│   ├── breakout/
│   ├── mean_reversion/
│   └── liquidity_hunt/
│
├── dataflow/                       # Event producers and consumers
│   ├── ingestion/                  # tick → NATS
│   ├── candle_aggregation/         # 1m → 5m → 15m → ...
│   ├── adapters/                   # NATS in/out, WebSockets
│   └── publishers/
│
├── config/                         # Declarative pipeline definitions
│   ├── indicators.yaml
│   ├── strategies.yaml
│   └── pipelines/
│       └── symbol_template.yaml
│
├── infra/                          # K3s manifests and Helm (optional)
│   ├── helm/
│   ├── k8s/
│   └── kustomize/
│
├── tests/                          # Unit, integration, replay tests
│   ├── replay/
│   ├── fuzz/
│   └── e2e/
│
└── tools/                          # Dev tools, graph visualization
    └── dagviz/
```

---

## 4. K3s Deployment Model

You scale by **symbol**, not by indicator or strategy.

### Recommended Components:

* `tick-collector`
* `candle-aggregator`
* `engine-executor` (one per symbol or symbol-group)
* `dashboard-streamer`
* `nats`

The `engine-executor` contains the DAG engine and runs all indicators and strategies for that symbol. This avoids inter-service latency, keeps state local, and ensures strict ordering.

---

## 5. Multi-Timeframe and Cross-Indicator Dependencies

The system naturally supports complex dependencies such as:

```
IndicatorA → IndicatorB → Strategy1
         ↘            ↘
          ↘→ IndicatorC → IndicatorD → Strategy2
```

Because topological ordering is enforced and nodes compute exactly once per event, these patterns do not introduce complexity.

---

## 6. Event Routing and Execution Flow

1. External event arrives (Tick or Candle(TF))
2. Coordinator marks impacted nodes
3. Coordinator filters the global topological order
4. Each node:

   * Fetches latest inputs
   * Calls `compute()`
   * Updates its state
5. Outputs are published to:

   * Indicators stream
   * Strategies stream
   * Dashboard feeds

---

## 7. Recommended Repo Separation (3 Repos Total)

Although this repo holds all trading-engine logic, the full system is expected to use:

**Repo 1 — trading-engine (this repository)**

* Indicators
* Strategies
* Engine runtime
* Data ingestion
* TF aggregation
* NATS adapters

**Repo 2 — infra**

* K3s manifests
* Helm charts
* Prometheus/Grafana
* Logging (Loki/Promtail)
* Secrets, ingress, certificates

**Repo 3 — dashboard**

* Web dashboards
* WebSocket clients
* Analytics/UI

This separation keeps deployment concerns and UI development decoupled from engine evolution.

---

## 8. Next Steps

You can extend this README with:

* Build instructions
* Symbol configuration templates
* CI/CD pipelines
* Helm chart deployment guides
* Testing and deterministic replay instructions

If you need ready-made templates for Helm, CI/CD, or a full DAG engine skeleton, they can be added in this repository under `infra/` or `engine/` respectively.
