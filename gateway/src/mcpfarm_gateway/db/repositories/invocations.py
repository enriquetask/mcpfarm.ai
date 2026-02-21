"""Tool invocation data access layer."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mcpfarm_gateway.db.models import ToolInvocation


class InvocationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        tool_id: uuid.UUID,
        server_id: uuid.UUID,
        input_data: dict[str, Any],
        caller_id: str | None = None,
    ) -> ToolInvocation:
        inv = ToolInvocation(
            tool_id=tool_id,
            server_id=server_id,
            input_data=input_data,
            caller_id=caller_id,
            status="pending",
        )
        self.session.add(inv)
        await self.session.commit()
        await self.session.refresh(inv)
        return inv

    async def complete(
        self,
        invocation_id: uuid.UUID,
        output_data: dict[str, Any],
        duration_ms: int,
        status: str = "success",
    ) -> ToolInvocation | None:
        result = await self.session.execute(
            select(ToolInvocation).where(ToolInvocation.id == invocation_id)
        )
        inv = result.scalar_one_or_none()
        if not inv:
            return None
        inv.output_data = output_data
        inv.duration_ms = duration_ms
        inv.status = status
        await self.session.commit()
        return inv

    async def list_recent(self, limit: int = 50, offset: int = 0) -> list[ToolInvocation]:
        result = await self.session.execute(
            select(ToolInvocation)
            .options(selectinload(ToolInvocation.tool), selectinload(ToolInvocation.server))
            .order_by(ToolInvocation.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_server(self, server_id: uuid.UUID, limit: int = 50) -> list[ToolInvocation]:
        result = await self.session.execute(
            select(ToolInvocation)
            .where(ToolInvocation.server_id == server_id)
            .order_by(ToolInvocation.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(ToolInvocation.id)))
        return result.scalar_one()
