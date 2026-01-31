import redis.asyncio as redis
import json
from typing import Optional
from app.core.config import settings

class CacheService:
    def __init__(self):
        self.redis_client = None
    
    async def connect(self):
        self.redis_client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    
    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()
    
    async def get(self, key: str) -> Optional[dict]:
        if not self.redis_client:
            return None
        try:
            data = await self.redis_client.get(key)
            return json.loads(data) if data else None
        except:
            return None
    
    async def set(self, key: str, value: dict, expire: int = 3600):
        if not self.redis_client:
            return
        try:
            await self.redis_client.setex(key, expire, json.dumps(value))
        except:
            pass
    
    async def delete(self, key: str):
        if not self.redis_client:
            return
        try:
            await self.redis_client.delete(key)
        except:
            pass
    
    async def increment(self, key: str) -> int:
        if not self.redis_client:
            return 0
        try:
            return await self.redis_client.incr(key)
        except:
            return 0
    
    async def check_rate_limit(self, user_id: str, limit: int = 100) -> bool:
        key = f"rate_limit:{user_id}"
        count = await self.increment(key)
        if count == 1:
            await self.redis_client.expire(key, 60)
        return count <= limit

cache_service = CacheService()
