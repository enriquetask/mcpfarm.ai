"""Request ID + access logging + HTTP metrics middleware."""

from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from mcpfarm_gateway.observability.metrics import (
    http_request_duration_seconds,
    http_requests_total,
)

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

logger = structlog.stdlib.get_logger(__name__)

# Paths to skip for access logging and metrics (avoid noise)
_SKIP_PATHS = {"/health", "/health/live", "/metrics"}


def _normalize_path(path: str) -> str:
    """Normalize path to avoid cardinality explosion in metrics.

    Replaces UUIDs and numeric IDs with placeholders.
    """
    parts = path.rstrip("/").split("/")
    normalized = []
    for part in parts:
        # UUID pattern
        if len(part) == 36 and part.count("-") == 4 or part.isdigit():
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/".join(normalized) or "/"


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware that adds request tracing, access logging, and HTTP metrics."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract or generate request ID
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())

        # Bind to structlog contextvars (all downstream logs include it)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        # Set request ID on response
        response.headers["X-Request-ID"] = request_id

        # Skip noisy paths for logging and metrics
        if request.url.path not in _SKIP_PATHS:
            path_template = _normalize_path(request.url.path)

            # Prometheus metrics
            http_requests_total.labels(
                method=request.method,
                path_template=path_template,
                status_code=str(response.status_code),
            ).inc()
            http_request_duration_seconds.labels(
                method=request.method,
                path_template=path_template,
            ).observe(duration)

            # Structured access log
            logger.info(
                "request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=round(duration * 1000, 1),
                client_ip=request.client.host if request.client else None,
            )

        return response
