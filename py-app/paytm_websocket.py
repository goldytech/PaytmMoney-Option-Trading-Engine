import websockets
import json
import struct
import logging
import logging
from typing import Any, Dict, List, Optional

from opentelemetry import trace

from pytm_shared.models import (
    BaseMarketData,
    MarketDepth,
    LTP,
    Quote,
    Full,
    IndexLTP,
    IndexQuote,
    IndexFull,
    MarketData,
)
from pytm_shared.market_data_store import MarketDataStore

tracer = trace.get_tracer(__name__)


class PaytmWebSocketClient:
    """WebSocket client for Paytm Money live market data streaming."""

    def __init__(self, token: str, market_data_store: MarketDataStore) -> None:
        self.logger = logging.getLogger(__name__)
        self.token = token
        self.market_data_store = market_data_store
        self.url_no_token = "wss://developer-ws.paytmmoney.com/broadcast/user/v1/data"
        self.url = f"{self.url_no_token}?x_jwt_token={token}"
        self.logger.debug(
            "WebSocket URL constructed",
            extra={"url": self.url, "token_length": len(token)},
        )
        self.subscriptions: List[Dict[str, Any]] = []
        self.websocket: Optional[Any] = None

    def add_subscription(
        self, action: str, mode: str, scrip_type: str, exchange: str, scrip_id: str
    ):
        """
        Add a subscription preference.

        Args:
            action: "ADD" or "REMOVE"
            mode: "LTP", "QUOTE", "FULL"
            scrip_type: "INDEX", "EQUITY", "ETF", "FUTURE", "OPTION"
            exchange: "NSE", "BSE"
            scrip_id: The scrip ID
        """
        self.subscriptions.append(
            {
                "actionType": action,
                "modeType": mode,
                "scripType": scrip_type,
                "exchangeType": exchange,
                "scripId": scrip_id,
            }
        )

    async def connect(self):
        """
        Connect to the WebSocket and start listening for messages.
        """
        try:
            async with websockets.connect(self.url) as websocket:
                self.websocket = websocket
                self.logger.info(
                    "Connected to Paytm Money WebSocket", extra={"url": self.url}
                )

                # Send subscriptions
                if self.subscriptions:
                    await self._subscribe()

                # Listen for messages
                async for message in websocket:
                    if isinstance(message, bytes):
                        parsed_data = self.parse_message(message)
                        for data in parsed_data:
                            with tracer.start_as_current_span(
                                "websocket.message",
                                attributes={
                                    "market.security_id": data.security_id,
                                    "market.packet_type": data.packet_type,
                                },
                            ):
                                self.logger.info(
                                    "Received market data",
                                    extra={
                                        "security_id": data.security_id,
                                        "packet_type": data.packet_type,
                                        "last_price": getattr(data, "last_price", None),
                                    },
                                )
                                try:
                                    await self.market_data_store.save_snapshot(data)
                                except Exception as error:
                                    self.logger.error(
                                        "Failed to store market data",
                                        extra={
                                            "error": str(error),
                                            "security_id": data.security_id,
                                        },
                                    )
                                    raise

                    else:
                        self.logger.warning(
                            "Received text message", extra={"message": message}
                        )

        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg:
                self.logger.error(
                    "WebSocket authentication failed. Please check that ACCESS_TOKEN is valid.",
                    extra={"error": error_msg, "error_type": type(e).__name__},
                )
            elif "InvalidStatus" in str(type(e)):
                self.logger.error(
                    "WebSocket connection rejected by server",
                    extra={"error": error_msg, "error_type": type(e).__name__},
                )
            else:
                self.logger.error(
                    "Connection error",
                    extra={"error": error_msg, "error_type": type(e).__name__},
                )

    async def _subscribe(self):
        """Send subscription preferences to the server."""
        assert self.websocket is not None, "WebSocket connection not established"
        subscription_data = json.dumps(self.subscriptions)
        self.logger.info(
            "Sending subscription", extra={"subscription_data": subscription_data}
        )
        await self.websocket.send(subscription_data)
        self.logger.info(
            "Subscribed to instruments",
            extra={
                "subscription_count": len(self.subscriptions),
                "subscriptions": self.subscriptions,
            },
        )

    def parse_binary_message(self, data: bytes) -> List[MarketData]:
        """
        Parse binary WebSocket message data into structured market data models.

        This is the unified method to parse any binary message from the WebSocket.

        Args:
            data: The binary data received from the WebSocket

        Returns:
            List of parsed market data models
        """
        return self.parse_message(data)

    def parse_message(self, data: bytes) -> List[MarketData]:
        """Parse binary message data and return structured market data."""
        parsed_data: List[MarketData] = []

        pos = 0
        while pos < len(data):
            if pos + 1 > len(data):
                break
            packet_type = data[pos]
            pos += 1

            try:
                if packet_type == 61:  # LTP
                    model = self._parse_ltp(data, pos)
                    parsed_data.append(model)
                    pos += 22
                elif packet_type == 62:  # QUOTE
                    model = self._parse_quote(data, pos)
                    parsed_data.append(model)
                    pos += 66
                elif packet_type == 63:  # FULL
                    model = self._parse_full(data, pos)
                    parsed_data.append(model)
                    pos += 174
                elif packet_type == 64:  # INDEX LTP
                    model = self._parse_index_ltp(data, pos)
                    parsed_data.append(model)
                    pos += 22
                elif packet_type == 65:  # INDEX QUOTE
                    model = self._parse_index_quote(data, pos)
                    parsed_data.append(model)
                    pos += 42
                elif packet_type == 66:  # INDEX FULL
                    model = self._parse_index_full(data, pos)
                    parsed_data.append(model)
                    pos += 38
                else:
                    self.logger.warning(
                        "Unknown packet type received",
                        extra={"packet_type": packet_type},
                    )
                    break
            except struct.error as e:
                self.logger.error(
                    "Error parsing packet",
                    extra={"error": str(e), "error_type": type(e).__name__},
                )
                break

        return parsed_data

    def _parse_ltp(self, data: bytes, pos: int) -> LTP:
        """Parse LTP packet."""
        last_price = struct.unpack("<f", data[pos : pos + 4])[0]
        last_trade_time = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        security_id = struct.unpack("<I", data[pos + 8 : pos + 12])[0]
        tradable = data[pos + 12]
        mode = data[pos + 13]
        change_abs = struct.unpack("<f", data[pos + 14 : pos + 18])[0]
        change_pct = struct.unpack("<f", data[pos + 18 : pos + 22])[0]

        return LTP(
            last_price=last_price,
            last_trade_time=last_trade_time,
            security_id=security_id,
            tradable=tradable,
            mode=mode,
            change_absolute=change_abs,
            change_percent=change_pct,
        )

    def _parse_quote(self, data: bytes, pos: int) -> Quote:
        """Parse QUOTE packet."""
        last_price = struct.unpack("<f", data[pos : pos + 4])[0]
        last_trade_time = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        security_id = struct.unpack("<I", data[pos + 8 : pos + 12])[0]
        tradable = data[pos + 12]
        mode = data[pos + 13]
        last_traded_qty = struct.unpack("<I", data[pos + 14 : pos + 18])[0]
        avg_traded_price = struct.unpack("<f", data[pos + 18 : pos + 22])[0]
        volume = struct.unpack("<I", data[pos + 22 : pos + 26])[0]
        total_buy_qty = struct.unpack("<I", data[pos + 26 : pos + 30])[0]
        total_sell_qty = struct.unpack("<I", data[pos + 30 : pos + 34])[0]
        open_price = struct.unpack("<f", data[pos + 34 : pos + 38])[0]
        close_price = struct.unpack("<f", data[pos + 38 : pos + 42])[0]
        high = struct.unpack("<f", data[pos + 42 : pos + 46])[0]
        low = struct.unpack("<f", data[pos + 46 : pos + 50])[0]
        change_pct = struct.unpack("<f", data[pos + 50 : pos + 54])[0]
        change_abs = struct.unpack("<f", data[pos + 54 : pos + 58])[0]
        week52_high = struct.unpack("<f", data[pos + 58 : pos + 62])[0]
        week52_low = struct.unpack("<f", data[pos + 62 : pos + 66])[0]

        return Quote(
            last_price=last_price,
            last_trade_time=last_trade_time,
            security_id=security_id,
            tradable=tradable,
            mode=mode,
            last_traded_quantity=last_traded_qty,
            average_traded_price=avg_traded_price,
            volume_traded=volume,
            total_buy_quantity=total_buy_qty,
            total_sell_quantity=total_sell_qty,
            open=open_price,
            close=close_price,
            high=high,
            low=low,
            change_percent=change_pct,
            change_absolute=change_abs,
            week52_high=week52_high,
            week52_low=week52_low,
        )

    def _parse_full(self, data: bytes, pos: int) -> Full:
        """Parse FULL packet."""
        # Market depth (5 levels)
        depth = []
        depth_pos = pos
        for i in range(5):
            buy_qty = struct.unpack("<I", data[depth_pos : depth_pos + 4])[0]
            sell_qty = struct.unpack("<I", data[depth_pos + 4 : depth_pos + 8])[0]
            buy_orders = struct.unpack("<H", data[depth_pos + 8 : depth_pos + 10])[0]
            sell_orders = struct.unpack("<H", data[depth_pos + 10 : depth_pos + 12])[0]
            buy_price = struct.unpack("<f", data[depth_pos + 12 : depth_pos + 16])[0]
            sell_price = struct.unpack("<f", data[depth_pos + 16 : depth_pos + 20])[0]
            depth.append(
                MarketDepth(
                    buy_quantity=buy_qty,
                    sell_quantity=sell_qty,
                    buy_orders=buy_orders,
                    sell_orders=sell_orders,
                    buy_price=buy_price,
                    sell_price=sell_price,
                )
            )
            depth_pos += 20

        pos += 100  # Skip depth

        last_price = struct.unpack("<f", data[pos : pos + 4])[0]
        last_trade_time = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        security_id = struct.unpack("<I", data[pos + 8 : pos + 12])[0]
        tradable = data[pos + 12]
        mode = data[pos + 13]
        last_traded_qty = struct.unpack("<I", data[pos + 14 : pos + 18])[0]
        avg_traded_price = struct.unpack("<f", data[pos + 18 : pos + 22])[0]
        volume = struct.unpack("<I", data[pos + 22 : pos + 26])[0]
        total_buy_qty = struct.unpack("<I", data[pos + 26 : pos + 30])[0]
        total_sell_qty = struct.unpack("<I", data[pos + 30 : pos + 34])[0]
        open_price = struct.unpack("<f", data[pos + 34 : pos + 38])[0]
        close_price = struct.unpack("<f", data[pos + 38 : pos + 42])[0]
        high = struct.unpack("<f", data[pos + 42 : pos + 46])[0]
        low = struct.unpack("<f", data[pos + 46 : pos + 50])[0]
        change_pct = struct.unpack("<f", data[pos + 50 : pos + 54])[0]
        change_abs = struct.unpack("<f", data[pos + 54 : pos + 58])[0]
        week52_high = struct.unpack("<f", data[pos + 58 : pos + 62])[0]
        week52_low = struct.unpack("<f", data[pos + 62 : pos + 66])[0]
        oi = struct.unpack("<I", data[pos + 66 : pos + 70])[0]
        change_oi = struct.unpack("<I", data[pos + 70 : pos + 74])[0]

        return Full(
            market_depth=depth,
            last_price=last_price,
            last_trade_time=last_trade_time,
            security_id=security_id,
            tradable=tradable,
            mode=mode,
            last_traded_quantity=last_traded_qty,
            average_traded_price=avg_traded_price,
            volume_traded=volume,
            total_buy_quantity=total_buy_qty,
            total_sell_quantity=total_sell_qty,
            open=open_price,
            close=close_price,
            high=high,
            low=low,
            change_percent=change_pct,
            change_absolute=change_abs,
            week52_high=week52_high,
            week52_low=week52_low,
            oi=oi,
            change_oi=change_oi,
        )

    def _parse_index_ltp(self, data: bytes, pos: int) -> IndexLTP:
        """Parse INDEX LTP packet."""
        last_price = struct.unpack("<f", data[pos : pos + 4])[0]
        last_update_time = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        security_id = struct.unpack("<I", data[pos + 8 : pos + 12])[0]
        tradable = data[pos + 12]
        mode = data[pos + 13]
        change_abs = struct.unpack("<f", data[pos + 14 : pos + 18])[0]
        change_pct = struct.unpack("<f", data[pos + 18 : pos + 22])[0]

        return IndexLTP(
            last_price=last_price,
            last_update_time=last_update_time,
            security_id=security_id,
            tradable=tradable,
            mode=mode,
            change_absolute=change_abs,
            change_percent=change_pct,
        )

    def _parse_index_quote(self, data: bytes, pos: int) -> IndexQuote:
        """Parse INDEX QUOTE packet."""
        last_price = struct.unpack("<f", data[pos : pos + 4])[0]
        security_id = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        tradable = data[pos + 8]
        mode = data[pos + 9]
        open_price = struct.unpack("<f", data[pos + 10 : pos + 14])[0]
        close_price = struct.unpack("<f", data[pos + 14 : pos + 18])[0]
        high = struct.unpack("<f", data[pos + 18 : pos + 22])[0]
        low = struct.unpack("<f", data[pos + 22 : pos + 26])[0]
        change_pct = struct.unpack("<f", data[pos + 26 : pos + 30])[0]
        change_abs = struct.unpack("<f", data[pos + 30 : pos + 34])[0]
        week52_high = struct.unpack("<f", data[pos + 34 : pos + 38])[0]
        week52_low = struct.unpack("<f", data[pos + 38 : pos + 42])[0]

        return IndexQuote(
            last_price=last_price,
            security_id=security_id,
            tradable=tradable,
            mode=mode,
            open=open_price,
            close=close_price,
            high=high,
            low=low,
            change_percent=change_pct,
            change_absolute=change_abs,
            week52_high=week52_high,
            week52_low=week52_low,
        )

    def _parse_index_full(self, data: bytes, pos: int) -> IndexFull:
        """Parse INDEX FULL packet."""
        last_price = struct.unpack("<f", data[pos : pos + 4])[0]
        security_id = struct.unpack("<I", data[pos + 4 : pos + 8])[0]
        tradable = data[pos + 8]
        mode = data[pos + 9]
        open_price = struct.unpack("<f", data[pos + 10 : pos + 14])[0]
        close_price = struct.unpack("<f", data[pos + 14 : pos + 18])[0]
        high = struct.unpack("<f", data[pos + 18 : pos + 22])[0]
        low = struct.unpack("<f", data[pos + 22 : pos + 26])[0]
        change_pct = struct.unpack("<f", data[pos + 26 : pos + 30])[0]
        change_abs = struct.unpack("<f", data[pos + 30 : pos + 34])[0]
        last_trade_time = struct.unpack("<I", data[pos + 34 : pos + 38])[0]

        return IndexFull(
            last_price=last_price,
            security_id=security_id,
            tradable=tradable,
            mode=mode,
            open=open_price,
            close=close_price,
            high=high,
            low=low,
            change_percent=change_pct,
            change_absolute=change_abs,
            last_trade_time=last_trade_time,
        )
