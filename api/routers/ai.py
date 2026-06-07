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

class AIAnalyzeRequest(BaseModel):
    mode: str
    exchange: str = "binance"


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

def _collect_market_payload(exchange: str) -> dict[str, Any]:
    """
    Агрегирует историю за 30 дней в дневные бакеты (~30 точек).
    Из 2-часовых точек get_chart_agg("1m") делает дневную медиану.
    В payload попадает компактная выжимка + дневной ряд, НЕ сырьё.
    """
    agg = get_chart_agg(pair="USDT/UAH", timeframe="1m", exchange=exchange)

    if agg.insufficient_data or not agg.points:
        return {"summary": [], "chart": [], "note": "Недостаточно истории за 30 дней."}

    # Схлопываем 2-часовые бакеты → дневные (ts // 86400 * 86400)
    daily_buy: dict[int, list[float]] = defaultdict(list)
    daily_sell: dict[int, list[float]] = defaultdict(list)
    for pt in agg.points:
        day_ts = (pt.ts // 86400) * 86400
        daily_buy[day_ts].append(pt.buy_price)
        daily_sell[day_ts].append(pt.sell_price)

    daily_points: list[dict] = []
    for day_ts in sorted(daily_buy):
        b_prices = daily_buy[day_ts]
        s_prices = daily_sell[day_ts]
        daily_points.append({
            "ts": day_ts,
            "buy_price": round(statistics.median(b_prices), 4),
            "sell_price": round(statistics.median(s_prices), 4),
        })

    # Сводная статистика по дневному ряду
    all_buy = [p["buy_price"] for p in daily_points]
    all_sell = [p["sell_price"] for p in daily_points]
    all_spreads = [p["sell_price"] - p["buy_price"] for p in daily_points]

    buy_min = round(min(all_buy), 4)
    buy_max = round(max(all_buy), 4)
    buy_avg = round(statistics.mean(all_buy), 4)
    sell_min = round(min(all_sell), 4)
    sell_max = round(max(all_sell), 4)
    sell_avg = round(statistics.mean(all_sell), 4)
    spread_avg = round(statistics.mean(all_spreads), 4)

    current_buy = daily_points[-1]["buy_price"]
    current_sell = daily_points[-1]["sell_price"]
    current_spread = round(current_sell - current_buy, 4)

    # Где текущий BUY относительно 30-дневного диапазона (0% = минимум, 100% = максимум)
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
        "period_days": len(daily_points),
        "buy": {
            "current": current_buy,
            "min_30d": buy_min,
            "max_30d": buy_max,
            "avg_30d": buy_avg,
            "position_pct": buy_position_pct,
            "phase": buy_phase,
        },
        "sell": {
            "current": current_sell,
            "min_30d": sell_min,
            "max_30d": sell_max,
            "avg_30d": sell_avg,
        },
        "spread": {
            "current": current_spread,
            "avg_30d": spread_avg,
            "vs_avg": round(current_spread - spread_avg, 4),
        },
    }

    return {"summary": summary, "chart": daily_points}


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

    if body.mode not in ("sessions", "market"):
        raise HTTPException(422, detail="mode must be 'sessions' or 'market'")
    if body.exchange not in ("binance", "bybit"):
        raise HTTPException(422, detail="exchange must be 'binance' or 'bybit'")

    if body.mode == "sessions":
        payload = _collect_sessions_payload(body.exchange)
        if payload is None:
            return AIAnalyzeResponse(
                mode="sessions",
                analysis="Пока нет закрытых сессий для анализа. Закрой первую сессию — и агент даст комментарий.",
            )
    else:
        payload = _collect_market_payload(body.exchange)

    try:
        text = await analyze(body.mode, payload)
    except AIServiceError as exc:
        raise HTTPException(503, detail=str(exc))

    return AIAnalyzeResponse(mode=body.mode, analysis=text)
