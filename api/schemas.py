from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MakerInfo(BaseModel):
    nickname: str
    total_orders: int
    completion_rate: float
    is_merchant: bool
    trust_level: str = Field(..., description="expert / normal / novice / unknown")


class BankInfo(BaseModel):
    name: str
    risk: str = Field(..., description="safe / caution / avoid / unknown")


class MarketOrder(BaseModel):
    """Один ордер на рынке."""
    price: float = Field(..., description="Цена в фиате за единицу крипты")
    available_amount: float = Field(..., description="Доступное количество крипты")
    min_amount: float = Field(..., description="Минимальная сумма сделки в фиате")
    max_amount: float = Field(..., description="Максимальная сумма сделки в фиате")
    exchange: str
    pair: str = Field(..., description="Пара, например USDT/UAH")
    mode: str = Field(..., description="buy = мейкер продаёт нам, sell = мейкер покупает у нас")
    maker: MakerInfo
    banks: list[BankInfo] = Field(default_factory=list, description="Банки мейкера")
    is_outlier: bool = Field(default=False, description="Помечен как выброс")


class PairSummary(BaseModel):
    exchange: str
    pair: str
    mode: str = Field(..., description="buy / sell")
    snapshots: int
    orders_total: int
    price_min: float | None = None
    price_max: float | None = None
    price_avg: float | None = None
    price_now: float | None = None


class SpreadInfo(BaseModel):
    pair: str
    mode: str
    binance_price: float | None = None
    bybit_price: float | None = None
    spread: float | None = Field(None, description="binance_price - bybit_price")


class SummaryResponse(BaseModel):
    hours: int | None = None
    pairs: list[PairSummary]
    spreads: list[SpreadInfo]


class OutlierMaker(BaseModel):
    exchange: str
    pair: str
    mode: str
    nickname: str
    appearances: int
    price_min: float
    price_max: float
    volume_median: float


class OutliersResponse(BaseModel):
    hours: int | None = None
    pair: str | None = None
    mode: str | None = None
    total_orders: int
    total_outliers: int
    outlier_pct: float
    makers: list[OutlierMaker]


class BankListItem(BaseModel):
    name: str
    risk: str = Field(..., description="safe / caution / avoid / unknown")
    bybit_ids: list[str]
    binance_keys: list[str]


class BanksResponse(BaseModel):
    total: int
    banks: list[BankListItem]


class MakerDetail(BaseModel):
    """Подробная информация о мейкере."""
    id: int
    exchange: str
    external_id: str
    nickname: str
    total_orders: int
    completion_rate: float
    is_merchant: bool
    trust_level: str = Field(..., description="expert / normal / novice / unknown")
    first_seen: datetime
    last_seen: datetime


class ChartPoint(BaseModel):
    """Одна точка на графике цены."""
    timestamp: datetime
    price: float
    snapshot_id: int


class ChartResponse(BaseModel):
    """Данные для графика цены."""
    exchange: str
    pair: str
    mode: str
    hours: int
    points: list[ChartPoint]
    total_points: int
