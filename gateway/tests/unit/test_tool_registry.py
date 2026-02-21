"""Tests for tool registry (mocked Redis)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from mcpfarm_gateway.mcp.tool_registry import ToolRegistry


class MockPipeline:
    """Mock Redis pipeline that supports async context manager."""

    def __init__(self):
        self.hset = AsyncMock()
        self.hdel = AsyncMock()
        self.sadd = AsyncMock()
        self.delete = AsyncMock()
        self.execute = AsyncMock(return_value=[])

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.pipeline = MagicMock(return_value=MockPipeline())
    redis.hlen = AsyncMock(return_value=0)
    redis.hgetall = AsyncMock(return_value={})
    redis.hget = AsyncMock(return_value=None)
    redis.delete = AsyncMock()
    redis.smembers = AsyncMock(return_value=set())
    return redis


@pytest.mark.anyio
async def test_register_tools(mock_redis):
    reg = ToolRegistry(mock_redis)
    tools = [
        {"name": "echo", "description": "Echo a message", "inputSchema": {}},
        {"name": "reverse", "description": "Reverse text", "inputSchema": {}},
    ]
    await reg.register_tools("server-1", "test", tools)
    assert "test_echo" in reg._cache
    assert "test_reverse" in reg._cache
    assert reg._cache["test_echo"]["namespace"] == "test"


@pytest.mark.anyio
async def test_unregister_server(mock_redis):
    reg = ToolRegistry(mock_redis)
    reg._cache["test_echo"] = {"name": "echo", "namespaced_name": "test_echo"}
    mock_redis.smembers.return_value = {b"test_echo"}
    await reg.unregister_server("server-1")
    assert "test_echo" not in reg._cache


@pytest.mark.anyio
async def test_list_all_from_cache(mock_redis):
    reg = ToolRegistry(mock_redis)
    reg._cache["test_echo"] = {"name": "echo", "namespaced_name": "test_echo"}
    result = await reg.list_all()
    assert len(result) == 1
    assert result[0]["name"] == "echo"


@pytest.mark.anyio
async def test_count(mock_redis):
    mock_redis.hlen.return_value = 5
    reg = ToolRegistry(mock_redis)
    assert await reg.count() == 5
