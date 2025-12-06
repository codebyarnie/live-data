"""
DAG Builder

Builds and validates directed acyclic graphs from node definitions.
Performs cycle detection and computes topological execution order.
"""

from typing import List, Dict, Set
import logging

from .node import NodeDef, InputType

logger = logging.getLogger(__name__)


class DAGBuilder:
    """
    Builds and validates DAG from node definitions.

    The builder:
    1. Constructs adjacency lists from node input/output dependencies
    2. Validates no cycles exist (using DFS)
    3. Computes topological execution order (using Kahn's algorithm)

    Example usage:
        node_defs = [
            NodeDef(id="ema_20", type="EMA", inputs=[...], ...),
            NodeDef(id="strategy", type="Breakout", inputs=[...], ...)
        ]

        builder = DAGBuilder(node_defs)
        builder.build()

        # Access results
        print(builder.topo_order)  # ["ema_20", "strategy"]
        print(builder.adjacency)   # {"strategy": ["ema_20"]}
    """

    def __init__(self, node_defs: List[NodeDef]):
        """
        Initialize builder with node definitions.

        Args:
            node_defs: List of node definitions to build into DAG
        """
        self.nodes: Dict[str, NodeDef] = {n.id: n for n in node_defs}
        self.adjacency: Dict[str, List[str]] = {}
        self.reverse_deps: Dict[str, Set[str]] = {}
        self.topo_order: List[str] = []

        logger.info(f"Initialized DAGBuilder with {len(self.nodes)} nodes")

    def build(self) -> None:
        """
        Build DAG: construct adjacency lists, validate, compute order.

        Raises:
            ValueError: If DAG contains cycles or invalid dependencies
        """
        logger.info("Building DAG...")
        self._build_adjacency()
        self._validate_no_cycles()
        self._compute_topo_order()
        logger.info(
            f"DAG built successfully: {len(self.nodes)} nodes, "
            f"topological order: {self.topo_order}"
        )

    def _build_adjacency(self) -> None:
        """
        Build dependency graph from node inputs.

        For each node, extract dependencies from InputRef objects:
        - InputType.INDICATOR: Direct dependency on another node
        - InputType.CANDLE/TICK: External data dependency (no node dependency)

        Adjacency format: {node_id: [list of nodes it depends on]}
        Reverse deps format: {node_id: set of nodes that depend on it}
        """
        for node_id, node in self.nodes.items():
            deps = []

            for inp in node.inputs:
                if inp.type == InputType.INDICATOR:
                    # Validate dependency exists
                    if inp.source not in self.nodes:
                        raise ValueError(
                            f"Node '{node_id}' depends on unknown indicator: '{inp.source}'"
                        )
                    deps.append(inp.source)

            self.adjacency[node_id] = deps

            # Build reverse dependencies
            for dep in deps:
                if dep not in self.reverse_deps:
                    self.reverse_deps[dep] = set()
                self.reverse_deps[dep].add(node_id)

        logger.debug(f"Built adjacency lists: {self.adjacency}")
        logger.debug(f"Built reverse dependencies: {self.reverse_deps}")

    def _validate_no_cycles(self) -> None:
        """
        Detect cycles using depth-first search.

        Uses DFS with recursion stack to detect back edges (cycles).

        Raises:
            ValueError: If a cycle is detected
        """
        visited = set()
        rec_stack = set()

        def dfs(node_id: str, path: List[str]) -> None:
            """
            DFS traversal with cycle detection.

            Args:
                node_id: Current node being visited
                path: Path from root to current node (for error reporting)
            """
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for dep in self.adjacency.get(node_id, []):
                if dep not in visited:
                    dfs(dep, path[:])
                elif dep in rec_stack:
                    # Cycle detected
                    cycle_start = path.index(dep)
                    cycle = path[cycle_start:] + [dep]
                    raise ValueError(
                        f"Cycle detected in DAG: {' -> '.join(cycle)}"
                    )

            rec_stack.remove(node_id)

        # Run DFS from all unvisited nodes
        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id, [])

        logger.debug("No cycles detected in DAG")

    def _compute_topo_order(self) -> None:
        """
        Compute topological sort using Kahn's algorithm.

        Algorithm:
        1. Start with nodes that have no dependencies (in-degree = 0)
        2. Process each node, reducing in-degree of neighbors
        3. Add neighbors with in-degree 0 to queue
        4. Repeat until all nodes processed

        The resulting order ensures dependencies are computed before dependents.

        Raises:
            ValueError: If topological sort fails (indicates cycle, though
                       this should be caught by _validate_no_cycles)
        """
        # Calculate in-degrees (number of dependencies per node)
        in_degree = {n: 0 for n in self.nodes}
        for deps in self.adjacency.values():
            for dep in deps:
                in_degree[dep] += 1

        # Start with nodes that have no dependencies
        queue = [n for n in self.nodes if in_degree[n] == 0]
        self.topo_order = []

        logger.debug(f"Starting topological sort with queue: {queue}")

        while queue:
            # Process node with no remaining dependencies
            node_id = queue.pop(0)
            self.topo_order.append(node_id)

            # Reduce in-degree of nodes that depend on this one
            for neighbor in self.adjacency.get(node_id, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Verify all nodes were processed
        if len(self.topo_order) != len(self.nodes):
            missing = set(self.nodes.keys()) - set(self.topo_order)
            raise ValueError(
                f"Topological sort failed - DAG contains cycle. "
                f"Unreachable nodes: {missing}"
            )

        logger.debug(f"Computed topological order: {self.topo_order}")

    def get_dependencies(self, node_id: str) -> List[str]:
        """
        Get direct dependencies of a node.

        Args:
            node_id: Node identifier

        Returns:
            List of node IDs this node depends on
        """
        return self.adjacency.get(node_id, [])

    def get_dependents(self, node_id: str) -> Set[str]:
        """
        Get nodes that depend on this node.

        Args:
            node_id: Node identifier

        Returns:
            Set of node IDs that depend on this node
        """
        return self.reverse_deps.get(node_id, set())

    def get_all_transitive_dependents(self, node_id: str) -> Set[str]:
        """
        Get all transitive dependents of a node (downstream nodes).

        Args:
            node_id: Node identifier

        Returns:
            Set of all node IDs that transitively depend on this node
        """
        transitive = set()

        def collect_deps(nid: str):
            for dep in self.get_dependents(nid):
                if dep not in transitive:
                    transitive.add(dep)
                    collect_deps(dep)

        collect_deps(node_id)
        return transitive
