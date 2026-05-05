from __future__ import annotations

import sys
from itertools import groupby as _groupby
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from datetime import UTC, datetime, timedelta

from rich.console import Console
from rich.table import Table
from sqlalchemy import func, select

from core.database import Maker, Order, Snapshot, get_session
from core.utils.outliers import filter_outliers, get_clean_top1, median_price
from core.utils.timezone import format_kyiv

console = Console()

# ── tiny helpers ──────────────────────────────────────────────────────────────

def _cutoff(hours: int | None) -> datetime | None:
    """Naive UTC cutoff for SQLite comparisons."""
    if hours is None:
        return None
    return datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=hours)


def _parse_pair(pair_str: str) -> tuple[str, str]:
    parts = pair_str.upper().split("/")
    if len(parts) != 2:
        console.print(f"[red]Неверный формат пары: {pair_str!r}. Пример: USDT/UAH[/red]")
        sys.exit(1)
    return parts[0], parts[1]


def _no_data(msg: str = "Нет данных в БД. Запусти трекер: start_tracker.bat") -> None:
    console.print(f"[yellow]{msg}[/yellow]")
    sys.exit(0)


def _best_fn(trade_type: str):
    """Min price for BUY (cheapest), max for SELL (most expensive)."""
    return func.min(Order.price) if trade_type == "BUY" else func.max(Order.price)


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


