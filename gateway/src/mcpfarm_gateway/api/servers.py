"""MCP server management API endpoints."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException

from mcpfarm_gateway.api.deps import (
    get_container_manager,
    get_current_api_key,
    get_event_bus,
    get_proxy_manager,
    get_server_repo,
    get_tool_registry,
    get_tool_repo,
)
from mcpfarm_gateway.api.schemas import (
    ServerCreate,
    ServerListResponse,
    ServerResponse,
    ServerUpdate,
)
from mcpfarm_gateway.containers.health import wait_for_ready

if TYPE_CHECKING:
    import uuid

    from mcpfarm_gateway.containers.manager import DockerContainerManager
    from mcpfarm_gateway.db.models import APIKey
    from mcpfarm_gateway.db.repositories import ServerRepository, ToolRepository
    from mcpfarm_gateway.mcp.proxy_manager import ProxyManager
    from mcpfarm_gateway.mcp.tool_registry import ToolRegistry
    from mcpfarm_gateway.realtime.redis_pubsub import EventBus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/servers", tags=["servers"])


def _server_to_response(server, tool_count: int = 0) -> ServerResponse:
    return ServerResponse(
        id=server.id,
        name=server.name,
        namespace=server.namespace,
        image=server.image,
        port=server.port,
        env_vars=server.env_vars,
        status=server.status,
        container_id=server.container_id,
        auto_restart=server.auto_restart,
        tool_count=tool_count,
        created_at=server.created_at,
        updated_at=server.updated_at,
    )


@router.get("/", response_model=ServerListResponse)
async def list_servers(
    _caller: APIKey = Depends(get_current_api_key),
    repo: ServerRepository = Depends(get_server_repo),
):
    servers = await repo.list_all()
    items = [_server_to_response(s, tool_count=len(s.tools)) for s in servers]
    return ServerListResponse(servers=items, total=len(items))


@router.post("/", response_model=ServerResponse, status_code=201)
async def create_server(
    body: ServerCreate,
    _caller: APIKey = Depends(get_current_api_key),
    repo: ServerRepository = Depends(get_server_repo),
):
    existing = await repo.get_by_namespace(body.namespace)
    if existing:
        raise HTTPException(status_code=409, detail=f"Namespace '{body.namespace}' already exists")

    server = await repo.create(
        name=body.name,
        namespace=body.namespace,
        image=body.image,
        port=body.port,
        env_vars=body.env_vars,
        auto_restart=body.auto_restart,
    )
    return _server_to_response(server)


@router.get("/{server_id}", response_model=ServerResponse)
async def get_server(
    server_id: uuid.UUID,
    _caller: APIKey = Depends(get_current_api_key),
    repo: ServerRepository = Depends(get_server_repo),
):
    server = await repo.get_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return _server_to_response(server, tool_count=len(server.tools))


@router.patch("/{server_id}", response_model=ServerResponse)
async def update_server(
    server_id: uuid.UUID,
    body: ServerUpdate,
    _caller: APIKey = Depends(get_current_api_key),
    repo: ServerRepository = Depends(get_server_repo),
):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    server = await repo.update(server_id, **updates)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return _server_to_response(server, tool_count=len(server.tools))


@router.delete("/{server_id}", status_code=204)
async def delete_server(
    server_id: uuid.UUID,
    _caller: APIKey = Depends(get_current_api_key),
    repo: ServerRepository = Depends(get_server_repo),
    container_mgr: DockerContainerManager = Depends(get_container_manager),
    proxy_mgr: ProxyManager = Depends(get_proxy_manager),
    tool_reg: ToolRegistry = Depends(get_tool_registry),
    event_bus: EventBus = Depends(get_event_bus),
):
    server = await repo.get_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    # Stop and remove container if running
    if server.container_id:
        await container_mgr.remove(server.container_id)

    # Unmount from gateway
    await proxy_mgr.unmount(server.namespace)
    await tool_reg.unregister_server(str(server.id))

    await repo.delete(server_id)
    await event_bus.publish("server.deleted", {"server_id": str(server_id), "name": server.name})


@router.post("/{server_id}/start", response_model=ServerResponse)
async def start_server(
    server_id: uuid.UUID,
    _caller: APIKey = Depends(get_current_api_key),
    repo: ServerRepository = Depends(get_server_repo),
    tool_repo: ToolRepository = Depends(get_tool_repo),
    container_mgr: DockerContainerManager = Depends(get_container_manager),
    proxy_mgr: ProxyManager = Depends(get_proxy_manager),
    tool_reg: ToolRegistry = Depends(get_tool_registry),
    event_bus: EventBus = Depends(get_event_bus),
):
    server = await repo.get_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    if server.status == "HEALTHY":
        raise HTTPException(status_code=409, detail="Server is already running")

    # Start container
    container_id = await container_mgr.create_and_start(
        image=server.image,
        name=server.name,
        namespace=server.namespace,
        server_id=str(server.id),
        port=server.port,
        env_vars=server.env_vars,
    )

    # Update status
    server = await repo.update_status(server_id, "STARTING", container_id)
    assert server is not None

    # Get container IP and wait for readiness before mounting proxy
    ip = await container_mgr.get_ip(container_id)
    if ip:
        ready = await wait_for_ready(ip, server.port, retries=15, interval=1.0)
        if ready:
            mcp_url = f"http://{ip}:{server.port}/mcp"
            try:
                tools = await proxy_mgr.mount(server.namespace, mcp_url)
                await tool_reg.register_tools(str(server.id), server.namespace, tools)
                await tool_repo.sync_tools(server.id, server.namespace, tools)
                server = await repo.update_status(server_id, "HEALTHY")
                assert server is not None
            except Exception as e:
                logger.error("Failed to mount proxy for %s: %s", server.namespace, e)  # type: ignore[union-attr]
                server = await repo.update_status(server_id, "DEGRADED")
                assert server is not None
        else:
            logger.warning("Container %s not ready in time", container_id[:12])
            server = await repo.update_status(server_id, "DEGRADED")
            assert server is not None
    else:
        logger.warning("Could not get IP for container %s", container_id[:12])
        server = await repo.update_status(server_id, "DEGRADED")
        assert server is not None

    await event_bus.publish(
        "server.started",
        {
            "server_id": str(server_id),
            "name": server.name,
            "status": server.status,
        },
    )

    return _server_to_response(server, tool_count=len(server.tools))


@router.post("/{server_id}/stop", response_model=ServerResponse)
async def stop_server(
    server_id: uuid.UUID,
    _caller: APIKey = Depends(get_current_api_key),
    repo: ServerRepository = Depends(get_server_repo),
    tool_repo: ToolRepository = Depends(get_tool_repo),
    container_mgr: DockerContainerManager = Depends(get_container_manager),
    proxy_mgr: ProxyManager = Depends(get_proxy_manager),
    tool_reg: ToolRegistry = Depends(get_tool_registry),
    event_bus: EventBus = Depends(get_event_bus),
):
    server = await repo.get_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    if server.container_id:
        await container_mgr.stop(server.container_id)
        await container_mgr.remove(server.container_id)

    await proxy_mgr.unmount(server.namespace)
    await tool_reg.unregister_server(str(server.id))
    await tool_repo.mark_unavailable(server.id)

    server = await repo.update_status(server_id, "STOPPED", container_id=None)
    assert server is not None

    await event_bus.publish(
        "server.stopped",
        {
            "server_id": str(server_id),
            "name": server.name,
        },
    )

    return _server_to_response(server)


@router.post("/{server_id}/restart", response_model=ServerResponse)
async def restart_server(
    server_id: uuid.UUID,
    _caller: APIKey = Depends(get_current_api_key),
    repo: ServerRepository = Depends(get_server_repo),
    tool_repo: ToolRepository = Depends(get_tool_repo),
    container_mgr: DockerContainerManager = Depends(get_container_manager),
    proxy_mgr: ProxyManager = Depends(get_proxy_manager),
    tool_reg: ToolRegistry = Depends(get_tool_registry),
    event_bus: EventBus = Depends(get_event_bus),
):
    # Stop first
    server = await repo.get_by_id(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    if server.container_id:
        await container_mgr.stop(server.container_id)
        await container_mgr.remove(server.container_id)
        await proxy_mgr.unmount(server.namespace)
        await tool_reg.unregister_server(str(server.id))

    # Then start
    container_id = await container_mgr.create_and_start(
        image=server.image,
        name=server.name,
        namespace=server.namespace,
        server_id=str(server.id),
        port=server.port,
        env_vars=server.env_vars,
    )

    server = await repo.update_status(server_id, "STARTING", container_id)
    assert server is not None

    ip = await container_mgr.get_ip(container_id)
    if ip:
        ready = await wait_for_ready(ip, server.port, retries=15, interval=1.0)
        if ready:
            mcp_url = f"http://{ip}:{server.port}/mcp"
            try:
                tools = await proxy_mgr.mount(server.namespace, mcp_url)
                await tool_reg.register_tools(str(server.id), server.namespace, tools)
                await tool_repo.sync_tools(server.id, server.namespace, tools)
                server = await repo.update_status(server_id, "HEALTHY")
                assert server is not None
            except Exception as e:
                logger.error("Failed to mount proxy for %s: %s", server.namespace, e)  # type: ignore[union-attr]
                server = await repo.update_status(server_id, "DEGRADED")
                assert server is not None

    await event_bus.publish(
        "server.restarted",
        {
            "server_id": str(server_id),
            "name": server.name,
            "status": server.status,
        },
    )

    return _server_to_response(server, tool_count=len(server.tools))
