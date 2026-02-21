"""Tests for MCPFarm SDK client."""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import pytest

from mcpfarm_sdk import BearerAuth, MCPFarmClient


def test_client_init_default():
    client = MCPFarmClient()
    assert client.url == "http://localhost:8000/mcp"
    assert client.api_key is None


def test_client_init_custom():
    client = MCPFarmClient(url="http://farm:8000/mcp", api_key="sk-test")
    assert client.url == "http://farm:8000/mcp"
    assert client.api_key == "sk-test"
    assert client._headers["Authorization"] == "Bearer sk-test"


def test_as_mcp_config():
    client = MCPFarmClient(url="http://farm:8000/mcp")
    config = client.as_mcp_config()
    assert config["mcpfarm"]["url"] == "http://farm:8000/mcp"
    assert config["mcpfarm"]["transport"] == "streamable_http"


def test_as_mcp_config_with_auth():
    client = MCPFarmClient(url="http://farm:8000/mcp", api_key="sk-farm-abc123")
    config = client.as_mcp_config()
    assert config["mcpfarm"]["headers"]["Authorization"] == "Bearer sk-farm-abc123"


def test_bearer_auth():
    auth = BearerAuth("sk-farm-test123")
    request = httpx.Request("GET", "http://example.com")
    flow = auth.auth_flow(request)
    modified_request = next(flow)
    assert modified_request.headers["Authorization"] == "Bearer sk-farm-test123"


@pytest.mark.asyncio
async def test_call_tool():
    client = MCPFarmClient(url="http://farm:8000/mcp", api_key="sk-test")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "result": 3.0,
        "duration_ms": 5,
        "invocation_id": "abc-123",
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await client.call_tool("calc_add", {"a": 1, "b": 2})
        assert result == 3.0

        mock_client.request.assert_called_once()
        call_args = mock_client.request.call_args
        assert call_args[0] == ("POST", "http://farm:8000/api/tools/call")
        assert call_args[1]["json"] == {"tool_name": "calc_add", "arguments": {"a": 1, "b": 2}}


@pytest.mark.asyncio
async def test_call_tool_retry_on_server_error():
    """Test that 500 errors trigger retries."""
    client = MCPFarmClient(url="http://farm:8000/mcp", api_key="sk-test")

    error_response = MagicMock()
    error_response.status_code = 500
    error_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("Server Error", request=MagicMock(), response=error_response)
    )

    success_response = MagicMock()
    success_response.status_code = 200
    success_response.json.return_value = {"result": "ok"}
    success_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls, \
         patch("asyncio.sleep", new_callable=AsyncMock):
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=[error_response, success_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await client.call_tool("test_tool", {})
        assert result == "ok"
        assert mock_client.request.call_count == 2


@pytest.mark.asyncio
async def test_call_tool_no_retry_on_client_error():
    """Test that 4xx errors are NOT retried."""
    client = MCPFarmClient(url="http://farm:8000/mcp", api_key="sk-test")

    error_response = MagicMock()
    error_response.status_code = 404
    error_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("Not Found", request=MagicMock(), response=error_response)
    )

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=error_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            await client.call_tool("nonexistent", {})

        assert mock_client.request.call_count == 1


@pytest.mark.asyncio
async def test_list_tools():
    client = MCPFarmClient(url="http://farm:8000/mcp", api_key="sk-test")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "tools": [
            {"name": "add", "namespaced_name": "calc_add", "description": "Add numbers"},
        ],
        "total": 1,
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        tools = await client.list_tools()
        assert len(tools) == 1
        assert tools[0]["namespaced_name"] == "calc_add"


@pytest.mark.asyncio
async def test_is_healthy():
    client = MCPFarmClient(url="http://farm:8000/mcp")

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        assert await client.is_healthy() is True


@pytest.mark.asyncio
async def test_is_healthy_down():
    client = MCPFarmClient(url="http://farm:8000/mcp")

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        assert await client.is_healthy() is False
