import json
from datetime import datetime
from decimal import Decimal
from typing import Any

import redis.asyncio as redis

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
   
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
    return _redis_client


async def close_redis_client() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None


def _json_default(obj: Any) -> Any:

    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class RedisCache:

    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    async def get(self, key: str) -> dict | list | None:
        try:
            raw = await self._client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as e:
            logger.warning("cache_read_failed", key=key, error=str(e))
            return None

    async def set(self, key: str, value: dict | list, ttl_seconds: int) -> None:
        try:
            serialized = json.dumps(value, default=_json_default)
            await self._client.set(key, serialized, ex=ttl_seconds)
        except Exception as e:
            logger.warning("cache_write_failed", key=key, error=str(e))

    async def delete_pattern(self, pattern: str) -> None:
       
        try:
            keys = [k async for k in self._client.scan_iter(match=pattern)]
            if keys:
                await self._client.delete(*keys)
                logger.info("cache_invalidated", pattern=pattern, count=len(keys))
        except Exception as e:
            logger.warning("cache_invalidate_failed", pattern=pattern, error=str(e))
