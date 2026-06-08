"""AI-агент: POST /ai/analyze — аналитик P2P-торговли."""
from __future__ import annotations

import statistics
import threading
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from api.dependencies import require_api_key
from api.services.ai_service import AIServiceError, analyze
from api.services.market_service import get_chart_agg, get_orders
from core.database import Session, Trade, get_session

router = APIRouter(prefix="/ai", tags=["ai"])


# ── Простой in-memory rate limiter (без slowapi) ─────────────────────────────

_rl_lock = threading.Lock()
_rl_buckets: dict[str, list[datetime]] = defaultdict(list)
_RL_MAX = 10
_RL_WINDOW = timedelta(minutes=1)


def _rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = datetime.now(UTC)
    cutoff = now - _RL_WINDOW
    with _rl_lock:
        _rl_buckets[ip] = [t for t in _rl_buckets[ip] if t > cutoff]
        if len(_rl_buckets[ip]) >= _RL_MAX:
            raise HTTPException(429, detail="Слишком много запросов к AI. Лимит: 10 в минуту.")
        _rl_buckets[ip].append(now)


# ── Схемы запроса/ответа ──────────────────────────────────────────────────────

_PERIOD_CONFIG: dict[str, dict] = {
    "12h": {"timeframe": "12h", "bucket_sec": 1800,  "label": "12 часов"},
    "24h": {"timeframe": "24h", "bucket_sec": 3600,  "label": "24 часа"},
    "7d":  {"timeframe": "7d",  "bucket_sec": 21600, "label": "7 дней"},
    "30d": {"timeframe": "1m",  "bucket_sec": 86400, "label": "30 дней"},
}

_VALID_PERIODS = set(_PERIOD_CONFIG)


class AIAnalyzeRequest(BaseModel):
    mode: str
    exchange: str = "binance"
    period: str = "30d"


class AIAnalyzeResponse(BaseModel):
    mode: str
    analysis: str


# ── Сбор данных: режим "sessions" ─────────────────────────────────────────────

def _collect_sessions_payload(exchange: str) -> dict[str, Any] | None:
    """
    Возвращает payload для ai_service или None, если закрытых сессий нет.
    Берёт последние 5 закрытых сессий + сделки самой последней из них.
    """
    with get_session() as db:
        closed = db.scalars(
            select(Session)
            .where(Session.status == "closed")
            .order_by(Session.closed_at.desc())
            .limit(5)
        ).all()

        if not closed:
            return None

        sessions_data: list[dict] = []
        for s in closed:
            trades = db.scalars(
                select(Trade).where(Trade.session_id == s.id)
            ).all()

            buys = [t for t in trades if t.trade_type == "BUY"]
            sells = [t for t in trades if t.trade_type == "SELL"]
            usdt_bought = sum(t.amount_usdt for t in buys)
            uah_spent = sum(t.amount_uah for t in buys)
            usdt_sold = sum(t.amount_usdt for t in sells)
            uah_received = sum(t.amount_uah for t in sells)
            avg_buy = round(uah_spent / usdt_bought, 4) if usdt_bought else None

            duration_min: int | None = None
            if s.started_at and s.closed_at:
                duration_min = int((s.closed_at - s.started_at).total_seconds() / 60)

            sessions_data.append({
                "number": s.number,
                "status": s.status,
                "start_capital_uah": s.start_capital_uah,
                "exchange": s.exchange,
                "started_at": str(s.started_at)[:16],
                "closed_at": str(s.closed_at)[:16] if s.closed_at else None,
                "duration_minutes": duration_min,
                "close_sell_price": s.close_sell_price,
                "realized_uah": s.realized_uah,
                "unrealized_uah": s.unrealized_uah,
                "usdt_remaining": s.usdt_remaining,
                "trade_count": len(trades),
                "avg_buy_price": avg_buy,
                "usdt_bought": round(usdt_bought, 2),
                "uah_spent": round(uah_spent, 2),
                "usdt_sold": round(usdt_sold, 2),
                "uah_received": round(uah_received, 2),
            })

        # Сделки только самой последней сессии (для детального разбора)
        latest = closed[0]
        latest_trades_raw = db.scalars(
            select(Trade)
            .where(Trade.session_id == latest.id)
            .order_by(Trade.executed_at.asc())
        ).all()
        trades_data = [
            {
                "trade_type": t.trade_type,
                "price": t.price,
                "amount_usdt": t.amount_usdt,
                "amount_uah": t.amount_uah,
                "bank": t.bank,
                "executed_at": str(t.executed_at)[:16],
            }
            for t in latest_trades_raw
        ]

    # Текущий рынок
    market: dict[str, Any] = {}
    try:
        buy_orders = get_orders(pair="USDT/UAH", mode="buy", exchange=exchange, top=1)
        sell_orders = get_orders(pair="USDT/UAH", mode="sell", exchange=exchange, top=1)
        if buy_orders:
            market["buy_price"] = buy_orders[0].price
        if sell_orders:
            market["sell_price"] = sell_orders[0].price
    except Exception:
        pass

    return {"sessions": sessions_data, "trades": trades_data, "market": market}


