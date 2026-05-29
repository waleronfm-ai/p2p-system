from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from api.schemas import PositionResponse
from core.database import Trade, get_session
from core.utils.pnl import calc_realized_pnl

router = APIRouter(prefix="/position", tags=["position"])


@router.get("", response_model=PositionResponse, summary="Текущая позиция пользователя")
def get_position():
    with get_session() as session:
        trades = session.scalars(select(Trade)).all()

    buys = [t for t in trades if t.trade_type == "BUY"]
    sells = [t for t in trades if t.trade_type == "SELL"]

    total_buy_usdt = sum(t.amount_usdt for t in buys)
    total_buy_uah = sum(t.amount_uah for t in buys)
    total_sell_usdt = sum(t.amount_usdt for t in sells)
    total_sell_uah = sum(t.amount_uah for t in sells)

    usdt_balance = total_buy_usdt - total_sell_usdt

    if total_buy_usdt > 0:
        avg_buy_price = total_buy_uah / total_buy_usdt
        break_even = avg_buy_price
        realized_profit_uah = calc_realized_pnl(total_buy_uah, total_buy_usdt, total_sell_uah, total_sell_usdt)
    else:
        avg_buy_price = None
        break_even = None
        realized_profit_uah = None

    return PositionResponse(
        usdt_balance=round(usdt_balance, 8),
        avg_buy_price=round(avg_buy_price, 4) if avg_buy_price is not None else None,
        break_even=round(break_even, 4) if break_even is not None else None,
        realized_profit_uah=realized_profit_uah,
        total_trades=len(trades),
        buy_count=len(buys),
        sell_count=len(sells),
    )
