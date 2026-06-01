import redis.asyncio as redis
import json
from typing import Optional
from app.core.config import settings

class CacheService:
    def __init__(self):
        self.redis_client = None

    async def connect(self):
        self.redis_client = await redis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=True
        )

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()

    async def check_rate_limit(self, user_id: str, role: str) -> bool:
        if not self.redis_client:
            return False
        quota = getattr(settings, f"{role.upper()}_QUOTA", settings.MAX_REQUESTS_PER_MINUTE)
        if quota == 0:
            return True
        key = f"rate_limit:{role}:{user_id}"
        count = await self.increment(key)
        if count == 1:
            await self.redis_client.expire(key, 60)
        return count <= quota

    async def get(self, key: str) -> Optional[dict]:
        if not self.redis_client:
            return None
        try:
            data = await self.redis_client.get(key)
            return json.loads(data) if data else None
        except Exception:
            return None

    async def set(self, key: str, value: dict, expire: int = 3600, ttl: int = None):
        if not self.redis_client:
            return
        try:
            expiry = ttl if ttl is not None else expire
            await self.redis_client.setex(key, expiry, json.dumps(value))
        except Exception:
            pass

    async def delete(self, key: str):
        if not self.redis_client:
            return
        try:
            await self.redis_client.delete(key)
        except Exception:
            pass

    async def increment(self, key: str) -> int:
        if not self.redis_client:
            return 0
        try:
            return await self.redis_client.incr(key)
        except Exception:
            return 0

    async def delete_pattern(self, pattern: str):
        """Supprime toutes les clés correspondant au pattern (ex: 'fraud_list:*')."""
        if not self.redis_client:
            return
        try:
            cursor = 0
            while True:
                cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis_client.delete(*keys)
                if cursor == 0:
                    break
        except Exception:
            pass

cache_service = CacheService()