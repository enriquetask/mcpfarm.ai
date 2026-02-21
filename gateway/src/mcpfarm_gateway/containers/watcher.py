"""Background health monitor with auto-recovery.

Periodically checks all registered MCP servers and takes action
when health states change (restart on failure, re-mount on recovery).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from mcpfarm_gateway.containers.health import probe_mcp_health, wait_for_ready
from mcpfarm_gateway.containers.manager import DockerContainerManager
from mcpfarm_gateway.db import async_session
from mcpfarm_gateway.db.repositories.servers import ServerRepository
from mcpfarm_gateway.db.repositories.tools import ToolRepository
from mcpfarm_gateway.mcp.proxy_manager import ProxyManager
from mcpfarm_gateway.mcp.tool_registry import ToolRegistry
from mcpfarm_gateway.realtime.redis_pubsub import EventBus

from mcpfarm_gateway.observability.metrics import (
    server_restarts_total,
    server_restart_count,
    servers_total,
    tools_available,
)

logger = logging.getLogger(__name__)


class ServerWatcher:
    """Async background task that monitors all MCP server containers."""

    def __init__(
        self,
        container_mgr: DockerContainerManager,
        proxy_mgr: ProxyManager,
        tool_registry: ToolRegistry,
        event_bus: EventBus,
        poll_interval: float = 15.0,
        base_backoff: float = 5.0,
        max_backoff: float = 120.0,
    ):
        self.container_mgr = container_mgr
        self.proxy_mgr = proxy_mgr
        self.tool_registry = tool_registry
        self.event_bus = event_bus
        self.poll_interval = poll_interval
        self.base_backoff = base_backoff
        self.max_backoff = max_backoff

        self._task: asyncio.Task | None = None
        self._restart_counts: dict[str, int] = {}  # server_id -> consecutive failures

    async def start(self) -> None:
        """Start the watcher background loop."""
        await self._bootstrap_from_docker()
        self._task = asyncio.create_task(self._loop())
        logger.info("ServerWatcher started (poll_interval=%.0fs)", self.poll_interval)

    async def _bootstrap_from_docker(self) -> None:
        """Auto-discover docker-compose managed containers and create DB records.

        Scans Docker for containers with mcpfarm.managed=true label and ensures
        each has a corresponding database record. This handles servers defined
        in docker-compose that were not registered via the API.
        """
        try:
            managed = await self.container_mgr.list_managed()
        except Exception:
            logger.exception("Failed to list managed containers during bootstrap")
            return

        if not managed:
            return

        async with async_session() as session:
            repo = ServerRepository(session)

            for container in managed:
                namespace = container.get("namespace")
                if not namespace:
                    continue

                existing = await repo.get_by_namespace(namespace)
                if existing:
                    # Update container_id if the container is running but DB has stale ID
                    if (
                        container["status"] == "running"
                        and existing.container_id != container["container_id"]
                    ):
                        existing.container_id = container["container_id"]
                        if existing.status == "STOPPED":
                            existing.status = "STARTING"
                        await session.commit()
                        logger.info(
                            "Updated container_id for %s (%s)",
                            namespace, container["container_id"][:12],
                        )
                    continue

                # Create new server record for this docker-compose container
                display_name = namespace.replace("_", " ").title() + " Server"
                image = container.get("image", "unknown")
                server = await repo.create(
                    name=display_name,
                    namespace=namespace,
                    image=image,
                    port=9001,
                    auto_restart=False,  # docker-compose manages lifecycle
                )

                # Set container_id and initial status
                if container["status"] == "running":
                    await repo.update_status(
                        server.id, "STARTING", container["container_id"]
                    )

                logger.info(
                    "Bootstrap: registered %s (namespace=%s, container=%s)",
                    display_name, namespace, container["container_id"][:12],
                )

    async def stop(self) -> None:
        """Stop the watcher."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("ServerWatcher stopped")

    async def _loop(self) -> None:
        """Main polling loop."""
        while True:
            try:
                await self._check_all()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Watcher loop error")
            await asyncio.sleep(self.poll_interval)

    async def _check_all(self) -> None:
        """Check health of all servers that should be running."""
        async with async_session() as session:
            repo = ServerRepository(session)
            servers = await repo.list_all()

        # Update server health gauges
        status_counts: dict[str, int] = {}
        for s in servers:
            status_counts[s.status] = status_counts.get(s.status, 0) + 1
        for status_val in ("HEALTHY", "DEGRADED", "UNHEALTHY", "STARTING", "STOPPED"):
            servers_total.labels(status=status_val).set(status_counts.get(status_val, 0))

        # Update tools gauge
        try:
            tools_available.set(await self.tool_registry.count())
        except Exception:
            pass

        for server in servers:
            if server.status == "STOPPED":
                continue

            if not server.container_id:
                continue

            try:
                await self._check_server(server)
            except Exception:
                logger.exception("Error checking server %s", server.name)

    async def _check_server(self, server: Any) -> None:
        """Check a single server's health and take action."""
        server_id = str(server.id)

        # Docker-level: is the container running?
        docker_status = await self.container_mgr.get_status(server.container_id)

        if docker_status != "running":
            await self._handle_container_down(server, docker_status)
            return

        # MCP-level: can we connect to the server?
        ip = await self.container_mgr.get_ip(server.container_id)
        if not ip:
            await self._transition(server, "DEGRADED", "Cannot resolve container IP")
            return

        healthy = await probe_mcp_health(ip, server.port, timeout=3.0)

        if healthy and server.status != "HEALTHY":
            await self._handle_recovery(server, ip)
        elif healthy and server.status == "HEALTHY":
            # Ensure proxy is mounted (handles gateway restart)
            if server.namespace not in self.proxy_mgr._mounted:
                logger.info("Re-mounting proxy for %s after gateway restart", server.name)
                await self._mount_and_register(server, ip, server.container_id)
        elif not healthy and server.status == "HEALTHY":
            await self._transition(server, "DEGRADED", "MCP endpoint unresponsive")

    async def _handle_container_down(self, server: Any, docker_status: str | None) -> None:
        """Handle a server whose container is not running."""
        server_id = str(server.id)

        if not server.auto_restart:
            await self._transition(server, "UNHEALTHY", f"Container {docker_status or 'gone'}")
            return

        count = self._restart_counts.get(server_id, 0)
        if count >= server.max_restart_attempts:
            await self._transition(
                server, "UNHEALTHY",
                f"Max restart attempts ({server.max_restart_attempts}) exceeded"
            )
            return

        # Exponential backoff
        backoff = min(self.base_backoff * (2 ** count), self.max_backoff)
        logger.info(
            "Auto-restarting %s (attempt %d, backoff %.0fs)",
            server.name, count + 1, backoff,
        )
        await asyncio.sleep(backoff)

        try:
            await self._restart_server(server)
            self._restart_counts[server_id] = count + 1
            server_restarts_total.labels(server_name=server.name).inc()
            server_restart_count.labels(server_name=server.name).set(count + 1)
        except Exception:
            logger.exception("Auto-restart failed for %s", server.name)
            self._restart_counts[server_id] = count + 1
            server_restarts_total.labels(server_name=server.name).inc()
            server_restart_count.labels(server_name=server.name).set(count + 1)
            await self._transition(server, "UNHEALTHY", "Auto-restart failed")

    async def _restart_server(self, server: Any) -> None:
        """Restart a server container and re-mount proxy."""
        server_id = str(server.id)

        # Clean up old container
        if server.container_id:
            await self.container_mgr.remove(server.container_id)

        # Start new container
        container_id = await self.container_mgr.create_and_start(
            image=server.image,
            name=server.name,
            namespace=server.namespace,
            server_id=server_id,
            port=server.port,
            env_vars=server.env_vars,
        )

        async with async_session() as session:
            repo = ServerRepository(session)
            await repo.update_status(server.id, "STARTING", container_id)

        ip = await self.container_mgr.get_ip(container_id)
        if ip:
            ready = await wait_for_ready(ip, server.port, retries=10, interval=1.0)
            if ready:
                await self._mount_and_register(server, ip, container_id)
                return

        await self._transition(server, "DEGRADED", "Not ready after restart")

    async def _handle_recovery(self, server: Any, ip: str) -> None:
        """Handle a server that has recovered to healthy state."""
        server_id = str(server.id)
        self._restart_counts.pop(server_id, None)
        server_restart_count.labels(server_name=server.name).set(0)

        # Re-mount proxy if not already mounted
        if server.namespace not in self.proxy_mgr._mounted:
            await self._mount_and_register(server, ip, server.container_id)
        else:
            await self._transition(server, "HEALTHY", "Recovered")

    async def _mount_and_register(self, server: Any, ip: str, container_id: str) -> None:
        """Mount proxy and register tools for a server."""
        server_id = str(server.id)
        mcp_url = f"http://{ip}:{server.port}/mcp"

        try:
            tools = await self.proxy_mgr.mount(server.namespace, mcp_url)
            await self.tool_registry.register_tools(server_id, server.namespace, tools)

            async with async_session() as session:
                tool_repo = ToolRepository(session)
                await tool_repo.sync_tools(server.id, server.namespace, tools)

            await self._transition(server, "HEALTHY", f"Mounted with {len(tools)} tools")
            self._restart_counts.pop(server_id, None)
        except Exception as e:
            logger.error("Failed to mount proxy for %s: %s", server.namespace, e)
            await self._transition(server, "DEGRADED", f"Mount failed: {e}")

    async def _transition(self, server: Any, new_status: str, reason: str) -> None:
        """Transition a server to a new status if changed."""
        if server.status == new_status:
            return

        old_status = server.status
        logger.info(
            "Server %s: %s -> %s (%s)",
            server.name, old_status, new_status, reason,
        )

        async with async_session() as session:
            repo = ServerRepository(session)
            await repo.update_status(server.id, new_status)

        await self.event_bus.publish("server.health_changed", {
            "server_id": str(server.id),
            "name": server.name,
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason,
        })
