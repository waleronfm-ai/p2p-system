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
    snapshot_at: datetime = Field(..., description="Время сбора снапшота трекером (UTC)")


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
    p25: float | None = None
    p75: float | None = None


class ChartResponse(BaseModel):
    """Данные для графика цены."""
    exchange: str
    pair: str
    mode: str
    hours: int
    points: list[ChartPoint]
    total_points: int


class ChartPointAgg(BaseModel):
    """Агрегированная точка графика: обе стороны рынка за временное окно."""
    ts: int = Field(..., description="UNIX-секунды UTC")
    buy_price: float = Field(..., description="Медиана BUY-ордеров в окне")
    sell_price: float = Field(..., description="Медиана SELL-ордеров в окне")
    buy_p25: float | None = None
    buy_p75: float | None = None
    sell_p25: float | None = None
    sell_p75: float | None = None


class ChartAggResponse(BaseModel):
    """Агрегированный график с обеими сторонами рынка."""
    timeframe: str
    points: list[ChartPointAgg]
    insufficient_data: bool


class TimeframesResponse(BaseModel):
    """Доступные таймфреймы по объёму истории."""
    available: list[str]
    disabled: list[str]


# ---------------------------------------------------------------------------
# Trade Journal
# ---------------------------------------------------------------------------

class TradeCreate(BaseModel):
    exchange: str = Field("binance", description="binance / bybit")
    order_id: str = Field(..., description="Номер ордера с биржи")
    trade_type: str = Field(..., description="BUY — купил USDT, SELL — продал USDT")
    price: float = Field(..., gt=0, description="Курс UAH за 1 USDT")
    amount_usdt: float = Field(..., gt=0, description="Количество USDT")
    amount_uah: float = Field(..., gt=0, description="Сумма UAH")
    bank: str | None = Field(None, description="Банк контрагента, например Monobank")
    counterparty: str | None = Field(None, description="Ник контрагента")
    note: str | None = Field(None, description="Произвольный комментарий")
    executed_at: datetime = Field(..., description="Время сделки на бирже (UTC)")


class TradeOut(BaseModel):
    id: int
    exchange: str
    order_id: str
    trade_type: str
    price: float
    amount_usdt: float
    amount_uah: float
    bank: str | None
    counterparty: str | None
    note: str | None
    executed_at: datetime
    created_at: datetime
    session_id: int | None = None

    model_config = {"from_attributes": True}


class TradeStats(BaseModel):
    total_trades: int
    buy_count: int
    sell_count: int
    total_usdt_bought: float
    total_usdt_sold: float
    total_uah_spent: float
    total_uah_received: float
    avg_buy_price: float | None
    avg_sell_price: float | None
    pnl_uah: float | None = Field(None, description="Реализованный P&L: sell_uah - sell_usdt * avg_buy_price")


class PositionResponse(BaseModel):
    usdt_balance: float = Field(..., description="Текущий остаток USDT (BUY - SELL)")
    avg_buy_price: float | None = Field(None, description="Средневзвешенная цена покупки (UAH за USDT)")
    break_even: float | None = Field(None, description="Точка безубыточности (= avg_buy_price)")
    realized_profit_uah: float | None = Field(None, description="Реализованная прибыль UAH по всем продажам")
    total_trades: int
    buy_count: int
    sell_count: int


# ---------------------------------------------------------------------------
# Opportunities (Шаг 7А)
# ---------------------------------------------------------------------------

class OpportunityItem(BaseModel):
    price: float
    available_amount: float
    min_amount: float
    max_amount: float
    exchange: str
    pair: str
    profit_per_usdt: float = Field(..., description="Прибыль/экономия за 1 USDT: exit = price - break_even, entry = reference - price")
    maker: MakerInfo
    banks: list[BankInfo]
    snapshot_at: datetime


class OpportunitiesResponse(BaseModel):
    mode: str = Field(..., description="entry или exit")
    reference_price: float = Field(..., description="Опорная цена: медиана топ-5 для entry, break_even для exit")
    threshold_price: float = Field(..., description="Пороговая цена: entry — reference*(1 - discount%), exit — break_even + target_profit")
    opportunities: list[OpportunityItem]


# ---------------------------------------------------------------------------
# Trade Sessions (Шаг 9)
# ---------------------------------------------------------------------------

class SessionCreate(BaseModel):
    start_capital_uah: float = Field(..., gt=0, description="Стартовый капитал в ₴")
    exchange: str = Field("binance", description="binance / bybit")


class SessionOut(BaseModel):
    id: int
    number: int
    start_capital_uah: float
    exchange: str
    status: str = Field(..., description="active / closed")
    started_at: datetime
    closed_at: datetime | None = None
    close_sell_price: float | None = None
    realized_uah: float | None = None
    unrealized_uah: float | None = None
    usdt_remaining: float | None = None
    trade_count: int = Field(0, description="Число сделок привязанных к сессии")

    model_config = {"from_attributes": True}


class SessionDetail(SessionOut):
    trades: list[TradeOut] = Field(default_factory=list)
