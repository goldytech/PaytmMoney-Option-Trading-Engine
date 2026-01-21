"""Runtime configuration helpers for cache-related settings."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class CacheSettings:
    cache_uri: str
    ttl_seconds: int
    max_snapshots: int
    scan_batch_size: int
    key_prefix: str


def load_cache_settings() -> CacheSettings:
    return CacheSettings(
        cache_uri=os.environ["CACHE_URI"],
        ttl_seconds=int(os.environ["MARKET_DATA_TTL_SECONDS"]),
        max_snapshots=int(os.environ["MARKET_DATA_MAX_SNAPSHOTS"]),
        scan_batch_size=int(os.environ["MARKET_DATA_SCAN_BATCH_SIZE"]),
        key_prefix=os.environ["MARKET_DATA_KEY_PREFIX"],
    )
