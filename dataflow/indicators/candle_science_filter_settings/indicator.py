"""
Filter Settings Indicator Service

Real-time indicator that calculates direction and position filters from candle patterns.
Subscribes to candle data via NATS, maintains a rolling buffer, and publishes filter results.
"""

import asyncio
import json
import logging
import os
import sys
from collections import deque
from datetime import datetime
from typing import Optional, Dict, List

import asyncpg

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from dataflow.adapters.nats_client import NatsClient, NatsConfig, Topics
from schemas.market_data import Candle
from schemas.indicator_data import FilterSettings
from dataflow.indicators.candle_science_filter_settings.filters import CandleScienceFilterCalculator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class CandleScienceFilterSettingsIndicator:
    """
    Filter Settings Indicator Service.

    Processes candle data to calculate direction and position filters.
    One instance per symbol/timeframe pair.

    Architecture:
    - Subscribes to: candles.{symbol}.{timeframe}
    - Publishes to: indicators.{symbol}.filter-settings
    - Stores to: indicators table (indicator_id='filter-settings')
    - Buffer: Circular deque of N candles
    """

    def __init__(
        self,
        nats_client: NatsClient,
        db_pool: asyncpg.Pool,
        symbol: str,
        timeframe: str,
        buffer_size: int = 3
    ):
        """
        Initialize filter settings indicator.

        Args:
            nats_client: Connected NATS client
            db_pool: AsyncPG connection pool
            symbol: Trading symbol (e.g., 'ES', 'NQ')
            timeframe: Candle timeframe (e.g., '1m', '5m', '15m')
            buffer_size: Number of candles to maintain (N)
        """
        self.nats = nats_client
        self.pool = db_pool
        self.symbol = symbol
        self.timeframe = timeframe
        self.buffer_size = buffer_size

        # Circular buffer for candles (FIFO)
        self._candle_buffer: deque[Candle] = deque(maxlen=buffer_size)
        self._buffer_filled = False
        self._lock = asyncio.Lock()

        # Metrics
        self._filters_published = 0

        logger.info(
            f"Initialized FilterSettingsIndicator for {symbol}/{timeframe} "
            f"with buffer_size={buffer_size}"
        )

    async def _fill_buffer_from_db(self) -> None:
        """
        Fill buffer from database on startup.

        Loads the most recent N candles from TimescaleDB.
        If fewer than N candles exist, buffer remains partially filled.
        """
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT time, symbol, timeframe, open, high, low, close, volume, tick_count
                    FROM candles
                    WHERE symbol = $1 AND timeframe = $2
                    ORDER BY time DESC
                    LIMIT $3
                    """,
                    self.symbol,
                    self.timeframe,
                    self.buffer_size
                )

            if not rows:
                logger.info(f"No historical candles found for {self.symbol}/{self.timeframe}")
                return

            # Reverse to get chronological order (oldest first)
            for row in reversed(rows):
                candle = Candle(
                    symbol=row['symbol'],
                    timestamp=row['time'],
                    timeframe=row['timeframe'],
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row['volume']),
                    tick_count=row['tick_count']
                )
                self._candle_buffer.append(candle)

            logger.info(
                f"Loaded {len(self._candle_buffer)} historical candles "
                f"for {self.symbol}/{self.timeframe}"
            )

            # If buffer is full, calculate and publish immediately
            if len(self._candle_buffer) == self.buffer_size:
                self._buffer_filled = True
                filters = await self._calculate_filters(list(self._candle_buffer))
                if filters:
                    latest_candle = self._candle_buffer[-1]
                    await self._publish_filters(filters, latest_candle.timestamp)
                    await self._store_filters(filters, latest_candle.timestamp)
                    logger.info(f"Published initial filters for {self.symbol}/{self.timeframe}")

        except Exception as e:
            logger.error(f"Failed to fill buffer from DB: {e}")
            # Continue without historical data - will fill from live candles

    async def _handle_candle(self, msg) -> None:
        """
        Handle incoming candle from NATS.

        1. Parse candle from JSON
        2. Add to circular buffer
        3. If buffer full, calculate and publish filters
        """
        try:
            candle = Candle.from_json(msg.data.decode())

            # Verify this candle matches our subscription
            if candle.symbol != self.symbol or candle.timeframe != self.timeframe:
                logger.warning(
                    f"Received mismatched candle: {candle.symbol}/{candle.timeframe} "
                    f"(expected {self.symbol}/{self.timeframe})"
                )
                return

            logger.debug(
                f"Received candle: {candle.symbol}/{candle.timeframe} "
                f"@ {candle.timestamp} C={candle.close:.2f}"
            )

        except Exception as e:
            logger.error(f"Failed to parse candle: {e}")
            return

        async with self._lock:
            # Add to buffer (oldest will auto-evict if full)
            self._candle_buffer.append(candle)

            # Check if buffer just became full
            if len(self._candle_buffer) == self.buffer_size:
                if not self._buffer_filled:
                    logger.info(
                        f"Buffer filled for {self.symbol}/{self.timeframe} "
                        f"({len(self._candle_buffer)} candles)"
                    )
                    self._buffer_filled = True

            # Only calculate if buffer is full
            if not self._buffer_filled:
                logger.debug(
                    f"Buffer not yet full: {len(self._candle_buffer)}/{self.buffer_size}"
                )
                return

        # Calculate filters (outside lock for performance)
        filters = await self._calculate_filters(list(self._candle_buffer))

        if filters:
            # Publish and store
            await self._publish_filters(filters, candle.timestamp)
            await self._store_filters(filters, candle.timestamp)

    async def _calculate_filters(
        self, candles: List[Candle]
    ) -> Optional[Dict[str, str]]:
        """
        Calculate all filters from candle buffer.

        Args:
            candles: List of candles (length = buffer_size)

        Returns:
            Dictionary of filter key-value pairs, or None if insufficient data
        """
        try:
            # Use FilterCalculator to build filters
            filters = CandleScienceFilterCalculator.build_all_filters(candles)

            if filters:
                logger.debug(
                    f"Calculated {len(filters)} filters for {self.symbol}/{self.timeframe}"
                )

            return filters

        except Exception as e:
            logger.error(f"Failed to calculate filters: {e}")
            return None

    async def _publish_filters(
        self, filters: Dict[str, str], timestamp: datetime
    ) -> None:
        """
        Publish filter settings to NATS.

        Args:
            filters: Calculated filter dictionary
            timestamp: Timestamp of the latest candle
        """
        try:
            filter_settings = FilterSettings(
                symbol=self.symbol,
                timestamp=timestamp,
                timeframe=self.timeframe,
                filters=filters
            )

            topic = Topics.indicators(self.symbol, "filter-settings")
            await self.nats.publish_json(topic, filter_settings.to_json())

            self._filters_published += 1

            logger.info(
                f"Published filter settings for {self.symbol}/{self.timeframe} "
                f"@ {timestamp}: {len(filters)} filters"
            )

        except Exception as e:
            logger.error(f"Failed to publish filters: {e}")

    async def _store_filters(
        self, filters: Dict[str, str], timestamp: datetime
    ) -> None:
        """
        Store filter settings to TimescaleDB.

        Args:
            filters: Calculated filter dictionary
            timestamp: Timestamp of the latest candle
        """
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO indicators (time, symbol, indicator_id, timeframe, value)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (symbol, indicator_id, timeframe, time)
                    DO UPDATE SET value = EXCLUDED.value
                    """,
                    timestamp,
                    self.symbol,
                    "filter-settings",
                    self.timeframe,
                    json.dumps(filters)  # Convert dict to JSON string
                )

            logger.debug(f"Stored filters to database for {self.symbol}/{self.timeframe}")

        except Exception as e:
            logger.error(f"Failed to store filters to DB: {e}")

    async def start(self) -> None:
        """
        Start the indicator service.

        1. Fill buffer from database
        2. Subscribe to candle topic
        """
        logger.info(f"Starting FilterSettingsIndicator for {self.symbol}/{self.timeframe}")

        # Fill buffer from historical data
        await self._fill_buffer_from_db()

        # Subscribe to candle updates
        topic = Topics.candles(self.symbol, self.timeframe)
        # Sanitize symbol for queue name (NATS doesn't allow spaces)
        sanitized_symbol = self.symbol.replace(" ", "_")
        await self.nats.subscribe(
            topic,
            self._handle_candle,
            queue=f"filter-settings-{sanitized_symbol}-{self.timeframe}"
        )

        logger.info(
            f"FilterSettingsIndicator started for {self.symbol}/{self.timeframe}. "
            f"Buffer: {len(self._candle_buffer)}/{self.buffer_size}"
        )

    async def stop(self) -> None:
        """Stop the indicator service."""
        logger.info(
            f"Stopping FilterSettingsIndicator for {self.symbol}/{self.timeframe}. "
            f"Total published: {self._filters_published}"
        )
        # NATS client handles unsubscribe on disconnect


