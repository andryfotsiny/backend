import redis.asyncio as redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisService:
    def __init__(self):
        self.redis_client = None

    async def connect(self):
        if self.redis_client is None:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            try:
                await self.redis_client.ping()
                logger.info("Connected to Redis")
            except Exception as e:
                logger.error(f"Could not connect to Redis: {e}")
                self.redis_client = None

    async def get_client(self):
        if self.redis_client is None:
            await self.connect()
        return self.redis_client

    async def blacklist_token(self, jti: str, expire_seconds: int):
        """Ajoute un JTI à la liste noire avec un TTL égal au temps restant avant expiration."""
        client = await self.get_client()
        if client:
            await client.setex(f"blacklist:{jti}", expire_seconds, "true")

    async def is_token_blacklisted(self, jti: str) -> bool:
        """Vérifie si un JTI est dans la liste noire."""
        client = await self.get_client()
        if client:
            exists = await client.exists(f"blacklist:{jti}")
            return bool(exists)
        return False

redis_service = RedisService()
