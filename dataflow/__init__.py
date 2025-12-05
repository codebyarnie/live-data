"""
Dataflow Layer

Event I/O layer for the trading engine. Contains:
- ingestion: External data sources (NinjaTrader, IB, etc.)
- persistence: TimescaleDB sink
- candle_aggregation: Tick to candle aggregation
- adapters: NATS client adapters
"""
