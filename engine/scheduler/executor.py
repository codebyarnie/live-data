"""
DAG Executor

Executes DAG nodes in topological order based on incoming events.
Manages node state and input/output data flow.
"""

from typing import Dict, List, Any, Set
import logging

from ..dag.builder import DAGBuilder
from ..dag.node import Node, InputType

logger = logging.getLogger(__name__)


class DAGExecutor:
    """
    Executes DAG nodes in topological order.

    The executor:
    1. Receives events (ticks, candles)
    2. Determines which nodes are impacted
    3. Executes impacted nodes in topological order
    4. Manages node state and caches outputs

    Example usage:
        builder = DAGBuilder(node_defs)
        builder.build()

        nodes = {nid: create_node(ndef) for nid, ndef in builder.nodes.items()}
        executor = DAGExecutor(builder, nodes)

        # Process candle event
        candle_data = {"symbol": "ES", "timeframe": "5m", ...}
        executor.execute_event("candle", candle_data)

        # Access outputs
        ema_value = executor.node_outputs["ema_20"]["value"]
    """

    def __init__(self, dag: DAGBuilder, nodes: Dict[str, Node]):
        """
        Initialize executor with DAG and node instances.

        Args:
            dag: Built DAG with topological order
            nodes: Dictionary mapping node_id to Node instance
        """
        self.dag = dag
        self.nodes = nodes

        # Initialize node states
        self.node_states = {
            node_id: node.init_state()
            for node_id, node in nodes.items()
        }

        # Cache for node outputs (cleared on each event)
        self.node_outputs: Dict[str, Dict[str, Any]] = {}

        logger.info(
            f"Initialized DAGExecutor with {len(nodes)} nodes, "
            f"topological order: {dag.topo_order}"
        )

    def execute_event(self, event_type: str, event_data: Any) -> None:
        """
        Execute DAG for an incoming event.

        1. Determine which nodes are impacted by this event
        2. Filter topological order to impacted nodes
        3. Execute nodes in order

        Args:
            event_type: Type of event ("tick", "candle")
            event_data: Event payload (dict with event-specific fields)
        """
        logger.debug(f"Processing {event_type} event")

        # Clear previous outputs
        self.node_outputs = {}

        # Determine impacted nodes
        impacted = self._get_impacted_nodes(event_type, event_data)

        if not impacted:
            logger.debug(f"No nodes impacted by {event_type} event")
            return

        # Filter topological order to impacted nodes
        exec_order = [n for n in self.dag.topo_order if n in impacted]

        logger.debug(f"Executing {len(exec_order)} nodes: {exec_order}")

        # Execute nodes in order
        for node_id in exec_order:
            self._execute_node(node_id, event_type, event_data)

        logger.debug(f"Completed execution of {len(exec_order)} nodes")

    def _get_impacted_nodes(self, event_type: str, event_data: Any) -> Set[str]:
        """
        Determine which nodes need recomputation for this event.

        A node is impacted if:
        1. It directly consumes this event type
        2. It depends on an impacted node (transitive)

        Args:
            event_type: Type of event ("tick", "candle")
            event_data: Event payload

        Returns:
            Set of node IDs that should be executed
        """
        impacted = set()

        # Find nodes that directly depend on this event
        for node_id, node_def in self.dag.nodes.items():
            for inp in node_def.inputs:
                # Check if this input matches the event
                if inp.type.value == event_type:
                    # For candles, also match timeframe
                    if event_type == "candle":
                        event_tf = event_data.get("timeframe")
                        if inp.source == event_tf:
                            impacted.add(node_id)
                            self._add_transitive_deps(node_id, impacted)
                    else:
                        # For ticks, just match type
                        impacted.add(node_id)
                        self._add_transitive_deps(node_id, impacted)

        return impacted

    def _add_transitive_deps(self, node_id: str, impacted: Set[str]) -> None:
        """
        Add all transitive dependents of a node to impacted set.

        Uses the reverse dependency graph to find all downstream nodes.

        Args:
            node_id: Starting node ID
            impacted: Set to add transitive dependents to (modified in place)
        """
        for dep in self.dag.reverse_deps.get(node_id, []):
            if dep not in impacted:
                impacted.add(dep)
                self._add_transitive_deps(dep, impacted)

    def _execute_node(self, node_id: str, event_type: str, event_data: Any) -> None:
        """
        Execute a single node.

        1. Gather inputs from event data and upstream node outputs
        2. Call node's compute() method
        3. Cache output

        Args:
            node_id: ID of node to execute
            event_type: Current event type
            event_data: Current event data
        """
        node = self.nodes[node_id]
        node_def = self.dag.nodes[node_id]

        # Gather inputs
        inputs = self._gather_inputs(node_def, event_type, event_data)

        logger.debug(
            f"Executing node '{node_id}' (type={node_def.type}) "
            f"with inputs: {list(inputs.keys())}"
        )

        # Execute node
        try:
            output = node.compute(inputs, self.node_states[node_id])

            # Store output
            self.node_outputs[node_id] = output

            logger.debug(f"Node '{node_id}' output: {list(output.keys())}")

        except Exception as e:
            logger.error(f"Failed to execute node '{node_id}': {e}", exc_info=True)
            # Store empty output to prevent downstream failures
            self.node_outputs[node_id] = {}

    def _gather_inputs(
        self, node_def, event_type: str, event_data: Any
    ) -> Dict[str, Any]:
        """
        Gather all inputs for a node.

        Inputs come from:
        1. Event data (ticks, candles)
        2. Upstream node outputs (indicators)

        Args:
            node_def: Node definition with input specifications
            event_type: Current event type
            event_data: Current event data

        Returns:
            Dictionary of input name -> value
        """
        inputs = {}

        for inp_ref in node_def.inputs:
            if inp_ref.type == InputType.TICK and event_type == "tick":
                # Provide tick data
                inputs["tick"] = event_data

            elif inp_ref.type == InputType.CANDLE and event_type == "candle":
                # Provide candle data if timeframe matches
                if inp_ref.source == event_data.get("timeframe"):
                    key = f"candle_{inp_ref.source}"
                    inputs[key] = event_data

            elif inp_ref.type == InputType.INDICATOR:
                # Get cached output from earlier in this execution
                indicator_output = self.node_outputs.get(inp_ref.source)

                if indicator_output:
                    if inp_ref.field:
                        # Extract specific field from multi-output indicator
                        inputs[inp_ref.source] = indicator_output.get(inp_ref.field)
                    else:
                        # Single-output indicator or full output
                        inputs[inp_ref.source] = indicator_output
                else:
                    # Upstream node didn't execute (shouldn't happen with correct topo order)
                    logger.warning(
                        f"Node '{node_def.id}' depends on '{inp_ref.source}' "
                        f"but no output available"
                    )

        return inputs

    def get_node_output(self, node_id: str) -> Dict[str, Any]:
        """
        Get the most recent output of a node.

        Args:
            node_id: Node identifier

        Returns:
            Node output dictionary, or empty dict if no output
        """
        return self.node_outputs.get(node_id, {})

    def get_node_state(self, node_id: str) -> Dict[str, Any]:
        """
        Get the current state of a node.

        Args:
            node_id: Node identifier

        Returns:
            Node state dictionary
        """
        return self.node_states.get(node_id, {})

    def reset_node_state(self, node_id: str) -> None:
        """
        Reset a node's state to initial values.

        Args:
            node_id: Node identifier
        """
        if node_id in self.nodes:
            self.node_states[node_id] = self.nodes[node_id].init_state()
            logger.info(f"Reset state for node: {node_id}")
        else:
            logger.warning(f"Cannot reset unknown node: {node_id}")
