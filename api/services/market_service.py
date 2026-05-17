from __future__ import annotations

import json
import statistics as _stats
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from itertools import groupby as _groupby

from sqlalchemy import func, select

from core.banks.registry import (
    classify_payment_methods,
    find_bank,
    get_worst_risk,
    methods_match_bank,
)
from core.database import Maker, Order, Snapshot, get_session
from core.utils.maker_trust import classify_maker
from core.utils.outliers import filter_outliers

from api.schemas import (
    BankInfo,
    ChartPoint,
    ChartResponse,
    MakerInfo,
    MarketOrder,
    OutlierMaker,
    OutliersResponse,
    PairSummary,
    SpreadInfo,
    SummaryResponse,
)


# ── DB helpers ────────────────────────────────────────────────────────────────

def _cutoff(hours: int | None) -> datetime | None:
    if hours is None:
        return None
    return datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)


def _snap_where(
    exchange: str | None = None,
    asset: str | None = None,
    fiat: str | None = None,
    trade_type: str | None = None,
    cut: datetime | None = None,
) -> list:
    conds = []
    if exchange:
        conds.append(Snapshot.exchange == exchange)
    if asset:
        conds.append(Snapshot.asset == asset)
    if fiat:
        conds.append(Snapshot.fiat == fiat)
    if trade_type:
        conds.append(Snapshot.trade_type == trade_type)
    if cut is not None:
        conds.append(Snapshot.collected_at >= cut)
    return conds


def _best_fn(trade_type: str):
    return func.min(Order.price) if trade_type == "BUY" else func.max(Order.price)


def _clean_series(
    session,
    exchange: str,
    asset: str,
    fiat: str,
    trade_type: str,
    cut: datetime | None = None,
    top_n: int = 5,
) -> list[tuple[datetime, float]]:
    w = _snap_where(exchange, asset, fiat, trade_type, cut)
    snaps = session.execute(
        select(Snapshot.id, Snapshot.collected_at)
        .where(*w)
        .order_by(Snapshot.collected_at.asc())
    ).all()
    if not snaps:
        return []

    snap_ts_map = {s.id: s.collected_at for s in snaps}
    snap_ids = list(snap_ts_map)
    order_col = Order.price.asc() if trade_type == "BUY" else Order.price.desc()

    all_orders = session.execute(
        select(Order.snapshot_id, Order.price)
        .where(Order.snapshot_id.in_(snap_ids))
        .order_by(Order.snapshot_id, order_col)
    ).all()

    result = []
    for sid, grp in _groupby(all_orders, key=lambda r: r.snapshot_id):
        rows = list(grp)[:top_n]
        clean, _ = filter_outliers(rows, trade_type, top_n=top_n)
        if clean:
            result.append((snap_ts_map[sid], float(clean[0].price)))
    return result


# ── Schema builders ───────────────────────────────────────────────────────────

def _build_banks(methods: list[str]) -> list[BankInfo]:
    return [
        BankInfo(name=name, risk=risk.value)
        for name, risk in classify_payment_methods(methods)
    ]


def _build_maker(nickname: str, total_orders: int, completion_rate: float, is_merchant: bool) -> MakerInfo:
    return MakerInfo(
        nickname=nickname,
        total_orders=total_orders,
        completion_rate=completion_rate,
        is_merchant=is_merchant,
        trust_level=classify_maker(total_orders, completion_rate).value,
    )


# ── Public service functions ──────────────────────────────────────────────────

