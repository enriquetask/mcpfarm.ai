"""Pydantic request/response schemas for the REST API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Server schemas ───────────────────────────────────────────

class ServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    namespace: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    image: str = Field(..., min_length=1, max_length=500)
    port: int = Field(default=9001, ge=1, le=65535)
    env_vars: dict[str, str] = Field(default_factory=dict)
    auto_restart: bool = True


class ServerUpdate(BaseModel):
    name: str | None = None
    image: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    env_vars: dict[str, str] | None = None
    auto_restart: bool | None = None


class ServerResponse(BaseModel):
    id: uuid.UUID
    name: str
    namespace: str
    image: str
    port: int
    env_vars: dict[str, str]
    status: str
    container_id: str | None
    auto_restart: bool
    tool_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServerListResponse(BaseModel):
    servers: list[ServerResponse]
    total: int


# ── Tool schemas ─────────────────────────────────────────────

class ToolResponse(BaseModel):
    name: str
    namespaced_name: str
    description: str | None
    input_schema: dict[str, Any]
    server_namespace: str = ""
    is_available: bool = True


class ToolListResponse(BaseModel):
    tools: list[ToolResponse]
    total: int


# ── Invocation schemas ───────────────────────────────────────

class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    result: Any
    duration_ms: int
    invocation_id: uuid.UUID


class InvocationResponse(BaseModel):
    id: uuid.UUID
    tool_id: uuid.UUID | None
    server_id: uuid.UUID
    caller_id: str | None
    input_data: dict[str, Any]
    output_data: dict[str, Any] | None
    duration_ms: int | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InvocationListResponse(BaseModel):
    invocations: list[InvocationResponse]
    total: int


# ── API Key schemas ───────────────────────────────────────────

class APIKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    scopes: list[str] = Field(default_factory=list)


class APIKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    scopes: list[str]
    is_active: bool
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyCreatedResponse(APIKeyResponse):
    """Returned only on creation - includes the plaintext key."""
    key: str


class APIKeyListResponse(BaseModel):
    keys: list[APIKeyResponse]
    total: int


# ── Stats ────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    total_servers: int
    healthy_servers: int
    total_tools: int
    total_invocations: int
