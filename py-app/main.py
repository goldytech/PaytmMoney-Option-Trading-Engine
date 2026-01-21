import asyncio
import json
import os
import logging
from opentelemetry.sdk._logs import LoggingHandler
from paytm_websocket import PaytmWebSocketClient
from telemetry import configure_opentelemetry
from pytm_shared.market_data_store import MarketDataStore
from pytm_shared.cache_config import load_cache_settings
from pytm_shared.redis_repository import configure_cache


STANDARD_LOG_RECORD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
}


_LOG_RECORD_FACTORY_INSTALLED = False


def install_extra_context_record_factory() -> None:
    global _LOG_RECORD_FACTORY_INSTALLED
    if _LOG_RECORD_FACTORY_INSTALLED:
        return

    previous_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):  # type: ignore[override]
        record = previous_factory(*args, **kwargs)
        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in STANDARD_LOG_RECORD_ATTRS and not key.startswith("_")
        }
        if extra:
            base_message = record.getMessage()
            try:
                serialized = json.dumps(extra, default=str, separators=(",", ":"))
                record.extra_json = serialized
            except (TypeError, ValueError):
                record.extra_json = json.dumps(
                    {key: str(value) for key, value in extra.items()},
                    separators=(",", ":"),
                )
        else:
            record.extra_json = "{}"

        return record

    logging.setLogRecordFactory(record_factory)
    _LOG_RECORD_FACTORY_INSTALLED = True


# Configure console logging (OpenTelemetry logging is configured in telemetry.py)
def setup_logging() -> None:
    """Ensure console handlers emit plain messages for Aspire structured logs."""
    install_extra_context_record_factory()

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter(fmt="%(message)s | extra=%(extra_json)s")

    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, LoggingHandler
        ):
            handler.setFormatter(formatter)

    has_console_handler = any(
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, LoggingHandler)
        for handler in root_logger.handlers
    )
    if not has_console_handler:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)


def main():
    # Configure telemetry
    configure_opentelemetry()

    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Get access token (hardcoded for now)
    token = os.getenv("PUBLIC_ACCESS_TOKEN")
    if not token:
        logger.error("PUBLIC_ACCESS_TOKEN environment variable is not set")
        return
    logger.info(
        "Starting Paytm Money WebSocket client",
        extra={"token_length": len(token)},
    )

    # Initialize cache settings
    cache_settings = load_cache_settings()
    configure_cache(cache_settings)

    try:
        # Create WebSocket client
        market_data_store = MarketDataStore(cache_settings)
        client = PaytmWebSocketClient(token, market_data_store=market_data_store)

        # Add subscriptions (example: Nifty 50 index)
        client.add_subscription("ADD", "FULL", "INDEX", "NSE", "13")

        # You can add more subscriptions here
        # client.add_subscription("ADD", "LTP", "EQUITY", "NSE", "1234")

        logger.info(
            "Connecting to WebSocket",
            extra={"subscription_count": len(client.subscriptions)},
        )

        # Connect and start listening
        asyncio.run(client.connect())

    except Exception as error:
        logger.error(
            "Application error",
            extra={"error": str(error), "error_type": type(error).__name__},
        )
        raise


if __name__ == "__main__":
    main()
