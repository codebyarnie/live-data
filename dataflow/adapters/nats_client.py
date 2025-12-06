"""
NATS Client Adapter

Provides async NATS client for publishing and subscribing to market data events.
Supports both internal and external NATS connections.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional, Awaitable, Any
import nats
from nats.aio.client import Client as NatsConnection
from nats.aio.msg import Msg

logger = logging.getLogger(__name__)


@dataclass
class NatsConfig:
    """NATS connection configuration"""
    servers: list[str] = field(default_factory=lambda: ["nats://localhost:4222"])
    name: str = "trading-engine"
    reconnect_time_wait: float = 2.0
    max_reconnect_attempts: int = -1  # Infinite reconnects
    ping_interval: int = 20
    max_outstanding_pings: int = 3

    @classmethod
    def from_env(cls, prefix: str = "NATS") -> "NatsConfig":
        """Create config from environment variables"""
        import os
        servers = os.getenv(f"{prefix}_SERVERS", "nats://localhost:4222")
        return cls(
            servers=servers.split(","),
            name=os.getenv(f"{prefix}_CLIENT_NAME", "trading-engine"),
        )


class NatsClient:
    """
    Async NATS client wrapper for trading engine.

    Provides simplified pub/sub interface with automatic reconnection
    and error handling.

    Topic Patterns:
    - ticks.raw.{symbol}          - Raw tick data from ingestion
    - candles.{symbol}.{tf}       - Aggregated candles
    - indicators.{symbol}.{id}    - Indicator outputs
    - strategies.signals.{symbol} - Strategy signals
    """

    def __init__(self, config: Optional[NatsConfig] = None):
        self.config = config or NatsConfig()
        self._nc: Optional[NatsConnection] = None
        self._subscriptions: dict[str, Any] = {}
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if client is connected"""
        return self._connected and self._nc is not None and self._nc.is_connected

    async def connect(self) -> None:
        """Establish connection to NATS server"""
        if self._connected:
            return

        async def error_handler(e):
            logger.error(f"NATS error: {e}")

        async def closed_handler():
            logger.warning("NATS connection closed")
            self._connected = False

        async def reconnected_handler():
            logger.info("NATS reconnected")
            self._connected = True

        async def disconnected_handler():
            logger.warning("NATS disconnected")
            self._connected = False

        try:
            self._nc = await nats.connect(
                servers=self.config.servers,
                name=self.config.name,
                reconnect_time_wait=self.config.reconnect_time_wait,
                max_reconnect_attempts=self.config.max_reconnect_attempts,
                ping_interval=self.config.ping_interval,
                max_outstanding_pings=self.config.max_outstanding_pings,
                error_cb=error_handler,
                closed_cb=closed_handler,
                reconnected_cb=reconnected_handler,
                disconnected_cb=disconnected_handler,
            )
            self._connected = True
            logger.info(f"Connected to NATS: {self.config.servers}")
        except Exception as e:
            logger.error(f"Failed to connect to NATS: {e}")
            raise

    async def close(self) -> None:
        """Close NATS connection"""
        if self._nc:
            await self._nc.drain()
            await self._nc.close()
            self._connected = False
            logger.info("NATS connection closed")

    async def publish(self, subject: str, data: bytes) -> None:
        """
        Publish data to a NATS subject.

        Args:
            subject: NATS subject (e.g., "ticks.raw.ES")
            data: Bytes payload (typically JSON)
        """
        if not self.is_connected:
            raise RuntimeError("NATS client not connected")
        await self._nc.publish(subject, data)
        logger.debug(f"Published to {subject}: {len(data)} bytes")

    async def publish_json(self, subject: str, data: str) -> None:
        """
        Publish JSON string to a NATS subject.

        Args:
            subject: NATS subject
            data: JSON string
        """
        await self.publish(subject, data.encode("utf-8"))

    async def subscribe(
        self,
        subject: str,
        callback: Callable[[Msg], Awaitable[None]],
        queue: Optional[str] = None,
    ) -> None:
        """
        Subscribe to a NATS subject.

        Args:
            subject: NATS subject pattern (supports wildcards: *, >)
            callback: Async callback for received messages
            queue: Optional queue group for load balancing
        """
        if not self.is_connected:
            raise RuntimeError("NATS client not connected")

        if queue:
            sub = await self._nc.subscribe(subject, queue=queue, cb=callback)
        else:
            sub = await self._nc.subscribe(subject, cb=callback)

        self._subscriptions[subject] = sub
        logger.info(f"Subscribed to {subject}" + (f" (queue: {queue})" if queue else ""))

    async def unsubscribe(self, subject: str) -> None:
        """Unsubscribe from a subject"""
        if subject in self._subscriptions:
            await self._subscriptions[subject].unsubscribe()
            del self._subscriptions[subject]
            logger.info(f"Unsubscribed from {subject}")

    async def request(
        self, subject: str, data: bytes, timeout: float = 5.0
    ) -> Msg:
        """
        Send a request and wait for response.

        Args:
            subject: NATS subject
            data: Request payload
            timeout: Timeout in seconds

        Returns:
            Response message
        """
        if not self.is_connected:
            raise RuntimeError("NATS client not connected")
        return await self._nc.request(subject, data, timeout=timeout)


# Topic helpers
class Topics:
    """NATS topic name builders"""

    @staticmethod
    def _sanitize(name: str) -> str:
        """
        Sanitize a name for use in NATS topics.

        NATS topic segments can only contain alphanumeric characters,
        hyphens, and underscores. Spaces and other characters are
        replaced with underscores.
        """
        # Replace spaces with underscores
        # Replace any other invalid characters with underscores
        sanitized = name.replace(" ", "_")
        # Keep only alphanumeric, hyphens, underscores
        sanitized = "".join(c if c.isalnum() or c in "-_" else "_" for c in sanitized)
        return sanitized

    @staticmethod
    def ticks_raw(symbol: str) -> str:
        """Raw tick topic for a symbol"""
        return f"ticks.raw.{Topics._sanitize(symbol)}"

    @staticmethod
    def candles(symbol: str, timeframe: str) -> str:
        """Candle topic for a symbol and timeframe"""
        return f"candles.{Topics._sanitize(symbol)}.{timeframe}"

    @staticmethod
    def candles_all(symbol: str) -> str:
        """All candle timeframes for a symbol (wildcard)"""
        return f"candles.{Topics._sanitize(symbol)}.*"

    @staticmethod
    def indicators(symbol: str, indicator_id: str) -> str:
        """Indicator output topic"""
        return f"indicators.{Topics._sanitize(symbol)}.{indicator_id}"

    @staticmethod
    def strategy_signals(symbol: str) -> str:
        """Strategy signals topic"""
        return f"strategies.signals.{Topics._sanitize(symbol)}"

    @staticmethod
    def all_ticks() -> str:
        """Subscribe to all tick symbols"""
        return "ticks.raw.*"

    @staticmethod
    def all_candles() -> str:
        """Subscribe to all candles"""
        return "candles.>"
