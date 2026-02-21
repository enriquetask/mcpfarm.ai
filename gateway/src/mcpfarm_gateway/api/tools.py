"""Tool discovery API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends

from mcpfarm_gateway.api.deps import get_current_api_key, get_tool_registry
from mcpfarm_gateway.api.schemas import ToolListResponse, ToolResponse

if TYPE_CHECKING:
    from mcpfarm_gateway.db.models import APIKey
    from mcpfarm_gateway.mcp.tool_registry import ToolRegistry

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/", response_model=ToolListResponse)
async def list_tools(
    _caller: APIKey = Depends(get_current_api_key),
    tool_reg: ToolRegistry = Depends(get_tool_registry),
):
    tools = await tool_reg.list_all()
    items = [
        ToolResponse(
            name=t["name"],
            namespaced_name=t["namespaced_name"],
            description=t.get("description"),
            input_schema=t.get("input_schema", {}),
            server_namespace=t.get("namespace", ""),
            is_available=t.get("is_available", True),
        )
        for t in tools
    ]
    return ToolListResponse(tools=items, total=len(items))


@router.get("/{namespaced_name}", response_model=ToolResponse)
async def get_tool(
    namespaced_name: str,
    _caller: APIKey = Depends(get_current_api_key),
    tool_reg: ToolRegistry = Depends(get_tool_registry),
):
    tool = await tool_reg.get_tool(namespaced_name)
    if not tool:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Tool not found")
    return ToolResponse(
        name=tool["name"],
        namespaced_name=tool["namespaced_name"],
        description=tool.get("description"),
        input_schema=tool.get("input_schema", {}),
        server_namespace=tool.get("namespace", ""),
        is_available=tool.get("is_available", True),
    )
