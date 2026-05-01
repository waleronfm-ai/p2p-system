from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal

import httpx
from rich.console import Console
from rich.table import Table

from core.utils.logger import get_logger

_logger = get_logger("bybit")

_P2P_URL = "https://api2.bybit.com/fiat/otc/item/online"
_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

TradeType = Literal["BUY", "SELL"]

# Bybit side semantics are inverted vs Binance:
# side=1 → maker sells crypto (we BUY), side=0 → maker buys crypto (we SELL)
_SIDE_MAP: dict[TradeType, str] = {"BUY": "1", "SELL": "0"}


@dataclass
class BybitP2POrder:
    position: int
    external_id: str
    price: float
    available_amount: float
    min_amount: float
    max_amount: float
    maker_nickname: str
    trade_count: int
    completion_rate: float         # already in %, e.g. 98.0 means 98%
    payment_methods: list[str] = field(default_factory=list)  # payment IDs; map to names later
    is_merchant: bool = False      # authStatus == 1


class BybitP2PClient:
    def __init__(self) -> None:
        self._client: httpx.Client | None = None

    def __enter__(self) -> "BybitP2PClient":
        self._client = httpx.Client(headers=_HEADERS, timeout=15.0)
        return self

    def __exit__(self, *_) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def fetch_orders(
        self,
        asset: str = "USDT",
        fiat: str = "UAH",
        trade_type: TradeType = "BUY",
        rows: int = 20,
    ) -> list[BybitP2POrder]:
        assert self._client is not None, "Use BybitP2PClient as a context manager"

        payload = {
            "userId": "",
            "tokenId": asset,
            "currencyId": fiat,
            "payment": [],
            "side": _SIDE_MAP[trade_type],
            "size": str(rows),
            "page": "1",
            "amount": "",
            "authMaker": False,
            "canTrade": False,
        }

        try:
            response = self._client.post(_P2P_URL, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            _logger.error("HTTP error %s/%s %s: %s", asset, fiat, trade_type, exc)
            raise

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            _logger.error("JSONDecodeError %s/%s %s: %s", asset, fiat, trade_type, exc)
            raise

        if data.get("ret_code") != 0:
            msg = data.get("ret_msg") or f"ret_code={data.get('ret_code')}"
            raise RuntimeError(f"Bybit P2P API error: {msg}")

        items = data.get("result", {}).get("items") or []
        orders: list[BybitP2POrder] = []
        for i, item in enumerate(items):
            orders.append(BybitP2POrder(
                position=i + 1,
                external_id=str(item.get("userId") or item.get("nickName", "")),
                price=float(item["price"]),
                available_amount=float(item["quantity"]),
                min_amount=float(item["minAmount"]),
                max_amount=float(item["maxAmount"]),
                maker_nickname=item["nickName"],
                trade_count=int(item.get("recentOrderNum") or 0),
                completion_rate=float(item.get("recentExecuteRate") or 0),
                payment_methods=[str(p) for p in item.get("payments", [])],
                is_merchant=int(item.get("authStatus") or 0) == 1,
            ))

        _logger.info(
            "Bybit %s/%s %s: получено %d ордеров",
            asset, fiat, trade_type, len(orders),
        )
        return orders


if __name__ == "__main__":
    console = Console()

    with BybitP2PClient() as client:
        for trade_type in ("BUY", "SELL"):
            orders = client.fetch_orders("USDT", "UAH", trade_type, rows=5)  # type: ignore[arg-type]

            color = "green" if trade_type == "BUY" else "red"
            table = Table(
                title=f"[bold]Bybit P2P · USDT/UAH · {trade_type}[/bold]",
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("№", style="dim", width=3, justify="right")
            table.add_column("Цена", style=color, justify="right")
            table.add_column("Доступно USDT", justify="right")
            table.add_column("Мин фиат", justify="right")
            table.add_column("Макс фиат", justify="right")
            table.add_column("Мейкер")
            table.add_column("Сделок", justify="right")
            table.add_column("%", justify="right")
            table.add_column("Методы (ID)")

            for o in orders:
                merchant_mark = " ★" if o.is_merchant else ""
                methods_str = ", ".join(o.payment_methods[:3])
                if len(o.payment_methods) > 3:
                    methods_str += ", …"
                table.add_row(
                    str(o.position),
                    f"{o.price:.2f}",
                    f"{o.available_amount:.2f}",
                    f"{o.min_amount:.0f}",
                    f"{o.max_amount:.0f}",
                    o.maker_nickname + merchant_mark,
                    str(o.trade_count),
                    f"{o.completion_rate:.1f}%",
                    methods_str,
                )

            console.print(table)
            console.print()
