"""
TimescaleDB Sink Service

Consumes market data from NATS and persists to TimescaleDB.
Subscribes to:
- ticks.raw.*         -> ticks table
- candles.*.*         -> candles table

This is a dedicated microservice in the Engine layer that provides
durable storage for all market data flowing through the system.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Optional

import asyncpg

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dataflow.adapters.nats_client import NatsClient, NatsConfig, Topics
from schemas.market_data import Tick, Candle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class TimescaleDBSink:
    """
    Persists market data from NATS to TimescaleDB.

    Features:
    - Batch inserts for efficiency
    - Automatic reconnection
    - Graceful shutdown with pending flush
    """

    def __init__(
        self,
        nats_client: NatsClient,
        db_url: str,
        batch_size: int = 100,
        flush_interval: float = 1.0,
    ):
        self.nats = nats_client
        self.db_url = db_url
        self.batch_size = batch_size
        self.flush_interval = flush_interval

        self._pool: Optional[asyncpg.Pool] = None
        self._tick_buffer: list[Tick] = []
        self._candle_buffer: list[Candle] = []
        self._flush_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # Metrics
        self._ticks_written = 0
        self._candles_written = 0

    async def connect_db(self) -> None:
        """Connect to TimescaleDB"""
        logger.info(f"Connecting to TimescaleDB...")

        self._pool = await asyncpg.create_pool(
            self.db_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )

        logger.info("Connected to TimescaleDB")

    async def close_db(self) -> None:
        """Close database connection"""
        if self._pool:
            await self._pool.close()
            logger.info("TimescaleDB connection closed")

    async def _handle_tick(self, msg) -> None:
        """Handle incoming tick message"""
        try:
            tick = Tick.from_json(msg.data.decode())
        except Exception as e:
            logger.error(f"Failed to parse tick: {e}")
            return

        async with self._lock:
            self._tick_buffer.append(tick)

            if len(self._tick_buffer) >= self.batch_size:
                await self._flush_ticks()

    async def _handle_candle(self, msg) -> None:
        """Handle incoming candle message"""
        try:
            candle = Candle.from_json(msg.data.decode())
        except Exception as e:
            logger.error(f"Failed to parse candle: {e}")
            return

        async with self._lock:
            self._candle_buffer.append(candle)

            if len(self._candle_buffer) >= self.batch_size:
                await self._flush_candles()

    async def _flush_ticks(self) -> None:
        """Flush tick buffer to database"""
        if not self._tick_buffer:
            return

        ticks = self._tick_buffer
        self._tick_buffer = []

        try:
            async with self._pool.acquire() as conn:
                # Batch insert using COPY for efficiency
                await conn.executemany(
                    """
                    INSERT INTO ticks (time, symbol, price, volume, bid, ask)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    [
                        (
                            tick.timestamp,
                            tick.symbol,
                            tick.price,
                            tick.volume,
                            tick.bid,
                            tick.ask,
                        )
                        for tick in ticks
                    ],
                )

            self._ticks_written += len(ticks)
            logger.debug(f"Flushed {len(ticks)} ticks (total: {self._ticks_written})")

        except Exception as e:
            logger.error(f"Failed to flush ticks: {e}")
            # Re-add to buffer for retry
            async with self._lock:
                self._tick_buffer = ticks + self._tick_buffer

    async def _flush_candles(self) -> None:
        """Flush candle buffer to database"""
        if not self._candle_buffer:
            return

        candles = self._candle_buffer
        self._candle_buffer = []

        try:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO candles (time, symbol, timeframe, open, high, low, close, volume, tick_count)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (symbol, timeframe, time) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        tick_count = EXCLUDED.tick_count
                    """,
                    [
                        (
                            candle.timestamp,
                            candle.symbol,
                            candle.timeframe,
                            candle.open,
                            candle.high,
                            candle.low,
                            candle.close,
                            candle.volume,
                            candle.tick_count,
                        )
                        for candle in candles
                    ],
                )

            self._candles_written += len(candles)
            logger.debug(f"Flushed {len(candles)} candles (total: {self._candles_written})")

        except Exception as e:
            logger.error(f"Failed to flush candles: {e}")
            async with self._lock:
                self._candle_buffer = candles + self._candle_buffer

    async def _periodic_flush(self) -> None:
        """Periodically flush buffers"""
        while True:
            await asyncio.sleep(self.flush_interval)

            async with self._lock:
                if self._tick_buffer:
                    await self._flush_ticks()
                if self._candle_buffer:
                    await self._flush_candles()

    async def start(self) -> None:
        """Start the sink service"""
        logger.info("Starting TimescaleDB sink...")

        # Connect to database
        await self.connect_db()

        # Subscribe to NATS topics
        await self.nats.subscribe(Topics.all_ticks(), self._handle_tick, queue="db-sink")
        await self.nats.subscribe(Topics.all_candles(), self._handle_candle, queue="db-sink")

        # Start periodic flush task
        self._flush_task = asyncio.create_task(self._periodic_flush())

        logger.info("TimescaleDB sink started")

    async def stop(self) -> None:
        """Stop the sink service"""
        logger.info("Stopping TimescaleDB sink...")

        # Cancel periodic flush
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        async with self._lock:
            await self._flush_ticks()
            await self._flush_candles()

        # Close database
        await self.close_db()

        logger.info(
            f"TimescaleDB sink stopped. "
            f"Total written: {self._ticks_written} ticks, {self._candles_written} candles"
        )


async def main():
    """Main entry point"""
    # Configuration from environment
    nats_config = NatsConfig.from_env()
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/trading"
    )
    batch_size = int(os.getenv("BATCH_SIZE", "100"))
    flush_interval = float(os.getenv("FLUSH_INTERVAL", "1.0"))

    nats_client = NatsClient(nats_config)
    sink = TimescaleDBSink(
        nats_client,
        db_url,
        batch_size=batch_size,
        flush_interval=flush_interval,
    )

    try:
        await nats_client.connect()
        await sink.start()

        logger.info("TimescaleDB sink running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(10)
            # Log periodic stats
            logger.info(
                f"Stats: {sink._ticks_written} ticks, {sink._candles_written} candles written"
            )

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await sink.stop()
        await nats_client.close()


if __name__ == "__main__":
    asyncio.run(main())
