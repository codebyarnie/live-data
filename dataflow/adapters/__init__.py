"""
NATS Adapters

Provides NATS client wrappers for publishing and subscribing to events.
"""

from dataflow.adapters.nats_client import NatsClient, NatsConfig

__all__ = ["NatsClient", "NatsConfig"]
