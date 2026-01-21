# Paytm Money WebSocket Client with Aspire Orchestration

This repository contains a Python 3.14+ application that connects to Paytm Money's live market data WebSocket, enriches the telemetry with OpenTelemetry, and persists recent market snapshots into Redis. The project is hosted locally via .NET Aspire, which orchestrates the Python service, Redis, and distributed observability tooling.

## High-Level Architecture

- **Shared Package (`shared/`)**
  - `pytm-shared`: A reusable local UV package containing Redis utilities, Pydantic models, and cache configuration.
  - Includes `cache_config.py`, `redis_repository.py`, `market_data_store.py`, and `models.py` for modular reuse across projects.

- **Aspire AppHost (`apphost.cs`)**
  - Spins up the Python application alongside a Redis cache instance.
  - Injects required environment variables (WebSocket token, Redis URI, TTL configuration, etc.).
  - Optionally enables Redis Insight and persistence for local debugging.

- **Python Application (`py-app/`)**
  - `main.py` bootstraps OpenTelemetry, logging, cache settings, and runs the WebSocket client.
  - `paytm_websocket.py` subscribes to desired instruments, parses binary packets into Pydantic models, and logs structured events with Redis storage.
  - `telemetry.py` configures OTLP exporters so logs, traces, and metrics are viewable inside the Aspire dashboard.
  - References `pytm-shared` for Redis operations, ensuring code reusability.

## Key Features

- **Structured Observability**: Uses OpenTelemetry for logs, traces, and metrics. When run via Aspire, telemetry automatically flows to the local dashboard.
- **Redis-backed Market Snapshots**: Each WebSocket update is serialized to JSON and stored in Redis under a human-readable key (e.g., `market:SECURITY_ID:PACKET_TYPE`). Entries auto-expire after 5 minutes, and lists are trimmed to the most recent 25 updates (configurable).
- **Async, Modular Design**: The WebSocket client and Redis repository are async-first, enabling high-throughput streaming, and are designed for extension (future data types can reuse the same repository helpers).
- **Configurable via Env Vars**: All cache-related tuning—TTL, snapshot count, scan batch size, and key prefix—are injected by Aspire, keeping the Python code clean and testable.
- **Rich Logging & Tracing**: Every Redis write/read and WebSocket packet flows through OpenTelemetry spans with structured logs, so the Aspire dashboard shows cache operations alongside WebSocket activity.

## Getting Started

1. Ensure .NET Aspire 13.1+, Python 3.14+, and UV are installed.
2. Provide a valid Paytm Money `PUBLIC_ACCESS_TOKEN` when running Aspire (via parameter or user secret).
3. Install dependencies:
   - From `py-app/`: Run `uv sync` to install `pytm-shared` and other deps (UV resolves the local shared package automatically).
4. From the repository root, run:
   ```bash
   aspire run
   ```
   Aspire will launch the Redis container, the Python WebSocket app, and the observability dashboard.
5. Open the Aspire dashboard URL shown in the console to monitor structured logs, traces, and metrics in real time.

## Customization

- Update `shared/` to modify Redis utilities, Pydantic models, or cache config—changes propagate to all referencing projects.
- Update `apphost.cs` to add/remove subscriptions, tweak Redis persistence, or enable additional exporters.
- Modify `py-app/main.py` or `paytm_websocket.py` to add new instruments, extra logging, or downstream consumers.
- Adjust cache tuning by editing the environment variables inside `apphost.cs` (e.g., keep more than 25 snapshots or change TTL).
- Toggle logging verbosity by setting `LOG_LEVEL` (if desired) and inspect Redis spans/logs in the Aspire dashboard for troubleshooting.

## Future Enhancements

- Surface REST or GraphQL endpoints that read the Redis snapshots for downstream consumers.
- Add analytics or LLM-facing modules that summarize the cached time series.
- Integrate authentication/authorization around WebSocket access and cache introspection.

This setup provides a solid foundation for building richer market-data services while retaining full insight through Aspire’s local dashboard.
