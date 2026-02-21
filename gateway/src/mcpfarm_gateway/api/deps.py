"""FastAPI dependency injection helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from mcpfarm_gateway.db import get_session
from mcpfarm_gateway.db.models import APIKey
from mcpfarm_gateway.db.repositories import APIKeyRepository, InvocationRepository, ServerRepository, ToolRepository

if TYPE_CHECKING:
    from mcpfarm_gateway.containers.manager import DockerContainerManager
    from mcpfarm_gateway.mcp.proxy_manager import ProxyManager
    from mcpfarm_gateway.mcp.tool_registry import ToolRegistry
    from mcpfarm_gateway.realtime.redis_pubsub import EventBus


def get_container_manager(request: Request) -> "DockerContainerManager":
    return request.app.state.container_manager


def get_proxy_manager(request: Request) -> "ProxyManager":
    return request.app.state.proxy_manager


def get_tool_registry(request: Request) -> "ToolRegistry":
    return request.app.state.tool_registry


def get_event_bus(request: Request) -> "EventBus":
    return request.app.state.event_bus


def get_server_repo(
    session: AsyncSession = Depends(get_session),
) -> ServerRepository:
    return ServerRepository(session)


def get_tool_repo(
    session: AsyncSession = Depends(get_session),
) -> ToolRepository:
    return ToolRepository(session)


def get_invocation_repo(
    session: AsyncSession = Depends(get_session),
) -> InvocationRepository:
    return InvocationRepository(session)


def get_api_key_repo(
    session: AsyncSession = Depends(get_session),
) -> APIKeyRepository:
    return APIKeyRepository(session)


async def get_current_api_key(
    request: Request,
    api_key_repo: APIKeyRepository = Depends(get_api_key_repo),
) -> APIKey:
    """Validate the Bearer token and return the APIKey record."""
    from mcpfarm_gateway.api.auth import verify_api_key
    return await verify_api_key(request, api_key_repo)
