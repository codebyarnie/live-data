"""
Indicator Data Schemas

Dataclasses for indicator outputs and analysis results.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict


@dataclass
class FilterSettings:
    """
    Filter settings indicator output.

    Represents calculated direction and position filters from candle patterns.
    Used to analyze price action and feed dashboards with pattern metadata.
    """
    symbol: str
    timestamp: datetime
    timeframe: str
    filters: Dict[str, str]  # Filter key -> value mapping

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe,
            "filters": self.filters
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "FilterSettings":
        """Create from dictionary."""
        return cls(
            symbol=data["symbol"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            timeframe=data["timeframe"],
            filters=data["filters"]
        )

    @classmethod
    def from_json(cls, json_str: str) -> "FilterSettings":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
