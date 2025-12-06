"""
Node Registry

Factory registry for creating node instances from NodeDef specifications.
Allows dynamic node type registration and instantiation.
"""

from typing import Dict, Callable
import logging

from .node import Node, NodeDef

logger = logging.getLogger(__name__)


class NodeRegistry:
    """
    Registry of available node types with factory functions.

    The registry maintains a mapping from node type names (e.g., "EMA", "VWAP")
    to factory functions that create node instances.

    Example usage:
        registry = NodeRegistry()

        # Register a node type
        def create_ema_node(node_def: NodeDef) -> Node:
            return EMANode(
                node_id=node_def.id,
                length=node_def.params.get("length", 20)
            )

        registry.register("EMA", create_ema_node)

        # Create a node from definition
        node_def = NodeDef(
            id="ema_20",
            type="EMA",
            inputs=[InputRef(type=InputType.CANDLE, source="1m")],
            params={"length": 20},
            outputs=["value"]
        )
        node = registry.create(node_def)
    """

    def __init__(self):
        """Initialize empty registry"""
        self._factories: Dict[str, Callable[[NodeDef], Node]] = {}
        logger.debug("Initialized NodeRegistry")

    def register(self, node_type: str, factory: Callable[[NodeDef], Node]) -> None:
        """
        Register a node type factory.

        Args:
            node_type: Type identifier (e.g., "EMA", "VWAP", "FilterSettings")
            factory: Callable that takes NodeDef and returns Node instance

        Raises:
            ValueError: If node_type is already registered
        """
        if node_type in self._factories:
            logger.warning(f"Overwriting existing registration for node type: {node_type}")

        self._factories[node_type] = factory
        logger.info(f"Registered node type: {node_type}")

    def create(self, node_def: NodeDef) -> Node:
        """
        Create a node instance from definition.

        Args:
            node_def: Node definition containing type, params, inputs, outputs

        Returns:
            Instantiated node conforming to Node protocol

        Raises:
            ValueError: If node_def.type is not registered
        """
        if node_def.type not in self._factories:
            available = ", ".join(self._factories.keys())
            raise ValueError(
                f"Unknown node type: {node_def.type}. "
                f"Available types: {available if available else 'none'}"
            )

        factory = self._factories[node_def.type]
        node = factory(node_def)

        logger.debug(
            f"Created node: id={node_def.id}, type={node_def.type}, "
            f"params={node_def.params}"
        )

        return node

    def list_types(self) -> list[str]:
        """
        List all registered node types.

        Returns:
            List of registered node type names
        """
        return list(self._factories.keys())

    def is_registered(self, node_type: str) -> bool:
        """
        Check if a node type is registered.

        Args:
            node_type: Type identifier to check

        Returns:
            True if node_type is registered, False otherwise
        """
        return node_type in self._factories
