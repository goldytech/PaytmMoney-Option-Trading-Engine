from typing import List, Union
from pydantic import BaseModel


class BaseMarketData(BaseModel):
    """Base class for all market data types."""
    packet_type: int
    security_id: int
    tradable: int
    mode: int


class MarketDepth(BaseModel):
    buy_quantity: int
    sell_quantity: int
    buy_orders: int
    sell_orders: int
    buy_price: float
    sell_price: float


class LTP(BaseMarketData):
    packet_type: int = 61
    last_price: float
    last_trade_time: int
    change_absolute: float
    change_percent: float


class Quote(BaseMarketData):
    packet_type: int = 62
    last_price: float
    last_trade_time: int
    last_traded_quantity: int
    average_traded_price: float
    volume_traded: int
    total_buy_quantity: int
    total_sell_quantity: int
    open: float
    close: float
    high: float
    low: float
    change_percent: float
    change_absolute: float
    week52_high: float
    week52_low: float


class Full(BaseMarketData):
    packet_type: int = 63
    market_depth: List[MarketDepth]
    last_price: float
    last_trade_time: int
    last_traded_quantity: int
    average_traded_price: float
    volume_traded: int
    total_buy_quantity: int
    total_sell_quantity: int
    open: float
    close: float
    high: float
    low: float
    change_percent: float
    change_absolute: float
    week52_high: float
    week52_low: float
    oi: int
    change_oi: int


class IndexLTP(BaseMarketData):
    packet_type: int = 64
    last_price: float
    last_update_time: int
    change_absolute: float
    change_percent: float


class IndexQuote(BaseMarketData):
    packet_type: int = 65
    last_price: float
    open: float
    close: float
    high: float
    low: float
    change_percent: float
    change_absolute: float
    week52_high: float
    week52_low: float


class IndexFull(BaseMarketData):
    packet_type: int = 66
    last_price: float
    open: float
    close: float
    high: float
    low: float
    change_percent: float
    change_absolute: float
    last_trade_time: int


MarketData = Union[LTP, Quote, Full, IndexLTP, IndexQuote, IndexFull]