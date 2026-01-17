"""Repository for storing and retrieving market data snapshots in Redis."""

from __future__ import annotations

import logging
from typing import Iterable

from opentelemetry import trace
from pydantic import TypeAdapter

from cache_config import CacheSettings
from models import MarketData
from redis_repository import RedisRepository

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)
_market_data_adapter = TypeAdapter(MarketData)


class MarketDataStore:
    """Store and retrieve market data snapshots with TTL management."""

    def __init__(
        self,
        settings: CacheSettings,
        repository: RedisRepository | None = None,
    ) -> None:
        self._settings = settings
        self._repository = repository or RedisRepository(settings)

    async def save_snapshot(self, market_data: MarketData) -> None:
        key = self._repository.build_market_data_key(
            security_id=str(market_data.security_id),
            packet_type=market_data.packet_type,
        )
        payload = _market_data_adapter.dump_json(market_data, by_alias=True)
        with tracer.start_as_current_span(
            "market_data.save",
            attributes={
                "market.security_id": market_data.security_id,
                "market.packet_type": market_data.packet_type,
                "redis.key": key,
            },
        ):
            await self._repository.lpush_with_trim(
                key=key,
                value=payload if isinstance(payload, str) else payload.decode(),
                max_length=self._settings.max_snapshots,
                ttl_seconds=self._settings.ttl_seconds,
            )
        logger.info(
            "Stored market data snapshot",
            extra={
                "redis_key": key,
                "security_id": market_data.security_id,
                "packet_type": market_data.packet_type,
            },
        )

    async def fetch_recent_snapshots(self, pattern: str) -> list[MarketData]:
        results: list[MarketData] = []
        with tracer.start_as_current_span(
            "market_data.fetch",
            attributes={"redis.pattern": pattern},
        ):
            async for keys in self._repository.scan_keys(
                pattern=pattern,
                count=self._settings.scan_batch_size,
            ):
                for key in keys:
                    raw_entries = await self._repository.lrange(
                        key, 0, self._settings.max_snapshots - 1
                    )
                    results.extend(self._deserialize_entries(raw_entries))
        results.sort(key=lambda data: getattr(data, "last_trade_time", 0), reverse=True)
        logger.info(
            "Retrieved market data snapshots",
            extra={"pattern": pattern, "count": len(results)},
        )
        return results[: self._settings.max_snapshots]

    @staticmethod
    def _deserialize_entries(raw_entries: Iterable[str]) -> list[MarketData]:
        snapshots: list[MarketData] = []
        for entry in raw_entries:
            try:
                snapshots.append(_market_data_adapter.validate_json(entry))
            except ValueError:
                continue
        return snapshots
