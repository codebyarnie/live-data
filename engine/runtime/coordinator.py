"""
Symbol Coordinator

Coordinates DAG execution for a single symbol.
Handles NATS subscriptions, event routing, and output publishing.
"""

import asyncio
import json
import logging
from typing import Dict, Any
from pathlib import Path

from ..dag.builder import DAGBuilder
from ..dag.registry import NodeRegistry
from ..scheduler.executor import DAGExecutor
from ..config.loader import ConfigLoader
from dataflow.adapters.nats_client import NatsClient, Topics

logger = logging.getLogger(__name__)


class SymbolCoordinator:
    """
    Coordinates DAG execution for a single symbol.

    The coordinator:
    1. Loads pipeline configuration from YAML
    2. Builds DAG and creates node instances
    3. Subscribes to relevant NATS topics (ticks, candles)
    4. Executes DAG on each event
    5. Publishes indicator/strategy outputs to NATS

    Example usage:
        registry = NodeRegistry()
        registry.register("FilterSettings", create_filter_settings_node)

        nats_client = NatsClient(nats_config)
        await nats_client.connect()

        coordinator = SymbolCoordinator(
            symbol="ES",
            nats_client=nats_client,
            registry=registry,
            config_dir=Path("config")
        )

        await coordinator.start()
    """

    def __init__(
        self,
        symbol: str,
        nats_client: NatsClient,
        registry: NodeRegistry,
        config_dir: Path
    ):
        """
        Initialize coordinator for a symbol.

        Args:
            symbol: Trading symbol (e.g., "ES", "NQ")
            nats_client: Connected NATS client
            registry: Node registry with registered node types
            config_dir: Root config directory
        """
        self.symbol = symbol
        self.nats = nats_client
        self.registry = registry
        self.config_dir = config_dir

        # Load pipeline configuration
        logger.info(f"Loading pipeline config for {symbol}...")
        loader = ConfigLoader(config_dir)
        node_defs = loader.load_pipeline(symbol)

        # Build DAG
        logger.info(f"Building DAG for {symbol}...")
        self.dag = DAGBuilder(node_defs)
        self.dag.build()

        # Create node instances
        logger.info(f"Creating {len(node_defs)} node instances...")
        self.nodes = {}
        for node_def in node_defs:
            try:
                node = registry.create(node_def)
                self.nodes[node_def.id] = node
            except Exception as e:
                logger.error(f"Failed to create node {node_def.id}: {e}")
                raise

        # Create executor
        self.executor = DAGExecutor(self.dag, self.nodes)

        logger.info(
            f"Coordinator initialized for {symbol}: "
            f"{len(self.nodes)} nodes, "
            f"topological order: {self.dag.topo_order}"
        )

    async def start(self) -> None:
        """
        Start the coordinator.

        Subscribes to:
        - ticks.raw.{symbol} (for tick-based indicators)
        - candles.{symbol}.> (for all candle timeframes)
        """
        logger.info(f"Starting coordinator for {self.symbol}...")

        # Determine which event types we need to subscribe to
        needs_ticks = self._needs_event_type("tick")
        needs_candles = self._needs_event_type("candle")

        # Subscribe to ticks if needed
        if needs_ticks:
            topic = Topics.ticks_raw(self.symbol)
            sanitized_symbol = self.symbol.replace(" ", "_")
            await self.nats.subscribe(
                topic,
                self._handle_tick,
                queue=f"coordinator-{sanitized_symbol}-ticks"
            )
            logger.info(f"Subscribed to {topic}")

        # Subscribe to candles if needed
        if needs_candles:
            topic = Topics.candles_all(self.symbol)
            sanitized_symbol = self.symbol.replace(" ", "_")
            await self.nats.subscribe(
                topic,
                self._handle_candle,
                queue=f"coordinator-{sanitized_symbol}-candles"
            )
            logger.info(f"Subscribed to {topic}")

        logger.info(f"Coordinator started for {self.symbol}")

    def _needs_event_type(self, event_type: str) -> bool:
        """
        Check if any nodes need this event type.

        Args:
            event_type: "tick" or "candle"

        Returns:
            True if at least one node needs this event type
        """
        for node_def in self.dag.nodes.values():
            for inp in node_def.inputs:
                if inp.type.value == event_type:
                    return True
        return False

    async def _handle_tick(self, msg) -> None:
        """
        Handle incoming tick from NATS.

        Args:
            msg: NATS message with tick data
        """
        try:
            tick_data = json.loads(msg.data.decode())

            # Verify symbol matches
            if tick_data.get("symbol") != self.symbol:
                logger.warning(
                    f"Received tick for wrong symbol: {tick_data.get('symbol')} "
                    f"(expected {self.symbol})"
                )
                return

            logger.debug(f"Processing tick for {self.symbol}")

            # Execute DAG
            self.executor.execute_event("tick", tick_data)

            # Publish outputs
            await self._publish_outputs()

        except Exception as e:
            logger.error(f"Failed to handle tick: {e}", exc_info=True)

    async def _handle_candle(self, msg) -> None:
        """
        Handle incoming candle from NATS.

        Args:
            msg: NATS message with candle data
        """
        try:
            candle_data = json.loads(msg.data.decode())

            # Verify symbol matches
            if candle_data.get("symbol") != self.symbol:
                logger.warning(
                    f"Received candle for wrong symbol: {candle_data.get('symbol')} "
                    f"(expected {self.symbol})"
                )
                return

            timeframe = candle_data.get("timeframe")
            logger.debug(f"Processing candle for {self.symbol}/{timeframe}")

            # Execute DAG
            self.executor.execute_event("candle", candle_data)

            # Publish outputs
            await self._publish_outputs()

        except Exception as e:
            logger.error(f"Failed to handle candle: {e}", exc_info=True)

    async def _publish_outputs(self) -> None:
        """
        Publish indicator and strategy outputs to NATS.

        Publishes to:
        - indicators.{symbol}.{indicator_id} for indicator outputs
        - strategies.signals.{symbol}.{strategy_id} for strategy outputs
        """
        for node_id, output in self.executor.node_outputs.items():
            if not output:
                # Skip empty outputs
                continue

            node_def = self.dag.nodes[node_id]

            # Determine topic based on node type
            # Convention: Strategy types end with "Strategy" or are known strategy types
            is_strategy = (
                node_def.type.endswith("Strategy") or
                node_def.type in ["LiquidityBreakout", "Breakout", "MeanReversion"]
            )

            if is_strategy:
                # Strategy signal
                topic = f"strategies.signals.{Topics._sanitize(self.symbol)}.{node_id}"
            else:
                # Indicator output
                topic = Topics.indicators(self.symbol, node_id)

            try:
                payload = json.dumps(output)
                await self.nats.publish_json(topic, payload)

                logger.debug(f"Published {node_id} output to {topic}")

            except Exception as e:
                logger.error(f"Failed to publish {node_id} output: {e}")

    async def stop(self) -> None:
        """Stop the coordinator"""
        logger.info(
            f"Stopping coordinator for {self.symbol}"
        )
        # NATS client handles unsubscribe on disconnect

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get coordinator metrics.

        Returns:
            Dictionary with coordinator statistics
        """
        return {
            "symbol": self.symbol,
            "nodes": len(self.nodes),
            "topological_order": self.dag.topo_order,
            "node_states": {
                nid: len(state) for nid, state in self.executor.node_states.items()
            }
        }
