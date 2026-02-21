"""WebSocket connection manager.

Broadcasts events from Redis pub/sub to all connected frontend clients.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import TYPE_CHECKING, Any

from mcpfarm_gateway.observability.metrics import websocket_connections

if TYPE_CHECKING:
    from fastapi import WebSocket

    from mcpfarm_gateway.realtime.redis_pubsub import EventBus

logger = logging.getLogger(__name__)


class WebSocketHub:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._connections: set[WebSocket] = set()
        self._listener_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the background listener that relays Redis events to WebSockets."""
        self._listener_task = asyncio.create_task(self._relay_events())
        logger.info("WebSocket hub started")

    async def stop(self) -> None:
        """Stop the background listener."""
        if self._listener_task:
            self._listener_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listener_task
            self._listener_task = None
        logger.info("WebSocket hub stopped")

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self._connections.add(websocket)
        websocket_connections.inc()
        logger.info("WebSocket client connected (total: %d)", len(self._connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        self._connections.discard(websocket)
        websocket_connections.dec()
        logger.info("WebSocket client disconnected (total: %d)", len(self._connections))

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Send an event to all connected WebSocket clients."""
        if not self._connections:
            return

        message = json.dumps({"type": event_type, "data": data})
        dead = set()
        for ws in self._connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        self._connections -= dead

    async def _relay_events(self) -> None:
        """Background task: relay Redis pub/sub events to WebSocket clients."""
        try:
            async for event_type, data in self.event_bus.subscribe():
                await self.broadcast(event_type, data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Event relay error: %s", e)
