"""
Market Data Types

Core market data types used throughout the trading engine.
These types are used for NATS messaging and TimescaleDB persistence.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Literal
import json


@dataclass
class Tick:
    """Raw tick data from market feed"""
    symbol: str
    timestamp: datetime
    price: float
    volume: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "volume": self.volume,
            "bid": self.bid,
            "ask": self.ask,
        }

    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "Tick":
        """Create Tick from dictionary"""
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return cls(
            symbol=data["symbol"],
            timestamp=timestamp,
            price=data["price"],
            volume=data.get("volume"),
            bid=data.get("bid"),
            ask=data.get("ask"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Tick":
        """Deserialize from JSON string"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class Candle:
    """OHLCV candle data with timeframe metadata"""
    symbol: str
    timestamp: datetime
    timeframe: str  # '1m', '5m', '15m', '1h', '1d', etc.
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    tick_count: int = 0  # Number of ticks that formed this candle

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "timeframe": self.timeframe,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "tick_count": self.tick_count,
        }

    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "Candle":
        """Create Candle from dictionary"""
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return cls(
            symbol=data["symbol"],
            timestamp=timestamp,
            timeframe=data["timeframe"],
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            volume=data.get("volume", 0.0),
            tick_count=data.get("tick_count", 0),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Candle":
        """Deserialize from JSON string"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class Quote:
    """Bid/Ask/Spread quote data"""
    symbol: str
    timestamp: datetime
    bid: float
    ask: float
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None

    @property
    def spread(self) -> float:
        """Calculate bid-ask spread"""
        return self.ask - self.bid

    @property
    def mid(self) -> float:
        """Calculate mid price"""
        return (self.bid + self.ask) / 2

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "bid": self.bid,
            "ask": self.ask,
            "bid_size": self.bid_size,
            "ask_size": self.ask_size,
            "spread": self.spread,
            "mid": self.mid,
        }

    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> "Quote":
        """Create Quote from dictionary"""
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return cls(
            symbol=data["symbol"],
            timestamp=timestamp,
            bid=data["bid"],
            ask=data["ask"],
            bid_size=data.get("bid_size"),
            ask_size=data.get("ask_size"),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Quote":
        """Deserialize from JSON string"""
        return cls.from_dict(json.loads(json_str))
