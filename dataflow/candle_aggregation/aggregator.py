"""
Candle Aggregator - FIXED VERSION

Key fix: Return completed candles when creating new builders
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dataflow.adapters.nats_client import NatsClient, NatsConfig, Topics
from schemas.market_data import Tick, Candle

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

TIMEFRAMES = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


class CandleBuilder:
    """Builds a candle from incoming ticks"""

    def __init__(self, symbol: str, timeframe: str, start_time: datetime):
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_time = start_time
        self.open: Optional[float] = None
        self.high: Optional[float] = None
        self.low: Optional[float] = None
        self.close: Optional[float] = None
        self.volume: float = 0.0
        self.tick_count: int = 0

    def add_tick(self, tick: Tick) -> None:
        """Add a tick to this candle"""
        price = tick.price
        volume = tick.volume or 0.0

        if self.open is None:
            self.open = price
            self.high = price
            self.low = price

        self.high = max(self.high, price)
        self.low = min(self.low, price)
        self.close = price
        self.volume += volume
        self.tick_count += 1

    def is_empty(self) -> bool:
        """Check if candle has any data"""
        return self.open is None

    def build(self) -> Candle:
        """Build the final Candle object"""
        if self.is_empty():
            raise ValueError("Cannot build empty candle")

        return Candle(
            symbol=self.symbol,
            timestamp=self.start_time,
            timeframe=self.timeframe,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
            tick_count=self.tick_count,
        )


class CandleAggregator:
    """Aggregates ticks into candles for multiple symbols and timeframes"""

    def __init__(self, nats_client: NatsClient, timeframes: list[str] = None):
        self.nats = nats_client
        self.timeframes = timeframes or ["1m", "5m", "15m"]
        self._builders: Dict[str, Dict[str, CandleBuilder]] = defaultdict(dict)
        self._lock = asyncio.Lock()
        self._check_task: Optional[asyncio.Task] = None

    def _get_candle_start(self, timestamp: datetime, timeframe: str) -> datetime:
        """Get the start time for a candle containing this timestamp"""
        seconds = TIMEFRAMES[timeframe]
        epoch = timestamp.timestamp()
        aligned = (epoch // seconds) * seconds
        return datetime.fromtimestamp(aligned, tz=timestamp.tzinfo)

    def _get_or_create_builder(
        self, symbol: str, timeframe: str, timestamp: datetime
    ) -> Tuple[CandleBuilder, Optional[CandleBuilder]]:
        """
        Get existing builder or create new one.
        Returns (current_builder, completed_builder_to_publish).
        """
        candle_start = self._get_candle_start(timestamp, timeframe)

        # First time for this symbol/timeframe
        if timeframe not in self._builders[symbol]:
            builder = CandleBuilder(symbol, timeframe, candle_start)
            self._builders[symbol][timeframe] = builder
            return builder, None

        existing = self._builders[symbol][timeframe]

        # Check if we need a new candle
        if existing.start_time != candle_start:
            # Time has moved to a new candle period
            # Save the old one for publishing
            completed = existing if not existing.is_empty() else None

            # Create new builder
            new_builder = CandleBuilder(symbol, timeframe, candle_start)
            self._builders[symbol][timeframe] = new_builder

            return new_builder, completed

        return existing, None

    async def _handle_tick(self, msg) -> None:
        """Handle incoming tick message"""
        try:
            tick = Tick.from_json(msg.data.decode())
            logger.debug(f"Received tick: {tick.symbol} @ {tick.price}")
        except Exception as e:
            logger.error(f"Failed to parse tick: {e}")
            return

        candles_to_publish = []

        async with self._lock:
            for timeframe in self.timeframes:
                builder, completed = self._get_or_create_builder(
                    tick.symbol, timeframe, tick.timestamp
                )

                # If we completed a candle, queue it for publishing
                if completed is not None:
                    candles_to_publish.append(completed.build())

                # Add tick to current builder
                builder.add_tick(tick)

        # Publish completed candles outside the lock
        for candle in candles_to_publish:
            await self._publish_candle(candle)

    async def _check_and_publish_candles(self) -> None:
        """Periodically check and publish completed candles (backup mechanism)"""
        while True:
            await asyncio.sleep(1)

            now = datetime.now()
            candles_to_publish = []

            async with self._lock:
                for symbol, timeframe_builders in list(self._builders.items()):
                    for timeframe, builder in list(timeframe_builders.items()):
                        if builder.is_empty():
                            continue

                        # Check if candle period has ended
                        seconds = TIMEFRAMES[timeframe]
                        candle_end = builder.start_time + timedelta(seconds=seconds)

                        if now >= candle_end:
                            candles_to_publish.append(builder.build())

                            # Create new builder for next period
                            new_start = self._get_candle_start(now, timeframe)
                            self._builders[symbol][timeframe] = CandleBuilder(
                                symbol, timeframe, new_start
                            )

            for candle in candles_to_publish:
                await self._publish_candle(candle)

    async def _publish_candle(self, candle: Candle) -> None:
        """Publish a completed candle to NATS"""
        topic = Topics.candles(candle.symbol, candle.timeframe)

        try:
            await self.nats.publish_json(topic, candle.to_json())
            logger.info(
                f"✓ Published candle: {candle.symbol} {candle.timeframe} "
                f"O={candle.open:.2f} H={candle.high:.2f} "
                f"L={candle.low:.2f} C={candle.close:.2f} "
                f"V={candle.volume:.0f} ticks={candle.tick_count}"
            )
        except Exception as e:
            logger.error(f"Failed to publish candle: {e}")

    async def start(self) -> None:
        """Start the aggregator"""
        logger.info(f"Starting candle aggregator for timeframes: {self.timeframes}")
        await self.nats.subscribe(Topics.all_ticks(), self._handle_tick)
        self._check_task = asyncio.create_task(self._check_and_publish_candles())
        logger.info("Candle aggregator started")

    async def stop(self) -> None:
        """Stop the aggregator"""
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass

        # Publish any remaining candles
        async with self._lock:
            for symbol, timeframe_builders in self._builders.items():
                for timeframe, builder in timeframe_builders.items():
                    if not builder.is_empty():
                        await self._publish_candle(builder.build())

        logger.info("Candle aggregator stopped")


async def main():
    """Main entry point"""
    config = NatsConfig.from_env()
    nats_client = NatsClient(config)
    timeframes = os.getenv("TIMEFRAMES", "1m,5m,15m").split(",")
    aggregator = CandleAggregator(nats_client, TIMEFRAMES.keys())

    try:
        await nats_client.connect()
        await aggregator.start()
        logger.info("Candle aggregator running. Press Ctrl+C to stop.")
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await aggregator.stop()
        await nats_client.close()


if __name__ == "__main__":
    asyncio.run(main())