"""API key data access layer."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mcpfarm_gateway.config import settings
from mcpfarm_gateway.db.models import APIKey


def _hash_key(plaintext: str) -> str:
    """SHA-256 hash of the API key with the configured salt."""
    salted = f"{settings.api_key_secret}:{plaintext}"
    return hashlib.sha256(salted.encode()).hexdigest()


def _generate_key() -> str:
    """Generate a new API key in sk-farm-{32 hex} format."""
    return f"sk-farm-{secrets.token_hex(16)}"


class APIKeyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        name: str,
        scopes: list[str] | None = None,
        expires_at: datetime | None = None,
    ) -> tuple[APIKey, str]:
        """Create a new API key. Returns (db_record, plaintext_key)."""
        plaintext = _generate_key()
        key_hash = _hash_key(plaintext)
        api_key = APIKey(
            name=name,
            key_hash=key_hash,
            scopes=scopes or [],
            expires_at=expires_at,
        )
        self.session.add(api_key)
        await self.session.commit()
        await self.session.refresh(api_key)
        return api_key, plaintext

    async def get_by_hash(self, plaintext: str) -> APIKey | None:
        """Look up an API key by its plaintext value (hashed for lookup)."""
        key_hash = _hash_key(plaintext)
        result = await self.session.execute(select(APIKey).where(APIKey.key_hash == key_hash))
        return result.scalar_one_or_none()

    async def get_by_id(self, key_id: uuid.UUID) -> APIKey | None:
        result = await self.session.execute(select(APIKey).where(APIKey.id == key_id))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[APIKey]:
        result = await self.session.execute(select(APIKey).order_by(APIKey.created_at.desc()))
        return list(result.scalars().all())

    async def revoke(self, key_id: uuid.UUID) -> APIKey | None:
        api_key = await self.get_by_id(key_id)
        if not api_key:
            return None
        api_key.is_active = False
        await self.session.commit()
        await self.session.refresh(api_key)
        return api_key

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(APIKey.id)))
        return result.scalar_one()

    def validate_key(self, api_key: APIKey) -> bool:
        """Check if a key is active and not expired."""
        if not api_key.is_active:
            return False
        return not (api_key.expires_at and api_key.expires_at < datetime.now(UTC))
