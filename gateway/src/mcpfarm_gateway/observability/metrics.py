"""Prometheus metric definitions and /metrics endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.responses import Response

if TYPE_CHECKING:
    from starlette.requests import Request

# ── HTTP metrics (populated by middleware) ──────────────────────────

http_requests_total = Counter(
    "mcpfarm_http_requests_total",
    "Total HTTP requests",
    ["method", "path_template", "status_code"],
)

http_request_duration_seconds = Histogram(
    "mcpfarm_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path_template"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# ── Tool invocation metrics ─────────────────────────────────────────

tool_invocations_total = Counter(
    "mcpfarm_tool_invocations_total",
    "Total tool invocations",
    ["tool_name", "server_namespace", "status"],
)

tool_invocation_duration_seconds = Histogram(
    "mcpfarm_tool_invocation_duration_seconds",
    "Tool invocation duration in seconds",
    ["tool_name", "server_namespace"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

# ── Auth metrics ────────────────────────────────────────────────────

auth_failures_total = Counter(
    "mcpfarm_auth_failures_total",
    "Total authentication failures",
    ["reason"],
)

# ── Server health metrics ───────────────────────────────────────────

servers_total = Gauge(
    "mcpfarm_servers_total",
    "Servers by health status",
    ["status"],
)

tools_available = Gauge(
    "mcpfarm_tools_available",
    "Total available tools",
)

server_restarts_total = Counter(
    "mcpfarm_server_restarts_total",
    "Total server restart attempts",
    ["server_name"],
)

server_restart_count = Gauge(
    "mcpfarm_server_restart_count",
    "Consecutive restart count per server",
    ["server_name"],
)

# ── WebSocket metrics ───────────────────────────────────────────────

websocket_connections = Gauge(
    "mcpfarm_websocket_connections",
    "Active WebSocket connections",
)


# ── /metrics endpoint ──────────────────────────────────────────────


async def metrics_endpoint(request: Request) -> Response:
    """Prometheus metrics endpoint (unauthenticated)."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
