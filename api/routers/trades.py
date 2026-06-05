from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func

from core.utils.pnl import calc_realized_pnl

from api.dependencies import require_api_key
from api.schemas import TradeCreate, TradeOut, TradeStats
from core.database import Session, Trade, get_session

router = APIRouter(prefix="/trades", tags=["trades"])


@router.post("", response_model=TradeOut, status_code=201, summary="Добавить сделку",
             dependencies=[Depends(require_api_key)])
def create_trade(body: TradeCreate):
    if body.trade_type.upper() not in ("BUY", "SELL"):
        raise HTTPException(422, detail="trade_type must be 'BUY' or 'SELL'")
    if body.exchange not in ("binance", "bybit"):
        raise HTTPException(422, detail="exchange must be 'binance' or 'bybit'")

    with get_session() as db:
        active = db.scalars(
            select(Session).where(Session.status == "active").limit(1)
        ).first()

        trade = Trade(
            exchange=body.exchange,
            order_id=body.order_id,
            trade_type=body.trade_type.upper(),
            price=body.price,
            amount_usdt=body.amount_usdt,
            amount_uah=body.amount_uah,
            bank=body.bank,
            counterparty=body.counterparty,
            note=body.note,
            executed_at=body.executed_at,
            session_id=active.id if active else None,
        )
        db.add(trade)
        db.flush()
        db.refresh(trade)
        return TradeOut.model_validate(trade)


@router.get("", response_model=list[TradeOut], summary="Список сделок")
def list_trades(
    exchange: str | None = Query(None, description="binance / bybit"),
    trade_type: str | None = Query(None, description="BUY / SELL"),
    from_dt: datetime | None = Query(None, description="С даты (UTC ISO)"),
    to_dt: datetime | None = Query(None, description="По дату (UTC ISO)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    with get_session() as session:
        q = select(Trade).order_by(Trade.executed_at.desc())
        if exchange:
            q = q.where(Trade.exchange == exchange)
        if trade_type:
            q = q.where(Trade.trade_type == trade_type.upper())
        if from_dt:
            q = q.where(Trade.executed_at >= from_dt)
        if to_dt:
            q = q.where(Trade.executed_at <= to_dt)
        rows = session.scalars(q.offset(offset).limit(limit)).all()
        return [TradeOut.model_validate(r) for r in rows]


@router.get("/stats", response_model=TradeStats, summary="Статистика по сделкам")
def trade_stats(
    exchange: str | None = Query(None, description="binance / bybit"),
    from_dt: datetime | None = Query(None, description="С даты (UTC ISO)"),
    to_dt: datetime | None = Query(None, description="По дату (UTC ISO)"),
):
    with get_session() as session:
        q = select(Trade)
        if exchange:
            q = q.where(Trade.exchange == exchange)
        if from_dt:
            q = q.where(Trade.executed_at >= from_dt)
        if to_dt:
            q = q.where(Trade.executed_at <= to_dt)
        trades = session.scalars(q).all()

    buys = [t for t in trades if t.trade_type == "BUY"]
    sells = [t for t in trades if t.trade_type == "SELL"]

    total_uah_spent = sum(t.amount_uah for t in buys)
    total_uah_received = sum(t.amount_uah for t in sells)
    total_usdt_bought = sum(t.amount_usdt for t in buys)
    total_usdt_sold = sum(t.amount_usdt for t in sells)

    return TradeStats(
        total_trades=len(trades),
        buy_count=len(buys),
        sell_count=len(sells),
        total_usdt_bought=total_usdt_bought,
        total_usdt_sold=total_usdt_sold,
        total_uah_spent=total_uah_spent,
        total_uah_received=total_uah_received,
        avg_buy_price=sum(t.price for t in buys) / len(buys) if buys else None,
        avg_sell_price=sum(t.price for t in sells) / len(sells) if sells else None,
        pnl_uah=calc_realized_pnl(total_uah_spent, total_usdt_bought, total_uah_received, total_usdt_sold),
    )


@router.get("/{trade_id}", response_model=TradeOut, summary="Одна сделка по ID")
def get_trade(trade_id: int):
    with get_session() as session:
        trade = session.get(Trade, trade_id)
        if trade is None:
            raise HTTPException(404, detail=f"Сделка {trade_id} не найдена")
        return TradeOut.model_validate(trade)


@router.delete("/{trade_id}", status_code=204, summary="Удалить сделку",
               dependencies=[Depends(require_api_key)])
def delete_trade(trade_id: int):
    with get_session() as session:
        trade = session.get(Trade, trade_id)
        if trade is None:
            raise HTTPException(404, detail=f"Сделка {trade_id} не найдена")
        session.delete(trade)