# ── Сбор данных: режим "market" ───────────────────────────────────────────────

def _collect_market_payload(exchange: str, period: str) -> dict[str, Any]:
    """
    Агрегирует историю за выбранный период в компактные бакеты (~24-30 точек).

    period → timeframe → bucket_sec:
      12h  → get_chart_agg("12h") → 30-мин бакеты
      24h  → get_chart_agg("24h") → часовые бакеты
      7d   → get_chart_agg("7d")  → 6-часовые бакеты
      30d  → get_chart_agg("1m")  → дневные бакеты
    """
    cfg = _PERIOD_CONFIG[period]
    agg = get_chart_agg(pair="USDT/UAH", timeframe=cfg["timeframe"], exchange=exchange)

    if agg.insufficient_data or not agg.points:
        return {
            "summary": {},
            "chart": [],
            "note": f"Недостаточно истории за {cfg['label']}.",
        }

    # Схлопываем мелкие бакеты в бакеты нужного размера
    bucket_sec = cfg["bucket_sec"]
    bucket_buy: dict[int, list[float]] = defaultdict(list)
    bucket_sell: dict[int, list[float]] = defaultdict(list)
    for pt in agg.points:
        bk = (pt.ts // bucket_sec) * bucket_sec
        bucket_buy[bk].append(pt.buy_price)
        bucket_sell[bk].append(pt.sell_price)

    chart_points: list[dict] = []
    for bk in sorted(bucket_buy):
        chart_points.append({
            "ts": bk,
            "buy_price": round(statistics.median(bucket_buy[bk]), 4),
            "sell_price": round(statistics.median(bucket_sell[bk]), 4),
        })

    # Сводная статистика
    all_buy = [p["buy_price"] for p in chart_points]
    all_sell = [p["sell_price"] for p in chart_points]
    all_spreads = [p["sell_price"] - p["buy_price"] for p in chart_points]

    buy_min = round(min(all_buy), 4)
    buy_max = round(max(all_buy), 4)
    buy_avg = round(statistics.mean(all_buy), 4)
    sell_min = round(min(all_sell), 4)
    sell_max = round(max(all_sell), 4)
    sell_avg = round(statistics.mean(all_sell), 4)
    spread_avg = round(statistics.mean(all_spreads), 4)

    current_buy = chart_points[-1]["buy_price"]
    current_sell = chart_points[-1]["sell_price"]
    current_spread = round(current_sell - current_buy, 4)

    buy_range = buy_max - buy_min
    buy_position_pct = round((current_buy - buy_min) / buy_range * 100, 1) if buy_range else 50.0

    if buy_position_pct <= 25:
        buy_phase = "нижняя четверть диапазона"
    elif buy_position_pct <= 50:
        buy_phase = "нижняя половина диапазона"
    elif buy_position_pct <= 75:
        buy_phase = "верхняя половина диапазона"
    else:
        buy_phase = "верхняя четверть диапазона"

    summary = {
        "exchange": exchange,
        "pair": "USDT/UAH",
        "period_label": cfg["label"],
        "point_count": len(chart_points),
        "buy": {
            "current": current_buy,
            "min_p": buy_min,
            "max_p": buy_max,
            "avg_p": buy_avg,
            "position_pct": buy_position_pct,
            "phase": buy_phase,
        },
        "sell": {
            "current": current_sell,
            "min_p": sell_min,
            "max_p": sell_max,
            "avg_p": sell_avg,
        },
        "spread": {
            "current": current_spread,
            "avg_p": spread_avg,
            "vs_avg": round(current_spread - spread_avg, 4),
        },
    }

    return {"summary": summary, "chart": chart_points}


# ── Сбор данных: режим "position" ─────────────────────────────────────────────

def _range_stats(points: list) -> dict[str, float]:
    """min/max/avg по buy и sell из списка ChartPointAgg."""
    if not points:
        return {}
    buy = [p.buy_price for p in points]
    sell = [p.sell_price for p in points]
    spreads = [p.sell_price - p.buy_price for p in points]
    return {
        "buy_min":    round(min(buy), 4),
        "buy_max":    round(max(buy), 4),
        "buy_avg":    round(statistics.mean(buy), 4),
        "sell_min":   round(min(sell), 4),
        "sell_max":   round(max(sell), 4),
        "sell_avg":   round(statistics.mean(sell), 4),
        "spread_avg": round(statistics.mean(spreads), 4),
    }


def _collect_position_payload(exchange: str) -> dict[str, Any] | None:
    """
    Возвращает payload текущей открытой позиции или None, если активной сессии нет.

    Содержит:
      session  — мета сессии
      position — все метрики позиции (avg_buy, remaining, realized, break_even…)
      market   — текущий BUY/SELL + нереализованный P&L
      ranges   — диапазоны за 24ч и 7д для построения сценариев
      trades   — детальный список сделок сессии
    """
    with get_session() as db:
        session = db.scalars(
            select(Session).where(Session.status == "active").limit(1)
        ).first()

        if session is None:
            return None

        trades = db.scalars(
            select(Trade)
            .where(Trade.session_id == session.id)
            .order_by(Trade.executed_at.asc())
        ).all()

        buys  = [t for t in trades if t.trade_type == "BUY"]
        sells = [t for t in trades if t.trade_type == "SELL"]

        usdt_bought   = sum(t.amount_usdt for t in buys)
        uah_spent     = sum(t.amount_uah  for t in buys)
        usdt_sold     = sum(t.amount_usdt for t in sells)
        uah_received  = sum(t.amount_uah  for t in sells)
        usdt_remaining = round(usdt_bought - usdt_sold, 6)

        avg_buy: float | None = round(uah_spent / usdt_bought, 4) if usdt_bought else None
        break_even = avg_buy  # продать остаток по avg_buy → нулевой итог

        # Реализованный P&L: uah_received - usdt_sold * avg_buy
        realized_uah: float | None = None
        if avg_buy is not None and usdt_sold:
            realized_uah = round(uah_received - usdt_sold * avg_buy, 2)

        duration_min: int | None = None
        if session.started_at:
            duration_min = int(
                (datetime.now(UTC).replace(tzinfo=None) - session.started_at).total_seconds() / 60
            )

        session_meta = {
            "number":           session.number,
            "started_at":       str(session.started_at)[:16],
            "duration_minutes": duration_min,
            "start_capital_uah": session.start_capital_uah,
            "exchange":         session.exchange,
            "trade_count":      len(trades),
        }

        position = {
            "usdt_bought":    round(usdt_bought, 4),
            "uah_spent":      round(uah_spent, 2),
            "usdt_sold":      round(usdt_sold, 4),
            "uah_received":   round(uah_received, 2),
            "usdt_remaining": usdt_remaining,
            "avg_buy":        avg_buy,
            "break_even":     break_even,
            "realized_uah":   realized_uah,
        }

        trades_data = [
            {
                "trade_type":  t.trade_type,
                "price":       t.price,
                "amount_usdt": t.amount_usdt,
                "amount_uah":  t.amount_uah,
                "bank":        t.bank,
                "executed_at": str(t.executed_at)[:16],
            }
            for t in trades
        ]

    # Текущий рынок
    market: dict[str, Any] = {}
    try:
        buy_orders  = get_orders(pair="USDT/UAH", mode="buy",  exchange=exchange, top=1)
        sell_orders = get_orders(pair="USDT/UAH", mode="sell", exchange=exchange, top=1)
        current_buy  = buy_orders[0].price  if buy_orders  else None
        current_sell = sell_orders[0].price if sell_orders else None

        spread_current: float | None = None
        if current_buy and current_sell:
            spread_current = round(current_sell - current_buy, 4)

        unrealized_uah: float | None = None
        unrealized_pct: float | None = None
        if avg_buy is not None and current_sell is not None and usdt_remaining > 0:
            unrealized_uah = round(usdt_remaining * (current_sell - avg_buy), 2)
            unrealized_pct = round((current_sell - avg_buy) / avg_buy * 100, 2)

        market = {
            "current_buy":    current_buy,
            "current_sell":   current_sell,
            "spread_current": spread_current,
            "unrealized_uah": unrealized_uah,
            "unrealized_pct": unrealized_pct,
        }
    except Exception:
        pass

    # Диапазоны 24ч и 7д — из локальной БД, быстро
    ranges: dict[str, Any] = {}
    try:
        agg_24h = get_chart_agg(pair="USDT/UAH", timeframe="24h", exchange=exchange)
        agg_7d  = get_chart_agg(pair="USDT/UAH", timeframe="7d",  exchange=exchange)
        d1 = _range_stats(agg_24h.points) if not agg_24h.insufficient_data else {}
        d7 = _range_stats(agg_7d.points)  if not agg_7d.insufficient_data  else {}

        # Где текущий avg_buy относительно недельного диапазона
        if avg_buy and d7.get("buy_min") is not None and d7.get("buy_max") is not None:
            rng = d7["buy_max"] - d7["buy_min"]
            d7["avg_buy_position_pct"] = (
                round((avg_buy - d7["buy_min"]) / rng * 100, 1) if rng else 50.0
            )

        ranges = {"d1": d1, "d7": d7}
    except Exception:
        pass

    return {
        "session":  session_meta,
        "position": position,
        "market":   market,
        "ranges":   ranges,
        "trades":   trades_data,
    }


# ── Эндпоинт ─────────────────────────────────────────────────────────────────

@router.post(
    "/analyze",
    response_model=AIAnalyzeResponse,
    summary="AI-анализ сессий или рынка",
    dependencies=[Depends(require_api_key)],
)
async def ai_analyze(
    body: AIAnalyzeRequest,
    request: Request,
):
    _rate_limit(request)

    if body.mode not in ("sessions", "market", "position"):
        raise HTTPException(422, detail="mode must be 'sessions', 'market' or 'position'")
    if body.exchange not in ("binance", "bybit"):
        raise HTTPException(422, detail="exchange must be 'binance' or 'bybit'")
    if body.period not in _VALID_PERIODS:
        raise HTTPException(
            400,
            detail=f"period должен быть одним из: {', '.join(sorted(_VALID_PERIODS))}",
        )

    if body.mode == "sessions":
        payload = _collect_sessions_payload(body.exchange)
        if payload is None:
            return AIAnalyzeResponse(
                mode="sessions",
                analysis="Пока нет закрытых сессий для анализа. Закрой первую сессию — и агент даст комментарий.",
            )
    elif body.mode == "position":
        payload = _collect_position_payload(body.exchange)
        if payload is None:
            return AIAnalyzeResponse(
                mode="position",
                analysis="Нет открытой сессии. Начни сессию, чтобы анализировать текущую позицию.",
            )
    else:
        payload = _collect_market_payload(body.exchange, body.period)

    try:
        text = await analyze(body.mode, payload)
    except AIServiceError as exc:
        raise HTTPException(503, detail=str(exc))

    return AIAnalyzeResponse(mode=body.mode, analysis=text)