def get_summary(hours: int | None = None, raw: bool = False) -> SummaryResponse:
    cut = _cutoff(hours)
    pairs_out: list[PairSummary] = []
    last_prices: dict[tuple, float] = {}

    with get_session() as session:
        groups = session.execute(
            select(
                Snapshot.exchange, Snapshot.asset, Snapshot.fiat, Snapshot.trade_type,
                func.count(Snapshot.id).label("n"),
            )
            .where(*_snap_where(cut=cut))
            .group_by(Snapshot.exchange, Snapshot.asset, Snapshot.fiat, Snapshot.trade_type)
            .order_by(Snapshot.asset, Snapshot.fiat, Snapshot.exchange, Snapshot.trade_type)
        ).all()

        for exchange, asset, fiat, trade_type, snap_count in groups:
            bw = _snap_where(exchange, asset, fiat, trade_type, cut)
            order_count = session.execute(
                select(func.count(Order.id))
                .join(Snapshot, Order.snapshot_id == Snapshot.id)
                .where(*bw)
            ).scalar()

            if raw:
                min_p, max_p = session.execute(
                    select(func.min(Order.price), func.max(Order.price))
                    .join(Snapshot, Order.snapshot_id == Snapshot.id)
                    .where(*bw)
                ).one()
                best_sub = (
                    select(_best_fn(trade_type).label("bp"))
                    .join(Snapshot, Order.snapshot_id == Snapshot.id)
                    .where(*bw)
                    .group_by(Order.snapshot_id)
                    .subquery()
                )
                avg_p = session.execute(select(func.avg(best_sub.c.bp))).scalar()
                latest_sid = session.execute(
                    select(Snapshot.id).where(*bw)
                    .order_by(Snapshot.collected_at.desc()).limit(1)
                ).scalar_one_or_none()
                last_p = session.execute(
                    select(_best_fn(trade_type)).where(Order.snapshot_id == latest_sid)
                ).scalar() if latest_sid else None
            else:
                series = _clean_series(session, exchange, asset, fiat, trade_type, cut)
                if series:
                    prices = [p for _, p in series]
                    min_p, max_p = min(prices), max(prices)
                    avg_p = sum(prices) / len(prices)
                    last_p = prices[-1]
                else:
                    min_p = max_p = avg_p = last_p = None

            pairs_out.append(PairSummary(
                exchange=exchange,
                pair=f"{asset}/{fiat}",
                mode="buy" if trade_type == "BUY" else "sell",
                snapshots=snap_count,
                orders_total=order_count,
                price_min=round(min_p, 4) if min_p is not None else None,
                price_max=round(max_p, 4) if max_p is not None else None,
                price_avg=round(avg_p, 4) if avg_p is not None else None,
                price_now=round(last_p, 4) if last_p is not None else None,
            ))
            if last_p:
                last_prices[(exchange, asset, fiat, trade_type)] = last_p

    # Build cross-exchange spreads
    spreads_out: list[SpreadInfo] = []
    seen = {(p.pair, p.mode) for p in pairs_out}
    for pair_str, mode in sorted(seen):
        asset, fiat = pair_str.split("/")
        trade_type = "BUY" if mode == "buy" else "SELL"
        bn = last_prices.get(("binance", asset, fiat, trade_type))
        bb = last_prices.get(("bybit", asset, fiat, trade_type))
        spreads_out.append(SpreadInfo(
            pair=pair_str,
            mode=mode,
            binance_price=round(bn, 4) if bn is not None else None,
            bybit_price=round(bb, 4) if bb is not None else None,
            spread=round(bn - bb, 4) if (bn is not None and bb is not None) else None,
        ))

    return SummaryResponse(hours=hours, pairs=pairs_out, spreads=spreads_out)


def get_orders(
    pair: str,
    mode: str,
    exchange: str | None = None,
    min_orders: int = 0,
    min_completion: float = 0.0,
    bank: str | None = None,
    avoid_banks: list[str] | None = None,
    top: int = 10,
    raw: bool = False,
) -> list[MarketOrder]:
    parts = pair.upper().split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid pair format: {pair!r}. Expected ASSET/FIAT, e.g. USDT/UAH")
    asset, fiat = parts
    trade_type = "BUY" if mode.lower() == "buy" else "SELL"

    bank_entry = find_bank(bank) if bank else None
    avoid_entries = [e for name in (avoid_banks or []) if (e := find_bank(name))]

    exchanges = [exchange] if exchange else ["binance", "bybit"]
    collected: list[tuple[str, object]] = []

    with get_session() as session:
        for exch in exchanges:
            snap_row = session.execute(
                select(Snapshot.id, Snapshot.collected_at)
                .where(*_snap_where(exch, asset, fiat, trade_type))
                .order_by(Snapshot.collected_at.desc()).limit(1)
            ).one_or_none()
            if snap_row is None:
                continue
            snap_id, snap_ts = snap_row

            order_col = Order.price.asc() if trade_type == "BUY" else Order.price.desc()
            rows = session.execute(
                select(
                    Order.price, Order.available_amount, Order.min_amount, Order.max_amount,
                    Maker.nickname, Maker.total_orders, Maker.completion_rate, Maker.is_merchant,
                    Order.payment_methods,
                )
                .join(Maker, Order.maker_id == Maker.id)
                .where(Order.snapshot_id == snap_id)
                .order_by(order_col)
            ).all()

            if not raw and rows:
                rows, _ = filter_outliers(rows, trade_type, top_n=len(rows))

            for o in rows:
                collected.append((exch, snap_ts, o))

    results: list[MarketOrder] = []
    for exch, snap_ts, o in collected:
        if o.total_orders < min_orders:
            continue
        if o.completion_rate < min_completion:
            continue
        methods = [m for m in json.loads(o.payment_methods or "[]") if m is not None]
        if bank_entry and not methods_match_bank(methods, bank_entry):
            continue
        if avoid_entries and any(methods_match_bank(methods, e) for e in avoid_entries):
            continue
        results.append(MarketOrder(
            price=o.price,
            available_amount=o.available_amount,
            min_amount=o.min_amount,
            max_amount=o.max_amount,
            exchange=exch,
            pair=f"{asset}/{fiat}",
            mode=mode.lower(),
            maker=_build_maker(o.nickname, o.total_orders, o.completion_rate, o.is_merchant),
            banks=_build_banks(methods),
            is_outlier=False,
            snapshot_at=snap_ts,
        ))

    results.sort(key=lambda x: x.price if trade_type == "BUY" else -x.price)
    return results[:top]


