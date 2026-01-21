"""FastAPI application for market data APIs."""

from __future__ import annotations

import logging

import redis.asyncio as redis
from fastapi import Depends, FastAPI, HTTPException

from pytm_shared.cache_config import load_cache_settings
from pytm_shared.redis_repository import configure_cache, get_redis_client


logger = logging.getLogger(__name__)
app = FastAPI()


async def get_configured_redis_client() -> redis.Redis:
    """Dependency to ensure Redis is configured and return the client."""
    try:
        settings = load_cache_settings()
        configure_cache(settings)
        client = await get_redis_client()
        await client.ping()  # Test connectivity
        return client
    except Exception as exc:
        logger.error(
            "Redis configuration or connectivity failed", extra={"error": str(exc)}
        )
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc


@app.get("/")
async def main() -> dict[str, str]:
    return {"message": "Market API is running"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Verify Redis connectivity via ping."""
    try:
        settings = load_cache_settings()
        configure_cache(settings)
        client = await get_redis_client()
        await client.ping()
        return {"status": "healthy"}
    except Exception as exc:
        logger.error("Redis health check failed", extra={"error": str(exc)})
        return {"status": "unhealthy", "detail": str(exc)}
