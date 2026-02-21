"""MCPFarm SDK client for LangGraph integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_RETRY_DELAYS = [1.0, 2.0, 4.0]


class MCPFarmClient:
    """Client for connecting LangGraph agents to MCPFarm.ai."""

    def __init__(self, url: str = "http://localhost:8000/mcp", api_key: str | None = None):
        self.url = url
        self.base_url = url.rsplit("/mcp", 1)[0]
        self.api_key = api_key
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> httpx.Response:
        """Make an HTTP request with exponential backoff retry."""
        kwargs.setdefault("headers", {}).update(self._headers)
        last_exc: Exception | None = None

        for attempt, delay in enumerate([0.0] + _RETRY_DELAYS):
            if delay > 0:
                logger.debug("Retry attempt %d after %.1fs", attempt, delay)
                await asyncio.sleep(delay)
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.request(method, url, **kwargs)
                    resp.raise_for_status()
                    return resp
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_exc = exc
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 500:
                    raise
                logger.warning("Request to %s failed (attempt %d): %s", url, attempt + 1, exc)

        raise last_exc  # type: ignore[misc]

    async def is_healthy(self) -> bool:
        """Check if the farm gateway is healthy."""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
            except httpx.HTTPError:
                return False

    async def list_tools(self) -> list[dict[str, Any]]:
        """List all available tools from the farm."""
        resp = await self._request_with_retry("GET", f"{self.base_url}/api/tools/")
        return resp.json().get("tools", [])

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Call a tool by name with the given arguments.

        Returns the result value from the tool invocation.
        """
        resp = await self._request_with_retry(
            "POST",
            f"{self.base_url}/api/tools/call",
            json={"tool_name": name, "arguments": arguments or {}},
        )
        data = resp.json()
        return data.get("result")

    async def get_langchain_tools(self) -> list:
        """Get LangChain-compatible tools via langchain-mcp-adapters.

        Requires the `langchain` extra: pip install mcpfarm-sdk[langchain]
        Uses the MCP Streamable HTTP endpoint with Bearer auth.
        """
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
        except ImportError:
            raise ImportError(
                "langchain-mcp-adapters is required. "
                "Install with: pip install mcpfarm-sdk[langchain]"
            )

        headers = dict(self._headers) if self._headers else {}
        config = {
            "mcpfarm": {
                "url": self.url,
                "transport": "streamable_http",
                "headers": headers,
            }
        }
        async with MultiServerMCPClient(config) as mcp_client:
            return mcp_client.get_tools()

    async def create_tools(self) -> list:
        """Create LangChain StructuredTool wrappers for all farm tools.

        Async convenience method that wraps the REST API
        (no langchain-mcp-adapters needed). Returns a list of LangChain tools.
        Requires langchain-core to be installed.
        """
        try:
            from langchain_core.tools import StructuredTool
        except ImportError:
            raise ImportError(
                "langchain-core is required. "
                "Install with: pip install langchain-core"
            )

        tools_data = await self.list_tools()

        lc_tools = []
        for tool_info in tools_data:
            namespaced_name = tool_info["namespaced_name"]
            description = tool_info.get("description") or namespaced_name

            def _make_func(tool_name: str):
                async def _call(**kwargs: Any) -> Any:
                    return await self.call_tool(tool_name, kwargs)
                return _call

            lc_tools.append(
                StructuredTool.from_function(
                    coroutine=_make_func(namespaced_name),
                    name=namespaced_name,
                    description=description,
                )
            )

        return lc_tools

    def as_mcp_config(self) -> dict[str, Any]:
        """Return MCP client configuration dict for MultiServerMCPClient."""
        config: dict[str, Any] = {
            "mcpfarm": {
                "url": self.url,
                "transport": "streamable_http",
            }
        }
        if self._headers:
            config["mcpfarm"]["headers"] = dict(self._headers)
        return config
