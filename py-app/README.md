# Paytm Money WebSocket Client

## Redis-backed market data snapshots

- Configure cache endpoint via `CACHE_URI` (set automatically by Aspire in `apphost.cs`).
- Optional tuning:
  - `MARKET_DATA_TTL_SECONDS` (default `300` seconds) controls auto-expiry.
  - `MARKET_DATA_MAX_SNAPSHOTS` (default `25`) caps per-security history.
  - `MARKET_DATA_SCAN_BATCH_SIZE` (default `200`) affects wildcard scan batches.
- New modules:
  - `cache_config.py`: loads cache/env settings.
  - `redis_repository.py`: async Redis client singleton + helper ops.
  - `market_data_store.py`: saves parsed `MarketData` models in Redis lists.
- Retrieval: wildcard patterns (e.g., `market:NIFTY_*`) return a flat list sorted by `last_trade_time`.
