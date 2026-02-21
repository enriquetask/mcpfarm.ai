"""Tests for health endpoint.

These tests use a lightweight test app that doesn't require database/redis
connections - just the basic FastAPI routing.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from mcpfarm_gateway.api.health import router as health_router
from fastapi import FastAPI

# Create a minimal test app with just the health router
test_app = FastAPI()
test_app.include_router(health_router)


@pytest.mark.anyio
async def test_health_endpoint():
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "mcpfarm-gateway"
    assert data["version"] == "0.1.0"
