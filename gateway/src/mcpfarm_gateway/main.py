"""FastAPI application factory and lifespan."""

import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from mcpfarm_gateway.api.auth import MCPAuthMiddleware
from mcpfarm_gateway.api.health import router as health_router
from mcpfarm_gateway.api.invocations import router as invocations_router
from mcpfarm_gateway.api.keys import router as keys_router
from mcpfarm_gateway.api.servers import router as servers_router
from mcpfarm_gateway.api.tools import router as tools_router
from mcpfarm_gateway.config import settings
from mcpfarm_gateway.containers.manager import DockerContainerManager
from mcpfarm_gateway.containers.watcher import ServerWatcher
from mcpfarm_gateway.mcp.gateway_server import gateway_mcp
from mcpfarm_gateway.mcp.proxy_manager import ProxyManager
from mcpfarm_gateway.mcp.tool_registry import ToolRegistry
from mcpfarm_gateway.observability import ObservabilityMiddleware, metrics_endpoint, setup_logging
from mcpfarm_gateway.realtime.redis_pubsub import EventBus
from mcpfarm_gateway.realtime.ws_hub import WebSocketHub

setup_logging(
    log_level=settings.gateway_log_level,
    log_format=settings.gateway_log_format,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────
    logger.info("MCPFarm Gateway starting up...")

    # Database engine (lazy - created on first use via get_session)
    from mcpfarm_gateway.db import engine
    from mcpfarm_gateway.db.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")

    # Redis
    redis_client = aioredis.from_url(settings.redis_url, decode_responses=False)
    await redis_client.ping()  # type: ignore[misc]
    logger.info("Redis connected")

    # Core services
    container_manager = DockerContainerManager(
        network_internal=settings.docker_network_internal,
    )
    proxy_manager = ProxyManager(gateway_mcp)
    tool_registry = ToolRegistry(redis_client)
    event_bus = EventBus(redis_client)
    ws_hub = WebSocketHub(event_bus)

    # Store on app.state for dependency injection
    app.state.container_manager = container_manager
    app.state.proxy_manager = proxy_manager
    app.state.tool_registry = tool_registry
    app.state.event_bus = event_bus
    app.state.ws_hub = ws_hub
    app.state.redis = redis_client

    # Start background services
    await ws_hub.start()

    watcher = ServerWatcher(
        container_mgr=container_manager,
        proxy_mgr=proxy_manager,
        tool_registry=tool_registry,
        event_bus=event_bus,
    )
    await watcher.start()
    app.state.watcher = watcher

    logger.info("MCPFarm Gateway ready")

    yield

    # ── Shutdown ─────────────────────────────────────────────
    logger.info("MCPFarm Gateway shutting down...")
    await watcher.stop()
    await ws_hub.stop()
    await redis_client.close()
    await engine.dispose()
    logger.info("MCPFarm Gateway shutdown complete")


def create_app() -> FastAPI:
    # Build the MCP Starlette app first so we can chain its lifespan
    mcp_app = gateway_mcp.http_app(path="/", stateless_http=True)

    @asynccontextmanager
    async def combined_lifespan(app: FastAPI):
        # Run FastMCP lifespan (initializes session manager task group)
        async with mcp_app.lifespan(mcp_app), lifespan(app):
            yield

    app = FastAPI(
        title="MCPFarm.ai Gateway",
        version="0.1.0",
        lifespan=combined_lifespan,
    )

    # Observability middleware (outermost - wraps everything including CORS)
    app.add_middleware(ObservabilityMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # REST API routes
    app.include_router(health_router)

    # Prometheus metrics endpoint (unauthenticated)
    if settings.enable_metrics:
        app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], include_in_schema=False)
    app.include_router(keys_router, prefix="/api")
    app.include_router(servers_router, prefix="/api")
    app.include_router(tools_router, prefix="/api")
    app.include_router(invocations_router, prefix="/api")

    # MCP Streamable HTTP endpoint (wrapped with auth middleware)
    app.mount("/mcp", MCPAuthMiddleware(mcp_app, app))

    # WebSocket endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        ws_hub: WebSocketHub = app.state.ws_hub
        await ws_hub.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await ws_hub.disconnect(websocket)

    return app


app = create_app()
