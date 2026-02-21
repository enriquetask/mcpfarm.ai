"""Health check probes for MCP server containers."""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def probe_mcp_health(host: str, port: int, timeout: float = 5.0) -> bool:
    """Probe an MCP server by attempting a TCP connection.

    Returns True if the server is accepting connections.
    """
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (TimeoutError, OSError) as e:
        logger.debug("Health probe failed for %s:%d: %s", host, port, e)
        return False


async def wait_for_ready(host: str, port: int, retries: int = 10, interval: float = 1.0) -> bool:
    """Wait until an MCP server is ready to accept connections.

    Returns True if ready within the retry window, False otherwise.
    """
    for attempt in range(retries):
        if await probe_mcp_health(host, port, timeout=2.0):
            logger.info("Server %s:%d ready after %d attempts", host, port, attempt + 1)
            return True
        logger.debug("Waiting for %s:%d (attempt %d/%d)", host, port, attempt + 1, retries)
        await asyncio.sleep(interval)
    logger.warning("Server %s:%d not ready after %d attempts", host, port, retries)
    return False
