"""Server data access layer."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mcpfarm_gateway.db.models import MCPServer


class ServerRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> list[MCPServer]:
        result = await self.session.execute(
            select(MCPServer).options(selectinload(MCPServer.tools)).order_by(MCPServer.created_at)
        )
        return list(result.scalars().all())

    async def get_by_id(self, server_id: uuid.UUID) -> MCPServer | None:
        result = await self.session.execute(
            select(MCPServer)
            .options(selectinload(MCPServer.tools))
            .where(MCPServer.id == server_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> MCPServer | None:
        result = await self.session.execute(select(MCPServer).where(MCPServer.name == name))
        return result.scalar_one_or_none()

    async def get_by_namespace(self, namespace: str) -> MCPServer | None:
        result = await self.session.execute(
            select(MCPServer).where(MCPServer.namespace == namespace)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        namespace: str,
        image: str,
        port: int = 9001,
        env_vars: dict | None = None,
        auto_restart: bool = True,
    ) -> MCPServer:
        server = MCPServer(
            name=name,
            namespace=namespace,
            image=image,
            port=port,
            env_vars=env_vars or {},
            auto_restart=auto_restart,
        )
        self.session.add(server)
        await self.session.commit()
        await self.session.refresh(server)
        return server

    async def update_status(
        self, server_id: uuid.UUID, status: str, container_id: str | None = None
    ) -> MCPServer | None:
        server = await self.get_by_id(server_id)
        if not server:
            return None
        server.status = status
        if container_id is not None:
            server.container_id = container_id
        await self.session.commit()
        await self.session.refresh(server)
        return server

    async def update(self, server_id: uuid.UUID, **kwargs) -> MCPServer | None:
        server = await self.get_by_id(server_id)
        if not server:
            return None
        for key, value in kwargs.items():
            if hasattr(server, key):
                setattr(server, key, value)
        await self.session.commit()
        await self.session.refresh(server)
        return server

    async def delete(self, server_id: uuid.UUID) -> bool:
        server = await self.get_by_id(server_id)
        if not server:
            return False
        await self.session.delete(server)
        await self.session.commit()
        return True
