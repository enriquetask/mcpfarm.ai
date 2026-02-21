"""Health check and stats endpoints."""

import logging

from fastapi import APIRouter, Depends, Request

from mcpfarm_gateway.api.deps import get_invocation_repo, get_server_repo, get_tool_registry
from mcpfarm_gateway.api.schemas import StatsResponse
from mcpfarm_gateway.db.repositories import InvocationRepository, ServerRepository
from mcpfarm_gateway.mcp.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": "mcpfarm-gateway", "version": "0.1.0"}


@router.get("/health/live")
async def health_live():
    """Liveness probe - is the process running and accepting requests."""
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready(request: Request):
    """Deep readiness probe - checks DB, Redis, and server count."""
    checks: dict = {}
    overall = True

    # Check database
    try:
        from sqlalchemy import text

        from mcpfarm_gateway.db import engine

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        logger.warning("Readiness check: database unhealthy: %s", e)
        checks["database"] = f"error: {e}"
        overall = False

    # Check Redis
    try:
        redis = request.app.state.redis
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        logger.warning("Readiness check: redis unhealthy: %s", e)
        checks["redis"] = f"error: {e}"
        overall = False

    # Check server count
    try:
        tool_reg: ToolRegistry = request.app.state.tool_registry
        tool_count = await tool_reg.count()
        checks["tools_available"] = tool_count
    except Exception as e:
        checks["tools_available"] = f"error: {e}"

    status_code = 200 if overall else 503
    from starlette.responses import JSONResponse

    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if overall else "degraded", "checks": checks},
    )


@router.get("/api/stats", response_model=StatsResponse)
async def stats(
    server_repo: ServerRepository = Depends(get_server_repo),
    tool_reg: ToolRegistry = Depends(get_tool_registry),
    inv_repo: InvocationRepository = Depends(get_invocation_repo),
):
    servers = await server_repo.list_all()
    healthy = sum(1 for s in servers if s.status == "HEALTHY")
    tool_count = await tool_reg.count()
    inv_count = await inv_repo.count()
    return StatsResponse(
        total_servers=len(servers),
        healthy_servers=healthy,
        total_tools=tool_count,
        total_invocations=inv_count,
    )
