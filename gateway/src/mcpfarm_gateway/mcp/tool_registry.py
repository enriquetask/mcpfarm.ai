"""Aggregated tool cache and registry.

Maintains a fast in-memory + Redis cache of all available tools across
all mounted MCP servers, synced to the database.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

REDIS_TOOLS_KEY = "mcpfarm:tools"
REDIS_TOOLS_BY_SERVER_KEY = "mcpfarm:tools:server:{server_id}"


class ToolRegistry:
    """Fast tool lookup backed by Redis and synced to DB."""

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self._cache: dict[str, dict[str, Any]] = {}  # namespaced_name -> tool info

    async def register_tools(
        self, server_id: str, namespace: str, tools: list[dict[str, Any]]
    ) -> None:
        """Register discovered tools for a server in cache and Redis."""
        server_key = REDIS_TOOLS_BY_SERVER_KEY.format(server_id=server_id)

        # Clear old tools for this server
        await self.redis.delete(server_key)

        async with self.redis.pipeline() as pipe:
            tool_names = []
            for tool in tools:
                namespaced_name = f"{namespace}_{tool['name']}"
                tool_info = {
                    "name": tool["name"],
                    "namespaced_name": namespaced_name,
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("inputSchema", {}),
                    "server_id": server_id,
                    "namespace": namespace,
                    "is_available": True,
                }
                self._cache[namespaced_name] = tool_info
                await pipe.hset(REDIS_TOOLS_KEY, namespaced_name, json.dumps(tool_info))
                tool_names.append(namespaced_name)

            if tool_names:
                await pipe.sadd(server_key, *tool_names)
            await pipe.execute()

        logger.info("Registered %d tools for server %s (namespace=%s)", len(tools), server_id, namespace)

    async def unregister_server(self, server_id: str) -> None:
        """Remove all cached tools for a server."""
        server_key = REDIS_TOOLS_BY_SERVER_KEY.format(server_id=server_id)
        tool_names = await self.redis.smembers(server_key)

        if tool_names:
            async with self.redis.pipeline() as pipe:
                for name in tool_names:
                    name_str = name.decode() if isinstance(name, bytes) else name
                    self._cache.pop(name_str, None)
                    await pipe.hdel(REDIS_TOOLS_KEY, name_str)
                await pipe.delete(server_key)
                await pipe.execute()

        logger.info("Unregistered tools for server %s", server_id)

    async def list_all(self) -> list[dict[str, Any]]:
        """List all available tools."""
        if self._cache:
            return list(self._cache.values())

        # Rebuild from Redis
        all_tools = await self.redis.hgetall(REDIS_TOOLS_KEY)
        result = []
        for name, data in all_tools.items():
            tool_info = json.loads(data)
            name_str = name.decode() if isinstance(name, bytes) else name
            self._cache[name_str] = tool_info
            result.append(tool_info)
        return result

    async def get_tool(self, namespaced_name: str) -> dict[str, Any] | None:
        """Get a single tool by its namespaced name."""
        if namespaced_name in self._cache:
            return self._cache[namespaced_name]

        data = await self.redis.hget(REDIS_TOOLS_KEY, namespaced_name)
        if data:
            tool_info = json.loads(data)
            self._cache[namespaced_name] = tool_info
            return tool_info
        return None

    async def count(self) -> int:
        """Count total available tools."""
        return await self.redis.hlen(REDIS_TOOLS_KEY)

    async def clear(self) -> None:
        """Clear all cached tools."""
        self._cache.clear()
        await self.redis.delete(REDIS_TOOLS_KEY)
