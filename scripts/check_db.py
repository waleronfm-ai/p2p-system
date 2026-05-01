from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

from sqlalchemy import func, select
from rich.console import Console
from rich.table import Table

from core.database import Maker, Order, Snapshot, get_session
from core.utils.timezone import format_kyiv


def main() -> None:
    console = Console()

    with get_session() as session:
        # --- Makers ---
        total_makers = session.execute(select(func.count()).select_from(Maker)).scalar() or 0
        makers_by_exchange = session.execute(
            select(Maker.exchange, func.count(Maker.id)).group_by(Maker.exchange)
        ).all()

        # --- Snapshots ---
        total_snapshots = session.execute(select(func.count()).select_from(Snapshot)).scalar() or 0
        snaps_by_type = session.execute(
            select(
                Snapshot.exchange,
                Snapshot.asset,
                Snapshot.trade_type,
                Snapshot.is_deep,
                func.count(Snapshot.id),
            ).group_by(Snapshot.exchange, Snapshot.asset, Snapshot.trade_type, Snapshot.is_deep)
        ).all()

        # --- Orders ---
        total_orders = session.execute(select(func.count()).select_from(Order)).scalar() or 0

        # --- Last 5 snapshots ---
        last_snaps_rows = session.execute(
            select(
                Snapshot.id,
                Snapshot.exchange,
                Snapshot.asset,
                Snapshot.fiat,
                Snapshot.trade_type,
                Snapshot.is_deep,
                Snapshot.collected_at,
                Snapshot.order_count,
            ).order_by(Snapshot.collected_at.desc()).limit(5)
        ).all()

        # --- Top-3 orders from last USDT/UAH/BUY snapshot per exchange ---
        top_orders_data: dict[str, list[tuple[float, float, str]]] = {}
        for exchange in ["binance", "bybit"]:
            last_snap = session.execute(
                select(Snapshot.id).where(
                    Snapshot.exchange == exchange,
                    Snapshot.asset == "USDT",
                    Snapshot.fiat == "UAH",
                    Snapshot.trade_type == "BUY",
                ).order_by(Snapshot.collected_at.desc()).limit(1)
            ).scalar_one_or_none()

            if last_snap is not None:
                rows = session.execute(
                    select(Order.price, Order.available_amount, Maker.nickname)
                    .join(Maker, Order.maker_id == Maker.id)
                    .where(Order.snapshot_id == last_snap)
                    .order_by(Order.price.asc())
                    .limit(3)
                ).all()
                top_orders_data[exchange] = [(r.price, r.available_amount, r.nickname) for r in rows]

    # ── Print ──────────────────────────────────────────────────────────────
    console.rule("[bold cyan]Состояние БД")

    console.print(f"\n[bold]Мейкеры:[/] {total_makers}")
    for exchange, count in makers_by_exchange:
        console.print(f"  {exchange}: {count}")

    console.print(f"\n[bold]Снимков:[/] {total_snapshots}")
    if snaps_by_type:
        t = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
        t.add_column("Биржа")
        t.add_column("Актив")
        t.add_column("Тип")
        t.add_column("Deep")
        t.add_column("Кол-во", justify="right")
        for exchange, asset, trade_type, is_deep, count in snaps_by_type:
            t.add_row(exchange, asset, trade_type, "да" if is_deep else "нет", str(count))
        console.print(t)

    console.print(f"\n[bold]Ордеров:[/] {total_orders}")

    if last_snaps_rows:
        console.print("\n[bold]Последние 5 снимков:[/]")
        t = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
        t.add_column("ID", justify="right")
        t.add_column("Время (Киев)")
        t.add_column("Биржа")
        t.add_column("Актив")
        t.add_column("Тип")
        t.add_column("Deep")
        t.add_column("Ордеров", justify="right")
        for row in last_snaps_rows:
            t.add_row(
                str(row.id),
                format_kyiv(row.collected_at),
                row.exchange,
                f"{row.asset}/{row.fiat}",
                row.trade_type,
                "да" if row.is_deep else "нет",
                str(row.order_count),
            )
        console.print(t)

    for exchange, rows in top_orders_data.items():
        if rows:
            console.print(f"\n[bold]Топ-3 ордера (последний {exchange.upper()} USDT/UAH BUY):[/]")
            t = Table(show_header=True, header_style="bold green", box=None, padding=(0, 2))
            t.add_column("Цена", justify="right")
            t.add_column("Доступно", justify="right")
            t.add_column("Мейкер")
            for price, avail, nickname in rows:
                t.add_row(f"{price:.2f}", f"{avail:.2f}", nickname)
            console.print(t)

    console.rule()


if __name__ == "__main__":
    main()
