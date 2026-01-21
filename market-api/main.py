"""FastAPI application for market data APIs."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException

from pytm_shared.cache_config import load_cache_settings
from pytm_shared.redis_repository import configure_cache, get_redis_client


logger = logging.getLogger(__name__)
app = FastAPI()


@app.on_event("startup")
async def configure_application() -> None:
    """Load cache settings and configure the shared Redis client."""
    settings = load_cache_settings()
    configure_cache(settings)
    logger.info("Market API configured", extra={"redis_uri": settings.cache_uri})


@app.get("/")
async def main() -> dict[str, str]:
    return {"message": "Market API is running"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Verify Redis connectivity via ping."""
    try:
        client = await get_redis_client()
        await client.ping()
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("Redis health check failed", extra={"error": str(exc)})
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc

    return {"status": "healthy"}