async def main():
    """
    Main entry point for filter settings indicator service.

    Supports multiple symbol/timeframe pairs via environment variables.
    """
    # Configuration from environment
    nats_config = NatsConfig.from_env()
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/trading"
    )

    # Parse symbol/timeframe pairs
    # Format: SYMBOL1:TIMEFRAME1,SYMBOL2:TIMEFRAME2
    # Example: ES:5m,NQ:5m,ES:15m
    pairs_str = os.getenv("INDICATOR_PAIRS", "ES:5m")
    buffer_size = int(os.getenv("BUFFER_SIZE", "3"))

    pairs = []
    for pair in pairs_str.split(","):
        parts = pair.strip().split(":")
        if len(parts) != 2:
            logger.error(f"Invalid pair format: {pair}. Expected SYMBOL:TIMEFRAME")
            continue
        pairs.append((parts[0], parts[1]))

    if not pairs:
        logger.error("No valid symbol/timeframe pairs configured")
        return

    # Create NATS client and DB pool
    nats_client = NatsClient(nats_config)
    db_pool = await asyncpg.create_pool(
        db_url,
        min_size=2,
        max_size=10,
        command_timeout=60
    )

    # Create indicator instances for each pair
    indicators = []
    for symbol, timeframe in pairs:
        indicator = CandleScienceFilterSettingsIndicator(
            nats_client=nats_client,
            db_pool=db_pool,
            symbol=symbol,
            timeframe=timeframe,
            buffer_size=buffer_size
        )
        indicators.append(indicator)

    try:
        # Connect NATS
        await nats_client.connect()

        # Start all indicators
        for indicator in indicators:
            await indicator.start()

        logger.info(
            f"Filter settings indicator running for {len(indicators)} pairs. "
            f"Press Ctrl+C to stop."
        )

        # Keep running
        while True:
            await asyncio.sleep(10)
            # Log periodic stats
            for indicator in indicators:
                logger.info(
                    f"Stats [{indicator.symbol}/{indicator.timeframe}]: "
                    f"{indicator._filters_published} filters published"
                )

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        # Stop all indicators
        for indicator in indicators:
            await indicator.stop()

        # Cleanup
        await nats_client.close()
        await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())
