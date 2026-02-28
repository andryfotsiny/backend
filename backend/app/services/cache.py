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
        """Check per‑user rate limit based on role quota.
        A quota of 0 means unlimited.
        """
        if not self.redis_client:
            return False
        # Determine quota from settings
        quota = getattr(
            settings, f"{role.upper()}_QUOTA", settings.MAX_REQUESTS_PER_MINUTE
        )
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

    async def set(self, key: str, value: dict, expire: int = 3600):
        if not self.redis_client:
            return
        try:
            await self.redis_client.setex(key, expire, json.dumps(value))
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


cache_service = CacheService()