def _clean_series(
    session,
    exchange: str,
    asset: str,
    fiat: str,
    trade_type: str,
    cut: datetime | None = None,
    top_n: int = 5,
    threshold: float = 0.025,
) -> list[tuple[datetime, float]]:
    """Bulk-loads top-N orders per snapshot, filters outliers, returns [(ts, clean_top1_price)]."""
    w = _snap_where(exchange, asset, fiat, trade_type, cut)
    snaps = session.execute(
        select(Snapshot.id, Snapshot.collected_at).where(*w)
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
        clean, _ = filter_outliers(rows, trade_type, top_n=top_n, threshold=threshold)
        if clean:
            result.append((snap_ts_map[sid], float(clean[0].price)))
    return result


# ── ASCII chart helpers ───────────────────────────────────────────────────────

def _render_chart(values: list[float], height: int = 7) -> list[str]:
    """Multi-line bar chart. Returns `height` strings."""
    if not values:
        return []
    min_v, max_v = min(values), max(values)
    rng = max_v - min_v

    lines = []
    for row in range(height):
        hi = max_v - (row / height) * rng
        lo = max_v - ((row + 1) / height) * rng

        if row == 0:
            y_lbl = f"{max_v:6.2f}│"
        elif row == height // 2:
            y_lbl = f"{(min_v + max_v) / 2:6.2f}│"
        elif row == height - 1:
            y_lbl = f"{min_v:6.2f}│"
        else:
            y_lbl = "      │"

        bar = []
        for v in values:
            if rng == 0:
                bar.append("▄")
            elif v >= hi:
                bar.append("█")
            elif v >= lo:
                frac = (v - lo) / (hi - lo)
                bar.append("▁▂▃▄▅▆▇█"[min(7, int(frac * 8))])
            else:
                bar.append(" ")
        lines.append(y_lbl + "".join(bar))
    return lines


def _x_axis_labels(timestamps: list[datetime], width: int) -> str:
    """Sparse time labels under the chart."""
    if not timestamps:
        return ""
    n = min(5, len(timestamps))
    indices = [int(i * (len(timestamps) - 1) / max(n - 1, 1)) for i in range(n)]
    axis = [" "] * (8 + width)
    for idx in indices:
        label = format_kyiv(timestamps[idx], "%H:%M")
        pos = 8 + idx
        for j, ch in enumerate(label):
            if pos + j < len(axis):
                axis[pos + j] = ch
    return "".join(axis)


# ── cmd: summary ─────────────────────────────────────────────────────────────

def cmd_summary(args: argparse.Namespace) -> None:
    hours = getattr(args, "hours", None)
    raw: bool = getattr(args, "raw", False)
    cut = _cutoff(hours)
    price_label = "(сырые цены)" if raw else "(чистые цены)"

    with get_session() as session:
        if not session.execute(select(func.count()).select_from(Snapshot)).scalar():
            _no_data()

        first_ts = session.execute(select(func.min(Snapshot.collected_at))).scalar()
        last_ts  = session.execute(select(func.max(Snapshot.collected_at))).scalar()

        w = _snap_where(cut=cut)
        groups = session.execute(
            select(Snapshot.exchange, Snapshot.asset, Snapshot.fiat, Snapshot.trade_type,
                   func.count(Snapshot.id).label("n"))
            .where(*w)
            .group_by(Snapshot.exchange, Snapshot.asset, Snapshot.fiat, Snapshot.trade_type)
            .order_by(Snapshot.asset, Snapshot.fiat, Snapshot.exchange, Snapshot.trade_type)
        ).all()

        if not groups:
            _no_data(f"Нет данных за последние {hours} ч.")

        rows_data = []
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
                    min_p = min(prices)
                    max_p = max(prices)
                    avg_p = sum(prices) / len(prices)
                    last_p = prices[-1]
                else:
                    min_p = max_p = avg_p = last_p = None

            rows_data.append((exchange, asset, fiat, trade_type, snap_count,
                               order_count, min_p, max_p, avg_p, last_p))

    period_label = f"последние {hours} ч" if hours else "все данные"
    console.rule(f"[bold cyan]Сводка P2P — {period_label} {price_label}[/bold cyan]")

    if first_ts and last_ts:
        dur_h = (last_ts - first_ts).total_seconds() / 3600
        console.print(
            f"\n[dim]Период:[/dim] "
            f"{format_kyiv(first_ts, '%d.%m %H:%M')} → {format_kyiv(last_ts, '%d.%m %H:%M')} "
            f"[dim]({dur_h:.1f} ч)[/dim]\n"
        )

    t = Table(show_header=True, header_style="bold cyan", border_style="dim")
    t.add_column("Биржа")
    t.add_column("Пара")
    t.add_column("Тип")
    t.add_column("Снимков", justify="right")
    t.add_column("Ордеров", justify="right")
    t.add_column("Min", justify="right")
    t.add_column("Max", justify="right")
    t.add_column("Avg топ-1", justify="right")
    t.add_column("Сейчас", justify="right", style="bold")

    last_prices: dict[tuple, float] = {}
    for (exchange, asset, fiat, trade_type, snap_count, order_count,
         min_p, max_p, avg_p, last_p) in rows_data:
        c = "green" if trade_type == "BUY" else "red"
        t.add_row(
            exchange, f"{asset}/{fiat}", f"[{c}]{trade_type}[/{c}]",
            str(snap_count), str(order_count),
            f"{min_p:.2f}" if min_p else "—",
            f"{max_p:.2f}" if max_p else "—",
            f"{avg_p:.2f}" if avg_p else "—",
            f"{last_p:.2f}" if last_p else "—",
        )
        if last_p:
            last_prices[(exchange, asset, fiat, trade_type)] = last_p

    console.print(t)

    # Inter-exchange spread (Binance vs Bybit)
    shown = False
    for asset_fiat in sorted({(a, f) for _, a, f, *_ in rows_data}):
        asset, fiat = asset_fiat
        for tt in ("BUY", "SELL"):
            bn = last_prices.get(("binance", asset, fiat, tt))
            bb = last_prices.get(("bybit", asset, fiat, tt))
            if bn is None or bb is None:
                continue
            if not shown:
                console.print("\n[bold]Текущие спреды Binance ↔ Bybit:[/bold]")
                shown = True
            diff = bn - bb
            who = "Binance дороже" if diff > 0 else "Bybit дороже" if diff < 0 else "—"
            c = "red" if abs(diff) > 0.1 else "green"
            console.print(
                f"  {asset}/{fiat} {tt}:  "
                f"Binance [cyan]{bn:.2f}[/cyan]  Bybit [cyan]{bb:.2f}[/cyan]  "
                f"[{c}]спред {diff:+.2f}[/{c}]  [dim]{who}[/dim]"
            )

    # Intra-exchange spread (BUY vs SELL on same exchange)
    shown2 = False
    for asset_fiat in sorted({(a, f) for _, a, f, *_ in rows_data}):
        asset, fiat = asset_fiat
        for exchange in ("binance", "bybit"):
            buy_p = last_prices.get((exchange, asset, fiat, "BUY"))
            sell_p = last_prices.get((exchange, asset, fiat, "SELL"))
            if buy_p is None or sell_p is None:
                continue
            if not shown2:
                console.print("\n[bold]Внутрибиржевой спред (BUY vs SELL):[/bold]")
                shown2 = True
            spread = sell_p - buy_p
            pct = (spread / buy_p * 100) if buy_p else 0.0
            if pct < 1.5:
                sc = "green"
            elif pct < 3.0:
                sc = "yellow"
            else:
                sc = "red"
            console.print(
                f"  {asset}/{fiat} {exchange.upper()}:  "
                f"BUY [cyan]{buy_p:.2f}[/cyan]  "
                f"SELL [cyan]{sell_p:.2f}[/cyan]  "
                f"[{sc}]спред {spread:.2f} UAH ({pct:.2f}%)[/{sc}]"
            )


# ── cmd: chart ────────────────────────────────────────────────────────────────

def cmd_chart(args: argparse.Namespace) -> None:
    asset, fiat = _parse_pair(args.pair)
    hours = getattr(args, "hours", None)
    side: str = getattr(args, "side", "BOTH").upper()
    raw: bool = getattr(args, "raw", False)
    cut = _cutoff(hours)
    price_label = "(сырые цены)" if raw else "(чистые цены)"

    sides = ["BUY", "SELL"] if side == "BOTH" else [side]
    period_label = f"последние {hours} ч" if hours else "все данные"
    console.rule(f"[bold cyan]{asset}/{fiat} — {period_label} {price_label}[/bold cyan]")

    with get_session() as session:
        total = session.execute(
            select(func.count()).select_from(Snapshot)
            .where(Snapshot.asset == asset, Snapshot.fiat == fiat)
        ).scalar() or 0
        if total == 0:
            avail = session.execute(
                select(Snapshot.asset, Snapshot.fiat).distinct()
            ).all()
            pairs_str = ", ".join(f"{r.asset}/{r.fiat}" for r in avail)
            _no_data(
                f"Нет данных для {asset}/{fiat}. "
                + (f"Доступные пары: {pairs_str}" if avail else "БД пустая.")
            )

        for exchange in ("binance", "bybit"):
            for trade_type in sides:
                if raw:
                    w = _snap_where(exchange, asset, fiat, trade_type, cut)
                    series_rows = session.execute(
                        select(Snapshot.collected_at, _best_fn(trade_type).label("bp"))
                        .join(Order, Order.snapshot_id == Snapshot.id)
                        .where(*w)
                        .group_by(Snapshot.id, Snapshot.collected_at)
                        .order_by(Snapshot.collected_at.asc())
                    ).all()
                    if not series_rows:
                        console.print(f"\n[dim]{exchange.upper()} {trade_type}: нет данных[/dim]")
                        continue
                    timestamps = [r.collected_at for r in series_rows]
                    prices = [r.bp for r in series_rows]
                else:
                    pts = _clean_series(session, exchange, asset, fiat, trade_type, cut)
                    if not pts:
                        console.print(f"\n[dim]{exchange.upper()} {trade_type}: нет данных[/dim]")
                        continue
                    timestamps = [ts for ts, _ in pts]
                    prices = [p for _, p in pts]

                min_p, max_p = min(prices), max(prices)
                avg_p = sum(prices) / len(prices)
                last_p = prices[-1]

                c = "green" if trade_type == "BUY" else "red"
                console.print(
                    f"\n[bold]{exchange.upper()}[/bold] [{c}]{trade_type}[/{c}]  "
                    f"[dim]{len(prices)} точек[/dim]"
                )
                console.print(
                    f"  Min=[cyan]{min_p:.2f}[/cyan]  "
                    f"Max=[cyan]{max_p:.2f}[/cyan]  "
                    f"Avg=[cyan]{avg_p:.2f}[/cyan]  "
                    f"Сейчас=[bold]{last_p:.2f}[/bold]"
                )

                chart_w = min(len(prices), 60)
                if len(prices) > chart_w:
                    step = len(prices) / chart_w
                    sampled_p = [prices[int(i * step)] for i in range(chart_w)]
                    sampled_ts = [timestamps[int(i * step)] for i in range(chart_w)]
                else:
                    sampled_p, sampled_ts = prices[:], timestamps[:]

                for line in _render_chart(sampled_p, height=7):
                    console.print("  " + line)
                console.print("  " + _x_axis_labels(sampled_ts, chart_w))


# ── cmd: spread ───────────────────────────────────────────────────────────────

def cmd_spread(args: argparse.Namespace) -> None:
    asset, fiat = _parse_pair(args.pair)
    hours = getattr(args, "hours", None)
    raw: bool = getattr(args, "raw", False)
    cut = _cutoff(hours)
    price_label = "(сырые цены)" if raw else "(чистые цены, --raw для сырых)"
    period_label = f"последние {hours} ч" if hours else "все данные"
    console.rule(
        f"[bold cyan]Спред Binance ↔ Bybit — {asset}/{fiat} — {period_label} {price_label}[/bold cyan]"
    )

    with get_session() as session:
        total = session.execute(
            select(func.count()).select_from(Snapshot)
            .where(Snapshot.asset == asset, Snapshot.fiat == fiat)
        ).scalar() or 0
        if total == 0:
            _no_data(f"Нет данных для {asset}/{fiat}.")

        console.print()
        for trade_type in ("BUY", "SELL"):
            cur: dict[str, tuple[float, datetime]] = {}
            for exchange in ("binance", "bybit"):
                row = session.execute(
                    select(Snapshot.id, Snapshot.collected_at)
                    .where(*_snap_where(exchange, asset, fiat, trade_type))
                    .order_by(Snapshot.collected_at.desc()).limit(1)
                ).one_or_none()
                if row:
                    if raw:
                        p = session.execute(
                            select(_best_fn(trade_type)).where(Order.snapshot_id == row[0])
                        ).scalar()
                    else:
                        snap_orders = session.execute(
                            select(Order.snapshot_id, Order.price)
                            .where(Order.snapshot_id == row[0])
                            .order_by(Order.price.asc() if trade_type == "BUY" else Order.price.desc())
                            .limit(5)
                        ).all()
                        clean, _ = filter_outliers(snap_orders, trade_type)
                        p = float(clean[0].price) if clean else None
                    if p:
                        cur[exchange] = (p, row[1])

            if len(cur) == 2:
                bn_p, bn_ts = cur["binance"]
                bb_p, bb_ts = cur["bybit"]
                diff = bn_p - bb_p
                last_ts_val = max(bn_ts, bb_ts)
                c = "red" if abs(diff) > 0.15 else "yellow" if abs(diff) > 0.05 else "green"
                console.print(
                    f"[bold]Сейчас[/bold] ({format_kyiv(last_ts_val)})  {trade_type}:  "
                    f"Binance=[cyan]{bn_p:.2f}[/cyan]  Bybit=[cyan]{bb_p:.2f}[/cyan]  "
                    f"[{c}]спред {diff:+.2f}[/{c}]"
                )

        TimeMap = dict[datetime, float]
        series: dict[tuple[str, str], TimeMap] = {}
        for exchange in ("binance", "bybit"):
            for trade_type in ("BUY", "SELL"):
                if raw:
                    rows = session.execute(
                        select(Snapshot.collected_at, _best_fn(trade_type).label("bp"))
                        .join(Order, Order.snapshot_id == Snapshot.id)
                        .where(*_snap_where(exchange, asset, fiat, trade_type, cut))
                        .group_by(Snapshot.id, Snapshot.collected_at)
                        .order_by(Snapshot.collected_at.asc())
                    ).all()
                    series[(exchange, trade_type)] = {r.collected_at: r.bp for r in rows}
                else:
                    pts = _clean_series(session, exchange, asset, fiat, trade_type, cut)
                    series[(exchange, trade_type)] = {ts: p for ts, p in pts}

    bn_buy  = series.get(("binance", "BUY"), {})
    bb_buy  = series.get(("bybit",   "BUY"), {})
    bn_sell = series.get(("binance", "SELL"), {})
    bb_sell = series.get(("bybit",   "SELL"), {})

    bb_buy_ts  = sorted(bb_buy)
    bb_sell_ts = sorted(bb_sell)
    bn_sell_ts = sorted(bn_sell)

    def nearest(ts: datetime, ts_list: list[datetime]) -> datetime | None:
        if not ts_list:
            return None
        best = min(ts_list, key=lambda t: abs((t - ts).total_seconds()))
        return best if abs((best - ts).total_seconds()) <= 120 else None

    combined: list[tuple] = []
    for ts, bn_b in sorted(bn_buy.items()):
        ns_bn = nearest(ts, bn_sell_ts)
        bn_s  = bn_sell.get(ns_bn) if ns_bn else None
        nb    = nearest(ts, bb_buy_ts)
        ns    = nearest(ts, bb_sell_ts)
        bb_b  = bb_buy.get(nb) if nb else None
        bb_s  = bb_sell.get(ns) if ns else None
        combined.append((ts, bn_b, bb_b, bn_s, bb_s))

    if not combined:
        console.print("[yellow]Недостаточно данных для сравнения бирж.[/yellow]")
        return

    sp_buy_all  = [(r[1] - r[2]) for r in combined if r[1] and r[2]]
    sp_sell_all = [(r[3] - r[4]) for r in combined if r[3] and r[4]]

    display = combined[-20:]
    console.print(
        f"\n[bold]Динамика спреда[/bold]"
        f" [dim](последние {len(display)} из {len(combined)} точек)[/dim]\n"
    )

    def _fmt_sp(v: float | None) -> str:
        if v is None:
            return "—"
        c = "red" if abs(v) > 0.15 else "yellow" if abs(v) > 0.05 else "green"
        return f"[{c}]{v:+.2f}[/{c}]"

    t = Table(show_header=True, header_style="bold cyan", border_style="dim")
    t.add_column("Время (Киев)")
    t.add_column("BN BUY",  justify="right")
    t.add_column("BB BUY",  justify="right")
    t.add_column("Спред BUY",  justify="right")
    t.add_column("BN SELL", justify="right")
    t.add_column("BB SELL", justify="right")
    t.add_column("Спред SELL", justify="right")

    for ts, bn_b, bb_b, bn_s, bb_s in display:
        sp_b = (bn_b - bb_b) if (bn_b and bb_b) else None
        sp_s = (bn_s - bb_s) if (bn_s and bb_s) else None
        t.add_row(
            format_kyiv(ts, "%d.%m %H:%M"),
            f"{bn_b:.2f}" if bn_b else "—",
            f"{bb_b:.2f}" if bb_b else "—",
            _fmt_sp(sp_b),
            f"{bn_s:.2f}" if bn_s else "—",
            f"{bb_s:.2f}" if bb_s else "—",
            _fmt_sp(sp_s),
        )
    console.print(t)

    console.print()
    for label, spreads in (("BUY", sp_buy_all), ("SELL", sp_sell_all)):
        if spreads:
            arb = sum(1 for s in spreads if abs(s) > 0.20)
            console.print(
                f"  Спред {label}: "
                f"min={min(spreads):+.2f}  max={max(spreads):+.2f}  "
                f"avg={sum(spreads) / len(spreads):+.2f}  "
                f"[yellow]арбитражных окон (>0.20 UAH): {arb}[/yellow]"
            )


# ── cmd: makers ───────────────────────────────────────────────────────────────

def cmd_makers(args: argparse.Namespace) -> None:
    asset, fiat = _parse_pair(args.pair)
    side: str = getattr(args, "side", "BUY").upper()
    top_n: int = getattr(args, "top", 10)
    ex_arg: str = getattr(args, "exchange", "both").lower()

    console.rule(f"[bold cyan]Топ-{top_n} мейкеров {asset}/{fiat} {side}[/bold cyan]")

    with get_session() as session:
        total = session.execute(
            select(func.count()).select_from(Snapshot)
            .where(Snapshot.asset == asset, Snapshot.fiat == fiat, Snapshot.trade_type == side)
        ).scalar() or 0
        if total == 0:
            _no_data(f"Нет данных для {asset}/{fiat} {side}.")

        ex_cond = [] if ex_arg == "both" else [Snapshot.exchange == ex_arg]

        q = (
            select(
                Maker.nickname,
                Maker.exchange,
                Maker.total_orders,
                Maker.completion_rate,
                Maker.is_merchant,
                func.count(Order.snapshot_id.distinct()).label("appearances"),
                func.avg(Order.price).label("avg_price"),
                _best_fn(side).label("best_price"),
            )
            .join(Order, Order.maker_id == Maker.id)
            .join(Snapshot, Order.snapshot_id == Snapshot.id)
            .where(
                Snapshot.asset == asset,
                Snapshot.fiat == fiat,
                Snapshot.trade_type == side,
                *ex_cond,
            )
            .group_by(Maker.id)
            .order_by(func.count(Order.snapshot_id.distinct()).desc())
            .limit(top_n)
        )
        results = session.execute(q).all()

    if not results:
        _no_data(f"Нет данных для {asset}/{fiat} {side}.")

    t = Table(show_header=True, header_style="bold cyan", border_style="dim")
    t.add_column("Ник")
    t.add_column("Биржа")
    t.add_column("Появлений", justify="right")
    t.add_column("Avg цена",  justify="right")
    t.add_column("Best цена", justify="right")
    t.add_column("Всего сделок", justify="right")
    t.add_column("Completion%", justify="right")
    t.add_column("★")

    for r in results:
        t.add_row(
            r.nickname, r.exchange,
            str(r.appearances),
            f"{r.avg_price:.2f}" if r.avg_price else "—",
            f"{r.best_price:.2f}" if r.best_price else "—",
            str(r.total_orders),
            f"{r.completion_rate:.1f}%",
            "★" if r.is_merchant else "",
        )
    console.print(t)


# ── cmd: latest ───────────────────────────────────────────────────────────────

def cmd_latest(args: argparse.Namespace) -> None:
    raw: bool = getattr(args, "raw", False)

    with get_session() as session:
        if not session.execute(select(func.count()).select_from(Snapshot)).scalar():
            _no_data()

        last_ts = session.execute(select(func.max(Snapshot.collected_at))).scalar()
        console.print(
            f"\n[bold]Последнее обновление:[/bold] "
            f"[cyan]{format_kyiv(last_ts, '%d.%m.%Y %H:%M:%S')} Киев[/cyan]\n"
        )

        groups = session.execute(
            select(Snapshot.exchange, Snapshot.asset, Snapshot.fiat, Snapshot.trade_type)
            .distinct()
            .order_by(Snapshot.asset, Snapshot.fiat, Snapshot.exchange, Snapshot.trade_type)
        ).all()

        for exchange, asset, fiat, trade_type in groups:
            snap = session.execute(
                select(Snapshot.id, Snapshot.collected_at, Snapshot.order_count)
                .where(*_snap_where(exchange, asset, fiat, trade_type))
                .order_by(Snapshot.collected_at.desc()).limit(1)
            ).one_or_none()
            if not snap:
                continue
            snap_id, snap_ts, snap_cnt = snap

            orders = session.execute(
                select(Order.price, Order.available_amount, Order.min_amount, Order.max_amount,
                       Maker.nickname, Maker.total_orders, Maker.completion_rate, Maker.is_merchant)
                .join(Maker, Order.maker_id == Maker.id)
                .where(Order.snapshot_id == snap_id)
                .order_by(Order.price.asc() if trade_type == "BUY" else Order.price.desc())
                .limit(5)
            ).all()

            # Build outlier flags
            outlier_set: set[int] = set()
            if not raw and orders:
                clean, _ = filter_outliers(orders, trade_type)
                clean_prices = {float(o.price) for o in clean}
                outlier_set = {i for i, o in enumerate(orders) if float(o.price) not in clean_prices}

            c = "green" if trade_type == "BUY" else "red"
            console.print(
                f"[bold]{exchange.upper()}[/bold] "
                f"[{c}]{asset}/{fiat} {trade_type}[/{c}]  "
                f"[dim](снимок #{snap_id}, {format_kyiv(snap_ts)}, {snap_cnt} ордеров)[/dim]"
            )

            t = Table(show_header=True, header_style="cyan", box=None, padding=(0, 1))
            t.add_column("Цена", justify="right", style=c)
            t.add_column("Доступно", justify="right")
            t.add_column(f"Min {fiat}", justify="right")
            t.add_column(f"Max {fiat}", justify="right")
            t.add_column("Мейкер")
            t.add_column("Сделок", justify="right")
            t.add_column("%", justify="right")
            if not raw:
                t.add_column("OK", justify="center")

            for i, o in enumerate(orders):
                merchant = " ★" if o.is_merchant else ""
                row_vals = [
                    f"{o.price:.2f}", f"{o.available_amount:.2f}",
                    f"{o.min_amount:.0f}", f"{o.max_amount:.0f}",
                    o.nickname + merchant,
                    str(o.total_orders), f"{o.completion_rate:.1f}%",
                ]
                if not raw:
                    row_vals.append("[red]✗[/red]" if i in outlier_set else "[green]✓[/green]")
                t.add_row(*row_vals)
            console.print(t)
            console.print()


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="market",
        description="P2P Market Viewer — просмотрщик данных трекера",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("summary", help="Общая сводка по всем парам")
    p.add_argument("--hours", type=int, default=None, metavar="N",
                   help="Показать только последние N часов")
    p.add_argument("--raw", action="store_true", help="Сырые цены без фильтрации выбросов")

    p = sub.add_parser("chart", help="ASCII-график цены пары")
    p.add_argument("pair", help="Пара: USDT/UAH, USDC/UAH …")
    p.add_argument("--hours", type=int, default=None, metavar="N")
    p.add_argument("--side", default="BOTH", choices=["BUY", "SELL", "BOTH"])
    p.add_argument("--raw", action="store_true", help="Сырые цены без фильтрации выбросов")

    p = sub.add_parser("spread", help="Спред Binance ↔ Bybit")
    p.add_argument("pair", help="Пара: USDT/UAH …")
    p.add_argument("--hours", type=int, default=None, metavar="N")
    p.add_argument("--raw", action="store_true", help="Сырые цены без фильтрации выбросов")

    p = sub.add_parser("makers", help="Топ мейкеров пары")
    p.add_argument("pair", help="Пара: USDT/UAH …")
    p.add_argument("--side", default="BUY", choices=["BUY", "SELL"])
    p.add_argument("--top", type=int, default=10, metavar="N")
    p.add_argument("--exchange", default="both", choices=["binance", "bybit", "both"])

    p = sub.add_parser("latest", help="Текущий снимок всех пар (топ-5)")
    p.add_argument("--raw", action="store_true", help="Без меток выбросов")

    args = parser.parse_args()
    {
        "summary": cmd_summary,
        "chart":   cmd_chart,
        "spread":  cmd_spread,
        "makers":  cmd_makers,
        "latest":  cmd_latest,
    }[args.command](args)


if __name__ == "__main__":
    main()
