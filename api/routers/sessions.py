from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from api.dependencies import require_api_key
from api.schemas import SessionCreate, SessionDetail, SessionOut, TradeOut
from api.services.market_service import get_orders
from core.database import Session, Trade, get_session

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _active_session(db) -> Session | None:
    return db.scalars(
        select(Session).where(Session.status == "active").limit(1)
    ).first()


def _calc_pnl(trades: list[Trade], current_sell_price: float) -> tuple[float, float, float, float]:
    """Возвращает (avg_buy_price, usdt_remaining, realized_uah, unrealized_uah)."""
    buys = [t for t in trades if t.trade_type == "BUY"]
    sells = [t for t in trades if t.trade_type == "SELL"]

    total_usdt_bought = sum(t.amount_usdt for t in buys)
    total_uah_spent = sum(t.amount_uah for t in buys)
    total_usdt_sold = sum(t.amount_usdt for t in sells)
    total_uah_received = sum(t.amount_uah for t in sells)

    avg_buy_price = (total_uah_spent / total_usdt_bought) if total_usdt_bought else 0.0
    usdt_remaining = total_usdt_bought - total_usdt_sold
    realized_uah = total_uah_received - total_usdt_sold * avg_buy_price
    unrealized_uah = usdt_remaining * (current_sell_price - avg_buy_price)

    return avg_buy_price, usdt_remaining, realized_uah, unrealized_uah


def _session_out(session: Session, trade_count: int) -> SessionOut:
    data = SessionOut.model_validate(session)
    data.trade_count = trade_count
    return data


@router.post("/start", response_model=SessionOut, status_code=201,
             summary="Начать торговую сессию",
             dependencies=[Depends(require_api_key)])
def start_session(body: SessionCreate):
    if body.exchange not in ("binance", "bybit"):
        raise HTTPException(422, detail="exchange must be 'binance' or 'bybit'")

    with get_session() as db:
        if _active_session(db) is not None:
            raise HTTPException(409, detail="Уже есть активная сессия")

        max_number = db.execute(select(func.max(Session.number))).scalar() or 0
        session = Session(
            number=max_number + 1,
            start_capital_uah=body.start_capital_uah,
            exchange=body.exchange,
            status="active",
            started_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(session)
        db.flush()
        db.refresh(session)
        return _session_out(session, 0)


@router.post("/{session_id}/close", response_model=SessionOut,
             summary="Закрыть торговую сессию",
             dependencies=[Depends(require_api_key)])
def close_session(session_id: int):
    with get_session() as db:
        session = db.get(Session, session_id)
        if session is None:
            raise HTTPException(404, detail=f"Сессия {session_id} не найдена")
        if session.status == "closed":
            raise HTTPException(409, detail="Сессия уже закрыта")

        trades = db.scalars(
            select(Trade).where(Trade.session_id == session_id)
        ).all()

        orders = get_orders(pair="USDT/UAH", mode="sell", exchange=session.exchange, top=1)
        current_sell_price = orders[0].price if orders else 0.0
        if not current_sell_price:
            raise HTTPException(
                503,
                detail="Не удалось получить текущий курс продажи. Попробуйте закрыть сессию через минуту.",
            )

        avg_buy_price, usdt_remaining, realized_uah, unrealized_uah = _calc_pnl(
            list(trades), current_sell_price
        )

        session.status = "closed"
        session.closed_at = datetime.now(UTC).replace(tzinfo=None)
        session.close_sell_price = round(current_sell_price, 4)
        session.realized_uah = round(realized_uah, 4)
        session.unrealized_uah = round(unrealized_uah, 4)
        session.usdt_remaining = round(usdt_remaining, 4)

        db.flush()
        db.refresh(session)
        return _session_out(session, len(trades))


@router.get("", response_model=list[SessionOut], summary="Список всех сессий")
def list_sessions():
    with get_session() as db:
        sessions = db.scalars(
            select(Session).order_by(Session.number.desc())
        ).all()

        counts: dict[int, int] = {}
        if sessions:
            ids = [s.id for s in sessions]
            rows = db.execute(
                select(Trade.session_id, func.count(Trade.id))
                .where(Trade.session_id.in_(ids))
                .group_by(Trade.session_id)
            ).all()
            counts = {sid: cnt for sid, cnt in rows}

        return [_session_out(s, counts.get(s.id, 0)) for s in sessions]


@router.get("/active", response_model=SessionOut | None, summary="Текущая активная сессия")
def get_active_session():
    with get_session() as db:
        session = _active_session(db)
        if session is None:
            return None
        count = db.execute(
            select(func.count(Trade.id)).where(Trade.session_id == session.id)
        ).scalar() or 0
        return _session_out(session, count)


@router.get("/{session_id}", response_model=SessionDetail, summary="Детали сессии со сделками")
def get_session_detail(session_id: int):
    with get_session() as db:
        session = db.get(Session, session_id)
        if session is None:
            raise HTTPException(404, detail=f"Сессия {session_id} не найдена")

        trades = db.scalars(
            select(Trade)
            .where(Trade.session_id == session_id)
            .order_by(Trade.executed_at.desc())
        ).all()

        result = SessionDetail.model_validate(session)
        result.trade_count = len(trades)
        result.trades = [TradeOut.model_validate(t) for t in trades]
        return result
