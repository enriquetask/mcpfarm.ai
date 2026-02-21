"""ProxyProvider lifecycle management.

Dynamically mounts/unmounts backend MCP servers onto the gateway FastMCP instance.
"""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages dynamic proxy mounting of backend MCP servers."""

    def __init__(self, gateway: FastMCP):
        self.gateway = gateway
        self._mounted: dict[str, FastMCP] = {}  # namespace -> proxy server

    async def mount(self, namespace: str, url: str) -> list[dict[str, Any]]:
        """Mount a backend MCP server onto the gateway.

        Creates a proxy FastMCP server for the backend URL and mounts it
        with the given namespace. Returns the list of discovered tools.
        """
        if namespace in self._mounted:
            logger.warning("Namespace %s already mounted, unmounting first", namespace)
            await self.unmount(namespace)

        logger.info("Mounting backend MCP server: namespace=%s url=%s", namespace, url)

        # Create a proxy server for the backend
        proxy = FastMCP.as_proxy(url)
        self.gateway.mount(proxy, namespace=namespace)
        self._mounted[namespace] = proxy

        # Discover tools from the proxy
        tools = await self._discover_tools(proxy, namespace)
        logger.info("Mounted %s with %d tools", namespace, len(tools))
        return tools

    async def unmount(self, namespace: str) -> None:
        """Unmount a backend MCP server from the gateway."""
        if namespace not in self._mounted:
            logger.warning("Namespace %s not mounted", namespace)
            return

        # FastMCP doesn't have a direct unmount, so we need to rebuild
        # For now, we track state and the gateway will be rebuilt on restart
        del self._mounted[namespace]
        logger.info("Unmounted namespace %s", namespace)

    async def _discover_tools(self, proxy: FastMCP, namespace: str) -> list[dict[str, Any]]:
        """Discover tools from a mounted proxy server."""
        try:
            tools = await proxy.list_tools()
            return [
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "inputSchema": tool.parameters if hasattr(tool, "parameters") else {},
                }
                for tool in tools
            ]
        except Exception as e:
            logger.error("Failed to discover tools for %s: %s", namespace, e)
            return []

    @property
    def mounted_namespaces(self) -> list[str]:
        return list(self._mounted.keys())

    def is_mounted(self, namespace: str) -> bool:
        return namespace in self._mounted
