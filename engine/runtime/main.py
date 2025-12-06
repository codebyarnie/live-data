"""
DAG Coordinator - Main Entry Point

Starts the DAG coordinator for one or more symbols.
Loads YAML configs, builds DAGs, and executes indicators/strategies.
"""

import asyncio
import logging
import os
from pathlib import Path

from dataflow.adapters.nats_client import NatsClient, NatsConfig
from engine.dag.registry import NodeRegistry
from engine.runtime.coordinator import SymbolCoordinator

# Import node factories as they are implemented
from indicators.filter_settings import create_filter_settings_node

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def setup_node_registry() -> NodeRegistry:
    """
    Set up node registry and register all available node types.

    Returns:
        Configured NodeRegistry with all node types registered
    """
    registry = NodeRegistry()

    # Register node types
    registry.register("FilterSettings", create_filter_settings_node)

    # TODO: Register additional node types as they are implemented
    # registry.register("EMA", create_ema_node)
    # registry.register("VWAP", create_vwap_node)
    # registry.register("SwingPoints", create_swing_points_node)

    logger.info(f"Registered {len(registry.list_types())} node types: {registry.list_types()}")

    return registry


async def main():
    """
    Main entry point for DAG coordinator.

    Environment Variables:
        SYMBOL: Trading symbol (default: "ES")
        CONFIG_DIR: Config directory path (default: "config")
        NATS_SERVERS: NATS server URLs (default: "nats://localhost:4222")
        NATS_CLIENT_NAME: NATS client name (default: "dag-coordinator")
    """
    # Configuration from environment
    symbol = os.getenv("SYMBOL", "ES")
    config_dir = Path(os.getenv("CONFIG_DIR", "config"))

    logger.info("=" * 60)
    logger.info("DAG Coordinator Starting")
    logger.info("=" * 60)
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Config Directory: {config_dir}")

    # Set up node registry
    logger.info("Setting up node registry...")
    registry = setup_node_registry()

    # Create NATS client
    logger.info("Connecting to NATS...")
    nats_config = NatsConfig.from_env()
    nats_client = NatsClient(nats_config)
    await nats_client.connect()

    # Create coordinator for symbol
    try:
        logger.info(f"Creating coordinator for {symbol}...")
        coordinator = SymbolCoordinator(
            symbol=symbol,
            nats_client=nats_client,
            registry=registry,
            config_dir=config_dir
        )

        # Start coordinator
        await coordinator.start()

        logger.info("=" * 60)
        logger.info(f"Coordinator running for {symbol}")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)

        # Keep running and periodically log metrics
        while True:
            await asyncio.sleep(60)

            # Log metrics
            metrics = coordinator.get_metrics()
            logger.info(
                f"Metrics [{symbol}]: "
                f"{metrics['nodes']} nodes, "
                f"order: {metrics['topological_order']}"
            )

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        # Cleanup
        if 'coordinator' in locals():
            await coordinator.stop()
        await nats_client.close()

        logger.info("Coordinator stopped")


if __name__ == "__main__":
    asyncio.run(main())
