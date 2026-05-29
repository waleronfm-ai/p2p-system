from __future__ import annotations


def calc_realized_pnl(
    buy_uah: float,
    buy_usdt: float,
    sell_uah: float,
    sell_usdt: float,
) -> float | None:
    if not buy_usdt:
        return None
    avg_buy_price = buy_uah / buy_usdt
    return round(sell_uah - sell_usdt * avg_buy_price, 4)
