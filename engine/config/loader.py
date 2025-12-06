"""
Config Loader

Loads and merges pipeline configurations from YAML files.
Converts YAML specifications to NodeDef objects for DAG construction.
"""

import yaml
from pathlib import Path
from typing import List, Dict
from pydantic import BaseModel, Field
import logging

from ..dag.node import NodeDef, InputRef, InputType

logger = logging.getLogger(__name__)


class IndicatorConfig(BaseModel):
    """Configuration for an indicator node"""
    id: str
    type: str
    params: Dict = Field(default_factory=dict)
    inputs: List[Dict]


class StrategyConfig(BaseModel):
    """Configuration for a strategy node"""
    id: str
    type: str
    params: Dict = Field(default_factory=dict)
    depends_on: List[str]


class PipelineConfig(BaseModel):
    """Complete pipeline configuration for a symbol"""
    symbol: str
    indicators: List[IndicatorConfig] = Field(default_factory=list)
    strategies: List[StrategyConfig] = Field(default_factory=list)


class ConfigLoader:
    """
    Loads and merges pipeline configs from YAML.

    The loader:
    1. Finds all YAML files in a symbol's directory
    2. Loads and validates each file
    3. Merges indicators and strategies (validating uniqueness)
    4. Converts to NodeDef objects

    Example usage:
        loader = ConfigLoader(Path("config"))
        node_defs = loader.load_pipeline("ES")

        # node_defs is a list of NodeDef objects ready for DAG construction
    """

    def __init__(self, config_dir: Path):
        """
        Initialize loader with config directory.

        Args:
            config_dir: Root config directory (contains pipelines/ subdirectory)
        """
        self.config_dir = config_dir
        logger.info(f"Initialized ConfigLoader with config_dir: {config_dir}")

    def load_pipeline(self, symbol: str) -> List[NodeDef]:
        """
        Load all YAML files for a symbol and merge into NodeDef list.

        Args:
            symbol: Trading symbol (e.g., "ES", "NQ")

        Returns:
            List of NodeDef objects representing the complete pipeline

        Raises:
            ValueError: If no config found, conflicts exist, or validation fails
        """
        symbol_dir = self.config_dir / "pipelines" / symbol

        if not symbol_dir.exists():
            raise ValueError(
                f"No config directory for symbol: {symbol}. "
                f"Expected: {symbol_dir}"
            )

        # Load all YAML files
        yaml_files = list(symbol_dir.glob("*.yaml"))
        if not yaml_files:
            raise ValueError(f"No YAML files found in {symbol_dir}")

        logger.info(f"Loading {len(yaml_files)} YAML files for {symbol}")

        configs = []
        for yaml_file in yaml_files:
            try:
                with open(yaml_file) as f:
                    raw = yaml.safe_load(f)
                    config = PipelineConfig(**raw)

                    # Validate symbol matches
                    if config.symbol != symbol:
                        logger.warning(
                            f"Symbol mismatch in {yaml_file.name}: "
                            f"expected {symbol}, got {config.symbol}"
                        )

                    configs.append(config)
                    logger.debug(f"Loaded {yaml_file.name}: {len(config.indicators)} indicators, {len(config.strategies)} strategies")

            except Exception as e:
                logger.error(f"Failed to load {yaml_file}: {e}")
                raise ValueError(f"Failed to load {yaml_file}: {e}")

        # Merge and deduplicate
        node_defs = self._merge_configs(configs)

        logger.info(
            f"Loaded pipeline for {symbol}: {len(node_defs)} total nodes"
        )

        return node_defs

    def _merge_configs(self, configs: List[PipelineConfig]) -> List[NodeDef]:
        """
        Merge multiple configs, validating uniqueness.

        Args:
            configs: List of PipelineConfig objects from different YAML files

        Returns:
            List of NodeDef objects

        Raises:
            ValueError: If conflicts exist (duplicate IDs with different definitions)
        """
        all_indicators = {}
        all_strategies = {}

        # Merge indicators
        for config in configs:
            for ind in config.indicators:
                if ind.id in all_indicators:
                    # Validate parameters match
                    existing = all_indicators[ind.id]
                    if (existing.params != ind.params or
                        existing.type != ind.type or
                        existing.inputs != ind.inputs):
                        raise ValueError(
                            f"Conflicting definitions for indicator: {ind.id}\n"
                            f"First: {existing}\n"
                            f"Second: {ind}"
                        )
                    logger.debug(f"Indicator {ind.id} already defined (identical), skipping")
                else:
                    all_indicators[ind.id] = ind

            # Merge strategies
            for strat in config.strategies:
                if strat.id in all_strategies:
                    raise ValueError(f"Duplicate strategy id: {strat.id}")
                all_strategies[strat.id] = strat

        # Convert to NodeDef objects
        node_defs = []

        # Convert indicators
        for ind in all_indicators.values():
            inputs = []
            for inp_dict in ind.inputs:
                try:
                    input_ref = InputRef(
                        type=InputType(inp_dict["type"]),
                        source=inp_dict["source"],
                        field=inp_dict.get("field")
                    )
                    inputs.append(input_ref)
                except KeyError as e:
                    raise ValueError(
                        f"Invalid input for indicator {ind.id}: missing {e}"
                    )
                except ValueError as e:
                    raise ValueError(
                        f"Invalid input type for indicator {ind.id}: {e}"
                    )

            node_defs.append(NodeDef(
                id=ind.id,
                type=ind.type,
                inputs=inputs,
                params=ind.params,
                outputs=["value"]  # Default single output
            ))

        # Convert strategies (strategies depend on indicators)
        for strat in all_strategies.values():
            inputs = [
                InputRef(type=InputType.INDICATOR, source=dep)
                for dep in strat.depends_on
            ]

            node_defs.append(NodeDef(
                id=strat.id,
                type=strat.type,
                inputs=inputs,
                params=strat.params,
                outputs=["signal"]  # Default strategy output
            ))

        return node_defs
