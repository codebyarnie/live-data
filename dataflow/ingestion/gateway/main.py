"""
Ingestion Gateway

FastAPI service that receives market data from NinjaTrader (or other sources)
and publishes to NATS for downstream processing.

HTTP Endpoints:
- POST /data     - Receive market data and publish as tick
- POST /candle   - Receive pre-aggregated candle
- GET  /         - Health check
- GET  /health   - Detailed health status
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from dataflow.adapters.nats_client import NatsClient, NatsConfig, Topics
from types.market_data import Tick, Candle

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# Request models (Pydantic)
class MarketDataRequest(BaseModel):
    """Market data received from NinjaTrader"""
    symbol: str
    timestamp: str
    price: float
    volume: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    # OHLC for candle data
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None


class CandleRequest(BaseModel):
    """Pre-aggregated candle data"""
    symbol: str
    timestamp: str
    timeframe: str  # '1m', '5m', etc.
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


# Global NATS client
nats_client: Optional[NatsClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for NATS connection"""
    global nats_client

    # Startup
    logger.info("Starting Ingestion Gateway...")

    nats_config = NatsConfig.from_env()
    nats_client = NatsClient(nats_config)

    try:
        await nats_client.connect()
        logger.info("NATS connection established")
    except Exception as e:
        logger.warning(f"Failed to connect to NATS: {e}. Running in standalone mode.")
        nats_client = None

    yield

    # Shutdown
    if nats_client:
        await nats_client.close()
    logger.info("Ingestion Gateway shutdown complete")


app = FastAPI(
    title="Trading Engine - Ingestion Gateway",
    description="Receives market data from external sources and publishes to NATS",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "ingestion-gateway",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health():
    """Detailed health status"""
    return {
        "status": "healthy",
        "service": "ingestion-gateway",
        "nats_connected": nats_client.is_connected if nats_client else False,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/data")
async def receive_data(data: MarketDataRequest):
    """
    Receive market data from NinjaTrader and publish as tick to NATS.

    This is the main ingestion endpoint. Data received here is:
    1. Validated
    2. Converted to Tick format
    3. Published to NATS topic: ticks.raw.{symbol}
    """
    try:
        # Parse timestamp
        timestamp = datetime.fromisoformat(data.timestamp.replace("Z", "+00:00"))
    except ValueError:
        # Try parsing common formats
        try:
            timestamp = datetime.strptime(data.timestamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            timestamp = datetime.now()

    # Create Tick object
    tick = Tick(
        symbol=data.symbol,
        timestamp=timestamp,
        price=data.price,
        volume=data.volume,
        bid=data.bid,
        ask=data.ask,
    )

    # Log received data
    logger.info(
        f"Received tick: {tick.symbol} @ ${tick.price:.2f}"
        + (f" vol={tick.volume}" if tick.volume else "")
    )

    # Publish to NATS
    if nats_client and nats_client.is_connected:
        topic = Topics.ticks_raw(data.symbol)
        await nats_client.publish_json(topic, tick.to_json())
        logger.debug(f"Published to {topic}")
    else:
        logger.debug("NATS not connected - tick logged only")

    return {
        "status": "success",
        "message": "Tick received and published",
        "topic": Topics.ticks_raw(data.symbol) if nats_client else None,
        "received_at": datetime.now().isoformat(),
    }


@app.post("/candle")
async def receive_candle(data: CandleRequest):
    """
    Receive pre-aggregated candle from external source.

    Useful when the source (e.g., NinjaTrader) provides completed candles.
    Published to NATS topic: candles.{symbol}.{timeframe}
    """
    try:
        timestamp = datetime.fromisoformat(data.timestamp.replace("Z", "+00:00"))
    except ValueError:
        try:
            timestamp = datetime.strptime(data.timestamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            timestamp = datetime.now()

    # Create Candle object
    candle = Candle(
        symbol=data.symbol,
        timestamp=timestamp,
        timeframe=data.timeframe,
        open=data.open,
        high=data.high,
        low=data.low,
        close=data.close,
        volume=data.volume,
    )

    logger.info(
        f"Received candle: {candle.symbol} {candle.timeframe} "
        f"O={candle.open:.2f} H={candle.high:.2f} L={candle.low:.2f} C={candle.close:.2f}"
    )

    # Publish to NATS
    if nats_client and nats_client.is_connected:
        topic = Topics.candles(data.symbol, data.timeframe)
        await nats_client.publish_json(topic, candle.to_json())
        logger.debug(f"Published to {topic}")

    return {
        "status": "success",
        "message": "Candle received and published",
        "topic": Topics.candles(data.symbol, data.timeframe) if nats_client else None,
        "received_at": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting Ingestion Gateway on {host}:{port}")
    logger.info(f"NATS servers: {os.getenv('NATS_SERVERS', 'nats://localhost:4222')}")

    uvicorn.run(app, host=host, port=port)
