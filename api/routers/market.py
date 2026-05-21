from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.schemas import ChartResponse, MarketOrder, OpportunitiesResponse, OutliersResponse, SummaryResponse
from api.services.market_service import get_chart, get_opportunities, get_orders, get_outliers, get_summary

router = APIRouter(prefix="/market")


@router.get("/summary", response_model=SummaryResponse, summary="Сводка по всем парам")
def summary(
    hours: int | None = Query(None, ge=1, description="Последние N часов (по умолчанию всё)"),
    raw: bool = Query(False, description="Сырые цены без фильтрации выбросов"),
):
    return get_summary(hours=hours, raw=raw)


@router.get("/orders", response_model=list[MarketOrder], summary="Ордера по паре с фильтрами")
def orders(
    pair: str = Query(..., description="Пара: USDT/UAH, USDC/UAH"),
    mode: str = Query(..., description="buy (купить крипту) или sell (продать)"),
    exchange: str | None = Query(None, description="binance или bybit (по умолчанию оба)"),
    min_orders: int = Query(0, ge=0, description="Минимум сделок у мейкера"),
    min_completion: float = Query(0.0, ge=0.0, le=100.0, description="Минимум %% completion"),
    bank: str = Query(None, description="Фильтр по банку: Privat, Mono, Oschad ..."),
    avoid_banks: str = Query(None, description="Исключить банки через запятую: Oschad,Pumb"),
    top: int = Query(10, ge=1, le=100, description="Количество ордеров в ответе"),
    raw: bool = Query(False, description="Сырые цены без фильтрации выбросов"),
):
    if mode.lower() not in ("buy", "sell"):
        raise HTTPException(422, detail="mode must be 'buy' or 'sell'")
    if exchange and exchange not in ("binance", "bybit"):
        raise HTTPException(422, detail="exchange must be 'binance' or 'bybit'")
    avoid_list = [b.strip() for b in avoid_banks.split(",")] if avoid_banks else []
    try:
        return get_orders(
            pair=pair, mode=mode, exchange=exchange,
            min_orders=min_orders, min_completion=min_completion,
            bank=bank, avoid_banks=avoid_list, top=top, raw=raw,
        )
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))


@router.get("/chart", response_model=ChartResponse, summary="Данные для графика цены")
def chart(
    pair: str = Query(..., description="Пара: USDT/UAH, USDC/UAH"),
    mode: str = Query(..., description="buy или sell"),
    exchange: str = Query(..., description="binance или bybit"),
    hours: int = Query(24, ge=1, le=8760, description="Глубина в часах (по умолчанию 24)"),
    raw: bool = Query(False, description="Сырые цены без фильтрации выбросов"),
    volume_uah: float | None = Query(None, gt=0, description="Объём сделки в UAH: фильтр ордеров где min_amount ≤ volume_uah"),
):
    if mode.lower() not in ("buy", "sell"):
        raise HTTPException(422, detail="mode must be 'buy' or 'sell'")
    if exchange not in ("binance", "bybit"):
        raise HTTPException(422, detail="exchange must be 'binance' or 'bybit'")
    try:
        return get_chart(pair=pair, mode=mode, exchange=exchange, hours=hours, raw=raw, volume_uah=volume_uah)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))


@router.get("/opportunities", response_model=OpportunitiesResponse, summary="Выгодные ордера с учётом позиции")
def opportunities(
    exchange: str = Query("binance", description="binance или bybit"),
    pair: str = Query("USDT/UAH", description="Пара: USDT/UAH, USDC/UAH"),
    mode: str | None = Query(None, description="entry / exit / null (авто по позиции)"),
):
    if mode is not None and mode not in ("entry", "exit"):
        raise HTTPException(422, detail="mode must be 'entry', 'exit' or omitted")
    if exchange not in ("binance", "bybit"):
        raise HTTPException(422, detail="exchange must be 'binance' or 'bybit'")
    try:
        return get_opportunities(exchange=exchange, pair=pair, mode=mode)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))


@router.get("/outliers", response_model=OutliersResponse, summary="Мейкеры-выбросы за период")
def outliers(
    hours: int | None = Query(None, ge=1, description="Период в часах (по умолчанию всё)"),
    pair: str | None = Query(None, description="Фильтр по паре: USDT/UAH"),
    mode: str | None = Query(None, description="Фильтр по стороне: buy или sell"),
):
    if mode and mode.lower() not in ("buy", "sell"):
        raise HTTPException(422, detail="mode must be 'buy' or 'sell'")
    return get_outliers(hours=hours, pair=pair, mode=mode)
