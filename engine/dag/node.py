"""
DAG Node Model

Defines the core data structures and protocols for DAG nodes (indicators and strategies).
Each node represents a computational unit with inputs, parameters, and outputs.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Protocol
from enum import Enum


class InputType(Enum):
    """Type of input that a node can consume"""
    TICK = "tick"
    CANDLE = "candle"
    INDICATOR = "indicator"


@dataclass
class InputRef:
    """
    Reference to an input source for a node.

    Examples:
        - Candle input: InputRef(type=InputType.CANDLE, source="5m")
        - Indicator input: InputRef(type=InputType.INDICATOR, source="ema_20")
        - Multi-output indicator: InputRef(type=InputType.INDICATOR, source="bollinger", field="upper")
    """
    type: InputType
    source: str  # For CANDLE: "5m", for INDICATOR: "ema_20"
    field: Optional[str] = None  # For multi-output indicators: "poc", "upper", etc.


@dataclass
class NodeDef:
    """
    Definition of a DAG node (indicator or strategy).

    This is the declarative specification loaded from YAML configs.
    NodeDef instances are used to create executable Node instances.

    Attributes:
        id: Unique identifier for this node (e.g., "ema_20", "breakout_strategy")
        type: Node type identifier (e.g., "EMA", "VWAP", "LiquidityBreakout")
        inputs: List of input references this node depends on
        params: Node-specific parameters (e.g., {"length": 20} for EMA)
        outputs: List of output field names (single: ["value"], multi: ["upper", "middle", "lower"])
    """
    id: str
    type: str  # "EMA", "VWAP", "SwingPoints", "LiquidityBreakout"
    inputs: List[InputRef]
    params: Dict[str, Any]
    outputs: List[str]  # For multi-output: ["upper", "middle", "lower"]


class Node(Protocol):
    """
    Protocol for executable DAG nodes.

    All indicator and strategy implementations must conform to this protocol.
    Nodes are stateful computational units that:
    - Maintain internal state across invocations
    - Receive inputs from upstream nodes or market data
    - Produce outputs consumed by downstream nodes

    Example implementation:
        class EMANode:
            def __init__(self, node_id: str, length: int):
                self.id = node_id
                self.length = length

            def init_state(self) -> Dict[str, Any]:
                return {"values": deque(maxlen=self.length)}

            def compute(self, inputs: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
                candle = inputs.get("candle_1m")
                state["values"].append(candle.close)
                ema = sum(state["values"]) / len(state["values"])
                return {"value": ema}
    """
    id: str

    def compute(self, inputs: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute node computation.

        Args:
            inputs: Dictionary of input values from upstream nodes or market data
                   Keys follow pattern: "candle_{timeframe}" or "{indicator_id}"
            state: Node's internal state (initialized by init_state(), persisted across calls)

        Returns:
            Dictionary of output values matching the node's defined outputs
            Keys should match the output field names defined in NodeDef.outputs
        """
        ...

    def init_state(self) -> Dict[str, Any]:
        """
        Initialize node state.

        Called once when the node is created. Returns the initial state dictionary
        that will be passed to compute() on each invocation.

        Returns:
            Initial state dictionary (can be empty {} if node is stateless)
        """
        ...
