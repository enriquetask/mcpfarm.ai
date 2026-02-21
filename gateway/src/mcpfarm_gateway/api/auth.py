"""API key authentication middleware and dependencies."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request
from starlette.responses import JSONResponse

from mcpfarm_gateway.config import settings
from mcpfarm_gateway.db.models import APIKey
from mcpfarm_gateway.observability.metrics import auth_failures_total

if TYPE_CHECKING:
    from mcpfarm_gateway.db.repositories.api_keys import APIKeyRepository

logger = logging.getLogger(__name__)


def _extract_bearer_token(request: Request) -> str | None:
    """Extract Bearer token from Authorization header."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None


async def verify_api_key(
    request: Request,
    api_key_repo: APIKeyRepository,
) -> APIKey:
    """Validate Bearer token and return the APIKey record.

    Called from deps.get_current_api_key which provides the repo.
    Also enforces rate limiting via Redis.
    """
    token = _extract_bearer_token(request)
    if not token:
        auth_failures_total.labels(reason="missing_key").inc()
        raise HTTPException(status_code=401, detail="Missing API key")

    # Check admin bootstrap key first
    if settings.admin_api_key and token == settings.admin_api_key:
        # Return a synthetic APIKey-like object for the admin key
        return _make_admin_key()

    api_key = await api_key_repo.get_by_hash(token)
    if not api_key:
        auth_failures_total.labels(reason="invalid_key").inc()
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not api_key_repo.validate_key(api_key):
        auth_failures_total.labels(reason="expired_or_revoked").inc()
        raise HTTPException(status_code=401, detail="API key expired or revoked")

    # Rate limiting
    await _check_rate_limit(request, api_key.key_hash)

    return api_key


def _make_admin_key() -> APIKey:
    """Create a synthetic APIKey for the admin bootstrap key.

    Constructs a proper SQLAlchemy instance without persisting to DB.
    """
    import uuid

    key = APIKey(
        id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
        name="admin",
        key_hash="admin",
        scopes=["*"],
        is_active=True,
        expires_at=None,
    )
    return key


async def _check_rate_limit(request: Request, key_hash: str) -> None:
    """Redis-based sliding window rate limiter."""
    if settings.rate_limit_per_minute <= 0:
        return

    redis = request.app.state.redis
    minute_bucket = int(time.time()) // 60
    redis_key = f"mcpfarm:ratelimit:{key_hash}:{minute_bucket}"

    current = await redis.incr(redis_key)
    if current == 1:
        await redis.expire(redis_key, 120)

    if current > settings.rate_limit_per_minute:
        auth_failures_total.labels(reason="rate_limited").inc()
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(60 - int(time.time()) % 60)},
        )


def require_scope(namespace: str):
    """Dependency factory: checks that the API key has access to a namespace."""
    from fastapi import Depends

    from mcpfarm_gateway.api.deps import get_current_api_key

    async def _check(api_key: APIKey = Depends(get_current_api_key)) -> APIKey:
        if "*" in api_key.scopes or not api_key.scopes:
            return api_key
        if namespace in api_key.scopes:
            return api_key
        raise HTTPException(status_code=403, detail=f"No access to namespace '{namespace}'")

    return _check


class MCPAuthMiddleware:
    """ASGI middleware that authenticates /mcp requests via Bearer token.

    Wraps the mounted MCP Starlette app and validates the token before
    passing through to the inner app.
    """

    def __init__(self, app, gateway_app):
        self.app = app
        self.gateway_app = gateway_app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Extract Authorization header
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode()

            if not auth_header.startswith("Bearer "):
                auth_failures_total.labels(reason="missing_key").inc()
                response = JSONResponse(
                    status_code=401,
                    content={"detail": "Missing API key"},
                )
                await response(scope, receive, send)
                return

            token = auth_header[7:]

            # Check admin bootstrap key
            if settings.admin_api_key and token == settings.admin_api_key:
                await self.app(scope, receive, send)
                return

            # Validate against DB
            from mcpfarm_gateway.db import async_session
            from mcpfarm_gateway.db.repositories.api_keys import APIKeyRepository

            async with async_session() as session:
                repo = APIKeyRepository(session)
                api_key = await repo.get_by_hash(token)
                if not api_key or not repo.validate_key(api_key):
                    auth_failures_total.labels(reason="invalid_key").inc()
                    response = JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid API key"},
                    )
                    await response(scope, receive, send)
                    return

            # Rate limit check via Redis
            redis = self.gateway_app.state.redis
            if settings.rate_limit_per_minute > 0:
                minute_bucket = int(time.time()) // 60
                redis_key = f"mcpfarm:ratelimit:{api_key.key_hash}:{minute_bucket}"
                current = await redis.incr(redis_key)
                if current == 1:
                    await redis.expire(redis_key, 120)
                if current > settings.rate_limit_per_minute:
                    auth_failures_total.labels(reason="rate_limited").inc()
                    response = JSONResponse(
                        status_code=429,
                        content={"detail": "Rate limit exceeded"},
                    )
                    await response(scope, receive, send)
                    return

            await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)
