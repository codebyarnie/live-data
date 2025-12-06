"""
Query API

FastAPI service for querying historical candle data from TimescaleDB.

HTTP Endpoints:
- GET  /              - Health check
- GET  /health        - Detailed health status
- GET  /candles/{symbol}/{timeframe}  - Fetch candles with limit parameter
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn
import asyncpg

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# Supported timeframes (in seconds)
TIMEFRAMES = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


# Response models (Pydantic)
class CandleResponse(BaseModel):
    """Single candle response"""
    symbol: str
    timestamp: str  # ISO 8601
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    tick_count: int


class CandlesResponse(BaseModel):
    """Response containing multiple candles"""
    symbol: str
    timeframe: str
    count: int
    candles: list[CandleResponse]


# Global database pool
db_pool: Optional[asyncpg.Pool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for database connection"""
    global db_pool

    # Startup
    logger.info("Starting Query API...")

    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/trading"
    )

    try:
        db_pool = await asyncpg.create_pool(
            db_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        logger.info("Database connection pool created")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        db_pool = None

    yield

    # Shutdown
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")
    logger.info("Query API shutdown complete")


app = FastAPI(
    title="Trading Engine - Query API",
    description="Query historical candle data",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "query-api",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health():
    """Detailed health status"""
    return {
        "status": "healthy",
        "service": "query-api",
        "database_connected": db_pool is not None,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/candles/{symbol}/{timeframe}")
async def get_candles(
    symbol: str,
    timeframe: str,
    limit: int = Query(default=100, ge=1, le=1000, description="Number of candles to fetch")
) -> CandlesResponse:
    """
    Fetch the last N candles for a symbol/timeframe.

    Args:
        symbol: Trading symbol (e.g., ES, NQ)
        timeframe: Candle timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)
        limit: Number of candles to fetch (1-1000, default 100)

    Returns:
        CandlesResponse with list of candles ordered by time descending (most recent first)

    Raises:
        400: Invalid timeframe
        404: No candles found
        503: Database unavailable
    """
    # Validate timeframe
    if timeframe not in TIMEFRAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timeframe '{timeframe}'. Must be one of: {list(TIMEFRAMES.keys())}"
        )

    # Normalize symbol to uppercase
    symbol = symbol.upper()

    # Check database connection
    if not db_pool:
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable"
        )

    # Query database
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT time, symbol, timeframe, open, high, low, close, volume, tick_count
                FROM candles
                WHERE symbol = $1 AND timeframe = $2
                ORDER BY time DESC
                LIMIT $3
                """,
                symbol,
                timeframe,
                limit
            )
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )

    # Handle empty result
    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No candles found for {symbol} {timeframe}"
        )

    # Convert rows to response model
    candles = [
        CandleResponse(
            symbol=row['symbol'],
            timestamp=row['time'].isoformat(),
            timeframe=row['timeframe'],
            open=float(row['open']),
            high=float(row['high']),
            low=float(row['low']),
            close=float(row['close']),
            volume=float(row['volume']),
            tick_count=row['tick_count']
        )
        for row in rows
    ]

    logger.info(f"Fetched {len(candles)} candles for {symbol} {timeframe} (limit={limit})")

    return CandlesResponse(
        symbol=symbol,
        timeframe=timeframe,
        count=len(candles),
        candles=candles
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8001"))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting Query API on {host}:{port}")
    logger.info(f"Database: {os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/trading')}")

    uvicorn.run(app, host=host, port=port)
