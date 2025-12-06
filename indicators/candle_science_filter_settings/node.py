"""
CandleScience Filter Settings DAG Node

Implements filter settings indicator as a DAG node.
Processes candle data to calculate direction and position filters.
"""

from typing import Dict, Any
from collections import deque
import logging

from schemas.market_data import Candle
from dataflow.indicators.filter_settings.filters import FilterCalculator

logger = logging.getLogger(__name__)


class CandleScienceFilterSettingsNode:
    """
    CandleScience Filter settings indicator as a DAG node.

    Maintains a rolling buffer of N candles and calculates filters
    based on candle patterns.

    Node Protocol:
        - Inputs: candle_{timeframe} (e.g., "candle_5m")
        - Outputs: {"symbol", "timestamp", "timeframe", "filters"}
        - State: {"buffer": deque, "buffer_filled": bool}
    """

    def __init__(self, node_id: str, buffer_size: int = 3):
        """
        Initialize filter settings node.

        Args:
            node_id: Unique node identifier
            buffer_size: Number of candles to maintain in buffer
        """
        self.id = node_id
        self.buffer_size = buffer_size

        logger.info(
            f"Initialized CandleScienceFilterSettingsNode '{node_id}' "
            f"with buffer_size={buffer_size}"
        )

    def init_state(self) -> Dict[str, Any]:
        """
        Initialize node state.

        Returns:
            Dictionary with buffer and buffer_filled flag
        """
        return {
            "buffer": deque(maxlen=self.buffer_size),
            "buffer_filled": False
        }

    def compute(self, inputs: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute filter settings from candle input.

        Args:
            inputs: Dictionary with "candle_{timeframe}" key containing candle data
            state: Node state with buffer

        Returns:
            Dictionary with filter settings, or empty dict if buffer not yet filled
        """
        # Find candle input (should be "candle_5m" or similar)
        candle_data = None
        for key, value in inputs.items():
            if key.startswith("candle_"):
                candle_data = value
                break

        if not candle_data:
            logger.warning(f"Node '{self.id}': No candle input found")
            return {}

        # Convert dict to Candle object
        try:
            candle = Candle.from_dict(candle_data)
        except Exception as e:
            logger.error(f"Node '{self.id}': Failed to parse candle: {e}")
            return {}

        # Update buffer
        state["buffer"].append(candle)

        # Check if buffer is filled
        if len(state["buffer"]) == self.buffer_size:
            if not state["buffer_filled"]:
                logger.info(
                    f"Node '{self.id}': Buffer filled "
                    f"({len(state['buffer'])} candles)"
                )
                state["buffer_filled"] = True

        # Only calculate if buffer is full
        if not state["buffer_filled"]:
            logger.debug(
                f"Node '{self.id}': Buffer not yet full: "
                f"{len(state['buffer'])}/{self.buffer_size}"
            )
            return {}

        # Calculate filters
        try:
            candles = list(state["buffer"])
            filters = FilterCalculator.build_all_filters(candles)

            if not filters:
                logger.warning(f"Node '{self.id}': No filters calculated")
                return {}

            # Return output matching FilterSettings schema
            output = {
                "symbol": candle.symbol,
                "timestamp": candle.timestamp.isoformat(),
                "timeframe": candle.timeframe,
                "filters": filters
            }

            logger.debug(
                f"Node '{self.id}': Calculated {len(filters)} filters "
                f"for {candle.symbol}/{candle.timeframe}"
            )

            return output

        except Exception as e:
            logger.error(f"Node '{self.id}': Failed to calculate filters: {e}")
            return {}


def create_candle_science_filter_settings_node(node_def):
    """
    Factory function for creating CandleScience FilterSettingsNode instances.

    This function is registered with the NodeRegistry and is called
    to create node instances from NodeDef specifications.

    Args:
        node_def: NodeDef with id, type, params, inputs, outputs

    Returns:
        CandleScienceFilterSettingsNode instance
    """
    return CandleScienceFilterSettingsNode(
        node_id=node_def.id,
        buffer_size=node_def.params.get("buffer_size", 3)
    )
