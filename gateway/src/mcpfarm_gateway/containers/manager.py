"""Docker SDK container CRUD with Protocol-based abstraction."""

from __future__ import annotations

import logging
from typing import Any, Protocol

import docker
from docker.models.containers import Container

logger = logging.getLogger(__name__)

LABEL_MANAGED = "mcpfarm.managed"
LABEL_NAMESPACE = "mcpfarm.namespace"
LABEL_SERVER_ID = "mcpfarm.server_id"


class ContainerManager(Protocol):
    """Protocol for container lifecycle management."""

    async def create_and_start(
        self,
        image: str,
        name: str,
        namespace: str,
        server_id: str,
        port: int,
        env_vars: dict[str, str] | None = None,
    ) -> str: ...

    async def stop(self, container_id: str) -> None: ...

    async def remove(self, container_id: str) -> None: ...

    async def get_status(self, container_id: str) -> str | None: ...

    async def get_ip(self, container_id: str, network: str) -> str | None: ...

    async def list_managed(self) -> list[dict[str, Any]]: ...


class DockerContainerManager:
    """Local Docker SDK implementation of ContainerManager."""

    def __init__(self, network_internal: str = "mcpfarm_internal"):
        self.client = docker.from_env()
        self.network_internal = network_internal

    def _get_full_network_name(self) -> str:
        """Find the actual Docker network name (may be prefixed by compose project)."""
        networks = self.client.networks.list()
        for net in networks:
            if net.name and self.network_internal in net.name:
                return net.name
        return self.network_internal

    async def create_and_start(
        self,
        image: str,
        name: str,
        namespace: str,
        server_id: str,
        port: int = 9001,
        env_vars: dict[str, str] | None = None,
    ) -> str:
        """Create and start an MCP server container. Returns container ID."""
        container_name = f"mcpfarm-{namespace}"
        network_name = self._get_full_network_name()

        # Remove existing container with same name if it exists
        try:
            existing = self.client.containers.get(container_name)
            existing.remove(force=True)
        except docker.errors.NotFound:
            pass

        labels = {
            LABEL_MANAGED: "true",
            LABEL_NAMESPACE: namespace,
            LABEL_SERVER_ID: server_id,
        }

        environment = env_vars or {}

        container: Container = self.client.containers.run(
            image=image,
            name=container_name,
            labels=labels,
            environment=environment,
            network=network_name,
            detach=True,
            remove=False,
        )

        logger.info("Started container %s (%s) on network %s", container_name, container.id[:12], network_name)
        return container.id

    async def stop(self, container_id: str) -> None:
        """Stop a container by ID."""
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=10)
            logger.info("Stopped container %s", container_id[:12])
        except docker.errors.NotFound:
            logger.warning("Container %s not found for stop", container_id[:12])

    async def remove(self, container_id: str) -> None:
        """Remove a container by ID."""
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=True)
            logger.info("Removed container %s", container_id[:12])
        except docker.errors.NotFound:
            logger.warning("Container %s not found for removal", container_id[:12])

    async def get_status(self, container_id: str) -> str | None:
        """Get container status (running, exited, etc.)."""
        try:
            container = self.client.containers.get(container_id)
            return container.status
        except docker.errors.NotFound:
            return None

    async def get_ip(self, container_id: str, network: str | None = None) -> str | None:
        """Get container IP address on the specified network."""
        try:
            container = self.client.containers.get(container_id)
            container.reload()
            networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
            target_network = network or self._get_full_network_name()
            for net_name, net_info in networks.items():
                if target_network in net_name:
                    return net_info.get("IPAddress")
            # Fallback: return first available IP
            for net_info in networks.values():
                ip = net_info.get("IPAddress")
                if ip:
                    return ip
            return None
        except docker.errors.NotFound:
            return None

    async def list_managed(self) -> list[dict[str, Any]]:
        """List all mcpfarm-managed containers."""
        containers = self.client.containers.list(
            all=True, filters={"label": f"{LABEL_MANAGED}=true"}
        )
        result = []
        for c in containers:
            # Get image name
            try:
                image = c.image.tags[0] if c.image.tags else c.attrs["Config"]["Image"]
            except Exception:
                image = "unknown"
            result.append({
                "container_id": c.id,
                "name": c.name,
                "status": c.status,
                "namespace": c.labels.get(LABEL_NAMESPACE, ""),
                "server_id": c.labels.get(LABEL_SERVER_ID, ""),
                "image": image,
            })
        return result
