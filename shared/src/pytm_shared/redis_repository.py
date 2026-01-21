"""Redis client management and base repository helpers."""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

import redis.asyncio as redis
from opentelemetry import trace

from .cache_config import CacheSettings

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

_redis_instance: redis.Redis | None = None
_redis_lock = asyncio.Lock()
_cache_settings: CacheSettings | None = None


def configure_cache(settings: CacheSettings) -> None:
    global _cache_settings
    _cache_settings = settings
    logger.info("Cache settings configured", extra={"cache_uri": settings.cache_uri})


async def get_redis_client() -> redis.Redis:
    """Return a singleton Redis client instance."""
    if _cache_settings is None:
        raise RuntimeError("Cache settings must be configured before use")
    global _redis_instance
    if _redis_instance is None:
        async with _redis_lock:
            if _redis_instance is None:
                logger.info(
                    "Creating Redis client",
                    extra={"cache_uri": _cache_settings.cache_uri},
                )
                _redis_instance = redis.from_url(
                    _cache_settings.cache_uri, decode_responses=True
                )
    return _redis_instance


class RedisRepository:
    """Convenience wrapper around redis operations used by repositories."""

    def __init__(
        self, settings: CacheSettings, client: redis.Redis | None = None
    ) -> None:
        self._settings = settings
        self._client = client

    async def _client_or_default(self) -> redis.Redis:
        if self._client is not None:
            return self._client
        return await get_redis_client()

    async def lpush_with_trim(
        self,
        key: str,
        value: str,
        max_length: int,
        ttl_seconds: int,
    ) -> None:
        client = await self._client_or_default()
        with tracer.start_as_current_span(
            "redis.lpush_trim",
            attributes={
                "redis.key": key,
                "redis.max_length": max_length,
                "redis.ttl_seconds": ttl_seconds,
            },
        ):
            async with client.pipeline(transaction=True) as pipe:
                pipe.lpush(key, value)
                pipe.ltrim(key, 0, max_length - 1)
                pipe.expire(key, ttl_seconds)
                result = await pipe.execute()
        logger.debug(
            "Updated Redis list", extra={"key": key, "pipeline_result": result}
        )

    async def lrange(self, key: str, start: int, end: int) -> list[str]:
        client = await self._client_or_default()
        with tracer.start_as_current_span(
            "redis.lrange",
            attributes={
                "redis.key": key,
                "redis.start": start,
                "redis.end": end,
            },
        ):
            values = await client.lrange(key, start, end)
        logger.debug("Fetched Redis list", extra={"key": key, "count": len(values)})
        return values

    async def scan_keys(self, pattern: str, count: int) -> AsyncIterator[list[str]]:
        client = await self._client_or_default()
        cursor: int = 0
        while True:
            with tracer.start_as_current_span(
                "redis.scan",
                attributes={
                    "redis.pattern": pattern,
                    "redis.count": count,
                },
            ):
                cursor, keys = await client.scan(
                    cursor=cursor, match=pattern, count=count
                )
            if keys:
                logger.debug(
                    "Scan batch", extra={"pattern": pattern, "batch_size": len(keys)}
                )
                yield keys
            if cursor == 0:
                break

    def build_market_data_key(self, security_id: str, packet_type: int) -> str:
        return f"{self._settings.key_prefix}:{security_id}:{packet_type}"
