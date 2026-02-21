"""Tool data access layer."""

import uuid

from sqlalchemy import select, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from mcpfarm_gateway.db.models import MCPTool


class ToolRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[MCPTool]:
        result = await self.session.execute(
            select(MCPTool).where(MCPTool.is_available).order_by(MCPTool.namespaced_name)
        )
        return list(result.scalars().all())

    async def list_by_server(self, server_id: uuid.UUID) -> list[MCPTool]:
        result = await self.session.execute(
            select(MCPTool).where(MCPTool.server_id == server_id).order_by(MCPTool.name)
        )
        return list(result.scalars().all())

    async def get_by_namespaced_name(self, namespaced_name: str) -> MCPTool | None:
        result = await self.session.execute(
            select(MCPTool).where(MCPTool.namespaced_name == namespaced_name)
        )
        return result.scalar_one_or_none()

    async def sync_tools(self, server_id: uuid.UUID, namespace: str, tools: list[dict]) -> None:
        """Replace all tools for a server with newly discovered ones."""
        await self.session.execute(
            sql_delete(MCPTool).where(MCPTool.server_id == server_id)
        )
        for tool_data in tools:
            tool = MCPTool(
                server_id=server_id,
                name=tool_data["name"],
                namespaced_name=f"{namespace}_{tool_data['name']}",
                description=tool_data.get("description"),
                input_schema=tool_data.get("inputSchema", {}),
                is_available=True,
            )
            self.session.add(tool)
        await self.session.commit()

    async def mark_unavailable(self, server_id: uuid.UUID) -> None:
        """Mark all tools for a server as unavailable."""
        tools = await self.list_by_server(server_id)
        for tool in tools:
            tool.is_available = False
        await self.session.commit()

    async def count(self) -> int:
        result = await self.session.execute(
            select(MCPTool).where(MCPTool.is_available)
        )
        return len(result.scalars().all())
