from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal

import httpx
from rich.console import Console
from rich.table import Table

from core.utils.logger import get_logger

_logger = get_logger("binance")

_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

TradeType = Literal["BUY", "SELL"]


@dataclass
class BinanceP2POrder:
    position: int
    external_id: str
    price: float
    available_amount: float
    min_amount: float
    max_amount: float
    maker_nickname: str
    trade_count: int
    completion_rate: float
    payment_methods: list[str] = field(default_factory=list)


class BinanceP2PClient:
    def __init__(self) -> None:
        self._client: httpx.Client | None = None

    def __enter__(self) -> "BinanceP2PClient":
        self._client = httpx.Client(headers=_HEADERS, timeout=15.0)
        return self

    def __exit__(self, *_) -> None:
        if self._client:
            self._client.close()
            self._client = None

    _MAX_ROWS_PER_PAGE = 20

    def _fetch_page(
        self,
        asset: str,
        fiat: str,
        trade_type: TradeType,
        page: int,
        rows_per_page: int,
    ) -> list[dict]:
        payload = {
            "asset": asset,
            "fiat": fiat,
            "merchantCheck": False,
            "page": page,
            "payTypes": [],
            "publisherType": None,
            "rows": rows_per_page,
            "tradeType": trade_type,
        }
        try:
            response = self._client.post(_P2P_URL, json=payload)  # type: ignore[union-attr]
            response.raise_for_status()
        except httpx.HTTPError as exc:
            _logger.error("HTTP error %s/%s %s p%d: %s", asset, fiat, trade_type, page, exc)
            raise
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            _logger.error("JSONDecodeError %s/%s %s p%d: %s", asset, fiat, trade_type, page, exc)
            raise
        if data.get("code") != "000000":
            msg = data.get("message") or f"code={data.get('code')}"
            raise RuntimeError(f"Binance P2P API error: {msg}")
        return data.get("data") or []

    def fetch_orders(
        self,
        asset: str = "USDT",
        fiat: str = "UAH",
        trade_type: TradeType = "BUY",
        rows: int = 20,
    ) -> list[BinanceP2POrder]:
        assert self._client is not None, "Use BinanceP2PClient as a context manager"

        import math
        pages_needed = math.ceil(rows / self._MAX_ROWS_PER_PAGE)
        all_items: list[dict] = []
        for page in range(1, pages_needed + 1):
            rows_this_page = min(self._MAX_ROWS_PER_PAGE, rows - len(all_items))
            items = self._fetch_page(asset, fiat, trade_type, page, rows_this_page)
            all_items.extend(items)
            if len(items) < rows_this_page:
                break  # no more data

        orders: list[BinanceP2POrder] = []
        for i, item in enumerate(all_items):
            adv = item["adv"]
            advertiser = item["advertiser"]
            methods = [m["tradeMethodName"] for m in adv.get("tradeMethods", [])]
            orders.append(BinanceP2POrder(
                position=i + 1,
                external_id=str(advertiser.get("userNo") or advertiser["nickName"]),
                price=float(adv["price"]),
                available_amount=float(adv["surplusAmount"]),
                min_amount=float(adv["minSingleTransAmount"]),
                max_amount=float(adv["maxSingleTransAmount"]),
                maker_nickname=advertiser["nickName"],
                trade_count=int(advertiser.get("monthOrderCount") or 0),
                completion_rate=float(advertiser.get("monthFinishRate") or 0) * 100,
                payment_methods=methods,
            ))

        _logger.info(
            "Binance %s/%s %s: получено %d ордеров (pages=%d)",
            asset, fiat, trade_type, len(orders), pages_needed,
        )
        return orders


if __name__ == "__main__":
    console = Console()

    with BinanceP2PClient() as client:
        for trade_type in ("BUY", "SELL"):
            orders = client.fetch_orders("USDT", "UAH", trade_type, rows=5)  # type: ignore[arg-type]

            color = "green" if trade_type == "BUY" else "red"
            table = Table(
                title=f"[bold]Binance P2P · USDT/UAH · {trade_type}[/bold]",
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
            table.add_column("Методы")

            for o in orders:
                methods_str = ", ".join(o.payment_methods[:3])
                if len(o.payment_methods) > 3:
                    methods_str += ", …"
                table.add_row(
                    str(o.position),
                    f"{o.price:.2f}",
                    f"{o.available_amount:.2f}",
                    f"{o.min_amount:.0f}",
                    f"{o.max_amount:.0f}",
                    o.maker_nickname,
                    str(o.trade_count),
                    f"{o.completion_rate:.1f}%",
                    methods_str,
                )

            console.print(table)
            console.print()
