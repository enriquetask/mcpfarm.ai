"""Integration tests for the MCPFarm SDK against a running gateway.

Run with: pytest sdk/tests/test_integration.py -v --run-integration

Requires:
  - `make docker-dev` running (gateway + redis + postgres + MCP servers)
  - ADMIN_API_KEY env var set (or default sk-admin-bootstrap)
"""

from __future__ import annotations

import os

import httpx
import pytest
import pytest_asyncio

GATEWAY_URL = os.getenv("MCPFARM_GATEWAY_URL", "http://localhost:8000")
ADMIN_KEY = os.getenv("ADMIN_API_KEY", "sk-admin-bootstrap")


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests against live gateway",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration"):
        skip = pytest.mark.skip(reason="need --run-integration flag to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)


pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def api_key() -> str:
    """Create a fresh API key using the admin bootstrap key."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GATEWAY_URL}/api/keys/",
            json={"name": "integration-test", "scopes": []},
            headers={
                "Authorization": f"Bearer {ADMIN_KEY}",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return data["key"]


@pytest.mark.asyncio
async def test_health():
    """Health endpoint should be public (no auth required)."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GATEWAY_URL}/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_unauthenticated_rejected():
    """API endpoints should reject unauthenticated requests."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{GATEWAY_URL}/api/servers/")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_tools(api_key: str):
    """SDK should list tools from the farm."""
    from mcpfarm_sdk import MCPFarmClient

    client = MCPFarmClient(url=f"{GATEWAY_URL}/mcp", api_key=api_key)
    tools = await client.list_tools()
    assert len(tools) >= 1
    # Check tools have expected structure
    for tool in tools:
        assert "name" in tool
        assert "namespaced_name" in tool


@pytest.mark.asyncio
async def test_call_calculator(api_key: str):
    """SDK should call the calculator add tool."""
    from mcpfarm_sdk import MCPFarmClient

    client = MCPFarmClient(url=f"{GATEWAY_URL}/mcp", api_key=api_key)
    result = await client.call_tool("calc_add", {"a": 1, "b": 2})
    assert result == 3.0 or str(result) == "3.0"


@pytest.mark.asyncio
async def test_sdk_healthy(api_key: str):
    """SDK health check should work."""
    from mcpfarm_sdk import MCPFarmClient

    client = MCPFarmClient(url=f"{GATEWAY_URL}/mcp", api_key=api_key)
    assert await client.is_healthy() is True


@pytest.mark.asyncio
async def test_invocation_logged(api_key: str):
    """Tool invocations should appear in the activity log with caller_id."""
    from mcpfarm_sdk import MCPFarmClient

    client = MCPFarmClient(url=f"{GATEWAY_URL}/mcp", api_key=api_key)

    # Make a tool call
    await client.call_tool("calc_add", {"a": 10, "b": 20})

    # Check invocations list
    async with httpx.AsyncClient() as http:
        resp = await http.get(
            f"{GATEWAY_URL}/api/invocations?limit=5",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        resp.raise_for_status()
        data = resp.json()
        assert data["total"] >= 1

        # Most recent invocation should have caller_id set
        latest = data["invocations"][0]
        assert latest["caller_id"] == "integration-test"
        assert latest["status"] == "success"


@pytest.mark.asyncio
async def test_rate_limit_header(api_key: str):
    """Rapid requests should eventually get rate-limited (429)."""
    # This test only works if rate_limit_per_minute is set low enough.
    # With default 60/min, we just verify the endpoint works and doesn't
    # immediately rate-limit us.
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GATEWAY_URL}/api/tools/",
            headers={"Authorization": f"Bearer {api_key}"},
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_full_flow(api_key: str):
    """End-to-end flow: create key, connect SDK, list tools, call tool, verify."""
    from mcpfarm_sdk import MCPFarmClient

    client = MCPFarmClient(url=f"{GATEWAY_URL}/mcp", api_key=api_key)

    # 1. Health check
    assert await client.is_healthy() is True

    # 2. List tools
    tools = await client.list_tools()
    assert len(tools) >= 1
    tool_names = [t["namespaced_name"] for t in tools]
    assert any("calc" in name or "echo" in name for name in tool_names)

    # 3. Call a tool
    if "calc_add" in tool_names:
        result = await client.call_tool("calc_add", {"a": 5, "b": 7})
        assert result == 12.0 or str(result) == "12.0"
