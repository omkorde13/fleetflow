import json
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Return a shared Redis client, creating it on first use."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis():
    """Close the shared Redis connection pool."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


class CacheManager:
    """JSON-backed cache wrapper around a Redis client."""

    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def get(self, key: str) -> Any:
        value = await self.redis.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        if not isinstance(value, str):
            value = json.dumps(value)
        if ttl:
            await self.redis.set(key, value, ex=ttl)
        else:
            await self.redis.set(key, value)

    async def delete(self, key: str):
        await self.redis.delete(key)


class PubSubManager:
    """Publishes real-time events over Redis pub/sub channels."""

    def __init__(self, redis: aioredis.Redis):
        self.redis = redis

    async def publish_delivery_update(self, delivery_id: str, status: str, extra: Optional[dict] = None):
        payload = {"type": "delivery_update", "delivery_id": delivery_id, "status": status}
        if extra:
            payload.update(extra)
        await self.redis.publish(f"delivery:{delivery_id}", json.dumps(payload))

    async def publish_notification(self, user_id: str, notification: dict):
        payload = {"type": "notification", "user_id": user_id, **notification}
        await self.redis.publish(f"user:{user_id}", json.dumps(payload))


async def check_rate_limit(redis: aioredis.Redis, key: str, limit: int, window_seconds: int) -> bool:
    """Fixed-window rate limiter. Returns True if the request is within the limit."""
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, window_seconds)
    return current <= limit
