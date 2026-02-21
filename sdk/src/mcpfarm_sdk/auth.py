"""Custom httpx auth for MCPFarm Bearer token authentication."""

from __future__ import annotations

import httpx


class BearerAuth(httpx.Auth):
    """httpx Auth class that injects a Bearer token into requests."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def auth_flow(self, request: httpx.Request):
        request.headers["Authorization"] = f"Bearer {self.api_key}"
        yield request
