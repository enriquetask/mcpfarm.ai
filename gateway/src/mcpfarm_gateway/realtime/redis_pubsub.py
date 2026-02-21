"""Redis event adapter for pub/sub."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

CHANNEL = "mcpfarm:events"


class EventBus:
    """Publishes and subscribes to events via Redis pub/sub."""

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """Publish an event to the bus."""
        message = json.dumps({"type": event_type, "data": data})
        await self.redis.publish(CHANNEL, message)
        logger.debug("Published event: %s", event_type)

    async def subscribe(self):
        """Subscribe to events. Yields (event_type, data) tuples."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(CHANNEL)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    payload = json.loads(message["data"])
                    yield payload["type"], payload["data"]
        finally:
            await pubsub.unsubscribe(CHANNEL)
            await pubsub.close()
