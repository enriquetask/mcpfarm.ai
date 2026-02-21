"""Tool invocation API endpoints."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException

from mcpfarm_gateway.api.deps import (
    get_current_api_key,
    get_event_bus,
    get_invocation_repo,
    get_tool_registry,
    get_tool_repo,
)
from mcpfarm_gateway.db.models import APIKey
from mcpfarm_gateway.api.schemas import (
    InvocationListResponse,
    InvocationResponse,
    ToolCallRequest,
    ToolCallResponse,
)
from mcpfarm_gateway.db.repositories import InvocationRepository, ToolRepository
from mcpfarm_gateway.mcp.gateway_server import gateway_mcp
from mcpfarm_gateway.mcp.tool_registry import ToolRegistry
from mcpfarm_gateway.realtime.redis_pubsub import EventBus

from mcpfarm_gateway.observability.metrics import (
    tool_invocations_total,
    tool_invocation_duration_seconds,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["invocations"])


@router.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(
    body: ToolCallRequest,
    caller: APIKey = Depends(get_current_api_key),
    tool_reg: ToolRegistry = Depends(get_tool_registry),
    tool_repo: ToolRepository = Depends(get_tool_repo),
    inv_repo: InvocationRepository = Depends(get_invocation_repo),
    event_bus: EventBus = Depends(get_event_bus),
):
    """Call a tool through the gateway and log the invocation."""
    tool_info = await tool_reg.get_tool(body.tool_name)
    if not tool_info:
        raise HTTPException(status_code=404, detail=f"Tool '{body.tool_name}' not found")

    server_id = uuid.UUID(tool_info["server_id"])

    db_tool = await tool_repo.get_by_namespaced_name(body.tool_name)
    if not db_tool:
        raise HTTPException(status_code=404, detail=f"Tool '{body.tool_name}' not in database")

    inv = await inv_repo.create(
        tool_id=db_tool.id,
        server_id=server_id,
        input_data=body.arguments,
        caller_id=caller.name,
    )

    # Derive namespace from namespaced tool name (e.g. "calc_add" -> "calc")
    server_namespace = body.tool_name.split("_", 1)[0] if "_" in body.tool_name else "unknown"

    start = time.monotonic()
    try:
        result = await gateway_mcp.call_tool(body.tool_name, body.arguments)
        duration_s = time.monotonic() - start
        duration_ms = int(duration_s * 1000)

        # Prometheus metrics
        tool_invocations_total.labels(
            tool_name=body.tool_name, server_namespace=server_namespace, status="success",
        ).inc()
        tool_invocation_duration_seconds.labels(
            tool_name=body.tool_name, server_namespace=server_namespace,
        ).observe(duration_s)

        # Extract content from ToolResult
        if result.structured_content is not None:
            output = result.structured_content
        else:
            texts = []
            for item in result.content:
                if hasattr(item, "text"):
                    texts.append(item.text)
                elif hasattr(item, "data"):
                    texts.append(str(item.data))
            output = {"result": texts[0] if len(texts) == 1 else texts}

        await inv_repo.complete(inv.id, output, duration_ms, status="success")

        await event_bus.publish("tool.invoked", {
            "tool_name": body.tool_name,
            "server_id": str(server_id),
            "duration_ms": duration_ms,
            "status": "success",
        })

        return ToolCallResponse(
            result=output.get("result", output),
            duration_ms=duration_ms,
            invocation_id=inv.id,
        )

    except Exception as e:
        duration_s = time.monotonic() - start
        duration_ms = int(duration_s * 1000)

        # Prometheus metrics
        tool_invocations_total.labels(
            tool_name=body.tool_name, server_namespace=server_namespace, status="error",
        ).inc()
        tool_invocation_duration_seconds.labels(
            tool_name=body.tool_name, server_namespace=server_namespace,
        ).observe(duration_s)

        await inv_repo.complete(
            inv.id, {"error": str(e)}, duration_ms, status="error"
        )
        await event_bus.publish("tool.error", {
            "tool_name": body.tool_name,
            "server_id": str(server_id),
            "error": str(e),
        })
        raise HTTPException(status_code=500, detail=f"Tool call failed: {e}")


@router.get("/invocations", response_model=InvocationListResponse)
async def list_invocations(
    limit: int = 50,
    offset: int = 0,
    _caller: APIKey = Depends(get_current_api_key),
    inv_repo: InvocationRepository = Depends(get_invocation_repo),
):
    """List recent tool invocations."""
    invocations = await inv_repo.list_recent(limit=limit, offset=offset)
    total = await inv_repo.count()
    items = [
        InvocationResponse(
            id=inv.id,
            tool_id=inv.tool_id,
            server_id=inv.server_id,
            caller_id=inv.caller_id,
            input_data=inv.input_data,
            output_data=inv.output_data,
            duration_ms=inv.duration_ms,
            status=inv.status,
            created_at=inv.created_at,
        )
        for inv in invocations
    ]
    return InvocationListResponse(invocations=items, total=total)
