"""API key management endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException

from mcpfarm_gateway.api.deps import get_api_key_repo, get_current_api_key
from mcpfarm_gateway.api.schemas import (
    APIKeyCreate,
    APIKeyCreatedResponse,
    APIKeyListResponse,
    APIKeyResponse,
)

if TYPE_CHECKING:
    import uuid

    from mcpfarm_gateway.db.models import APIKey
    from mcpfarm_gateway.db.repositories import APIKeyRepository

router = APIRouter(prefix="/keys", tags=["keys"])


@router.post("/", response_model=APIKeyCreatedResponse, status_code=201)
async def create_api_key(
    body: APIKeyCreate,
    _caller: APIKey = Depends(get_current_api_key),
    repo: APIKeyRepository = Depends(get_api_key_repo),
):
    """Create a new API key. The plaintext key is returned only once."""
    api_key, plaintext = await repo.create(
        name=body.name,
        scopes=body.scopes,
    )
    return APIKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        scopes=api_key.scopes,
        is_active=api_key.is_active,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
        key=plaintext,
    )


@router.get("/", response_model=APIKeyListResponse)
async def list_api_keys(
    _caller: APIKey = Depends(get_current_api_key),
    repo: APIKeyRepository = Depends(get_api_key_repo),
):
    """List all API keys (without hashes)."""
    keys = await repo.list_all()
    items = [
        APIKeyResponse(
            id=k.id,
            name=k.name,
            scopes=k.scopes,
            is_active=k.is_active,
            expires_at=k.expires_at,
            created_at=k.created_at,
        )
        for k in keys
    ]
    return APIKeyListResponse(keys=items, total=len(items))


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: uuid.UUID,
    _caller: APIKey = Depends(get_current_api_key),
    repo: APIKeyRepository = Depends(get_api_key_repo),
):
    """Revoke an API key."""
    result = await repo.revoke(key_id)
    if not result:
        raise HTTPException(status_code=404, detail="API key not found")