def get_outliers(
    hours: int | None = None,
    pair: str | None = None,
    mode: str | None = None,
) -> OutliersResponse:
    cut = _cutoff(hours)
    asset: str | None = None
    fiat: str | None = None
    if pair:
        parts = pair.upper().split("/")
        if len(parts) == 2:
            asset, fiat = parts

    trade_type: str | None = None
    if mode:
        trade_type = "BUY" if mode.lower() == "buy" else "SELL"

    MakerKey = tuple
    appearances: dict[MakerKey, int] = defaultdict(int)
    out_prices: dict[MakerKey, list[float]] = defaultdict(list)
    out_volumes: dict[MakerKey, list[float]] = defaultdict(list)
    total_orders_all = 0
    total_outliers_all = 0

    with get_session() as session:
        combos = session.execute(
            select(Snapshot.exchange, Snapshot.asset, Snapshot.fiat, Snapshot.trade_type)
            .where(*_snap_where(asset=asset, fiat=fiat, trade_type=trade_type, cut=cut))
            .distinct()
        ).all()

        for exch, snap_asset, snap_fiat, snap_tt in combos:
            snaps = session.execute(
                select(Snapshot.id)
                .where(*_snap_where(exch, snap_asset, snap_fiat, snap_tt, cut))
            ).scalars().all()
            if not snaps:
                continue

            order_col = Order.price.asc() if snap_tt == "BUY" else Order.price.desc()
            all_rows = session.execute(
                select(Order.snapshot_id, Order.price, Order.available_amount, Maker.nickname)
                .join(Maker, Order.maker_id == Maker.id)
                .where(Order.snapshot_id.in_(snaps))
                .order_by(Order.snapshot_id, order_col)
            ).all()

            for sid, grp in _groupby(all_rows, key=lambda r: r.snapshot_id):
                rows = list(grp)[:5]
                total_orders_all += len(rows)
                _, bad = filter_outliers(rows, snap_tt, top_n=5)
                total_outliers_all += len(bad)
                for o in bad:
                    key = (exch, snap_asset, snap_fiat, snap_tt, o.nickname)
                    appearances[key] += 1
                    out_prices[key].append(float(o.price))
                    out_volumes[key].append(float(o.available_amount))

    makers_out = [
        OutlierMaker(
            exchange=exch,
            pair=f"{snap_asset}/{snap_fiat}",
            mode="buy" if snap_tt == "BUY" else "sell",
            nickname=nickname,
            appearances=appearances[key],
            price_min=min(out_prices[key]),
            price_max=max(out_prices[key]),
            volume_median=_stats.median(out_volumes[key]) if out_volumes[key] else 0.0,
        )
        for key in sorted(appearances, key=lambda k: appearances[k], reverse=True)
        for exch, snap_asset, snap_fiat, snap_tt, nickname in [key]
    ]

    pct = (total_outliers_all / total_orders_all * 100) if total_orders_all else 0.0
    return OutliersResponse(
        hours=hours,
        pair=pair,
        mode=mode,
        total_orders=total_orders_all,
        total_outliers=total_outliers_all,
        outlier_pct=round(pct, 2),
        makers=makers_out,
    )


def get_chart(
    pair: str,
    mode: str,
    exchange: str,
    hours: int,
    raw: bool = False,
) -> ChartResponse:
    parts = pair.upper().split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid pair format: {pair!r}. Expected ASSET/FIAT, e.g. USDT/UAH")
    asset, fiat = parts
    trade_type = "BUY" if mode.lower() == "buy" else "SELL"
    cut = _cutoff(hours)

    w = _snap_where(exchange, asset, fiat, trade_type, cut)
    order_col = Order.price.asc() if trade_type == "BUY" else Order.price.desc()

    with get_session() as session:
        snaps = session.execute(
            select(Snapshot.id, Snapshot.collected_at)
            .where(*w)
            .order_by(Snapshot.collected_at.asc())
        ).all()

        if not snaps:
            return ChartResponse(
                exchange=exchange, pair=f"{asset}/{fiat}", mode=mode.lower(),
                hours=hours, points=[], total_points=0,
            )

        snap_ts_map = {s.id: s.collected_at for s in snaps}
        snap_ids = list(snap_ts_map)

        all_orders = session.execute(
            select(Order.snapshot_id, Order.price)
            .where(Order.snapshot_id.in_(snap_ids))
            .order_by(Order.snapshot_id, order_col)
        ).all()

    points: list[ChartPoint] = []
    for sid, grp in _groupby(all_orders, key=lambda r: r.snapshot_id):
        rows = list(grp)[:5]
        if raw:
            price = float(rows[0].price)
        else:
            clean, _ = filter_outliers(rows, trade_type, top_n=5)
            if not clean:
                continue
            price = float(clean[0].price)
        points.append(ChartPoint(
            timestamp=snap_ts_map[sid],
            price=price,
            snapshot_id=sid,
        ))

    return ChartResponse(
        exchange=exchange,
        pair=f"{asset}/{fiat}",
        mode=mode.lower(),
        hours=hours,
        points=points,
        total_points=len(points),
    )
