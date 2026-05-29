from __future__ import annotations

import json
import random
import time
from datetime import UTC, datetime

import httpx
from pathlib import Path
from typing import Any, Union

from sqlalchemy import select

from core.database import Maker, Order, Snapshot, get_session
from core.exchanges.binance import BinanceP2PClient, BinanceP2POrder
from core.exchanges.bybit import BybitP2PClient, BybitP2POrder
from core.utils.logger import get_logger
from core.utils.timezone import now_kyiv
from .config import TrackerConfig, DEFAULT_CONFIG

_logger = get_logger("tracker")

AnyOrder = Union[BinanceP2POrder, BybitP2POrder]


def _setup_error_log() -> None:
    import logging
    log_dir = Path(__file__).parents[2] / "logs"
    log_dir.mkdir(exist_ok=True)
    error_path = log_dir / "errors.log"

    handler = logging.FileHandler(error_path, encoding="utf-8")
    handler.setLevel(logging.ERROR)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    for name in ("tracker", "binance", "bybit"):
        lg = logging.getLogger(name)
        if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(error_path)
                   for h in lg.handlers):
            lg.addHandler(handler)


def _pause(cfg: TrackerConfig) -> None:
    time.sleep(random.uniform(cfg.min_pause_seconds, cfg.max_pause_seconds))


_RATE_LIMIT_PAUSE = 90.0  # seconds to wait on HTTP 429


def _with_retry(fn: Any, cfg: TrackerConfig, label: str) -> Any:
    last_exc: Exception | None = None
    for attempt in range(cfg.max_retries):
        try:
            return fn()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 429:
                last_exc = exc
                if attempt < cfg.max_retries - 1:
                    _logger.warning(
                        "[%s] HTTP 429 rate limit (попытка %d/%d) — пауза %.0f с",
                        label, attempt + 1, cfg.max_retries, _RATE_LIMIT_PAUSE,
                    )
                    time.sleep(_RATE_LIMIT_PAUSE)
                else:
                    _logger.error("[%s] HTTP 429 — все попытки исчерпаны: %s", label, exc)
            elif 400 <= status < 500:
                _logger.error("[%s] HTTP %d — fail fast: %s", label, status, exc)
                raise
            else:  # 5xx
                last_exc = exc
                delay = min(cfg.retry_base_delay * (2 ** attempt), cfg.retry_max_delay)
                if attempt < cfg.max_retries - 1:
                    _logger.warning(
                        "[%s] HTTP %d (попытка %d/%d) — повтор через %.1f с",
                        label, status, attempt + 1, cfg.max_retries, delay,
                    )
                    time.sleep(delay)
                else:
                    _logger.error("[%s] HTTP %d — все попытки исчерпаны: %s", label, status, exc)
        except RuntimeError as exc:
            _logger.error("[%s] API бизнес-ошибка — fail fast: %s", label, exc)
            raise
        except httpx.TransportError as exc:
            last_exc = exc
            delay = min(cfg.retry_base_delay * (2 ** attempt), cfg.retry_max_delay)
            if attempt < cfg.max_retries - 1:
                _logger.warning(
                    "[%s] сетевая ошибка (попытка %d/%d) — повтор через %.1f с: %s",
                    label, attempt + 1, cfg.max_retries, delay, exc,
                )
                time.sleep(delay)
            else:
                _logger.error("[%s] сетевая ошибка — все попытки исчерпаны: %s", label, exc)
        except Exception as exc:
            last_exc = exc
            delay = min(cfg.retry_base_delay * (2 ** attempt), cfg.retry_max_delay)
            if attempt < cfg.max_retries - 1:
                _logger.warning(
                    "[%s] ошибка (попытка %d/%d) — повтор через %.1f с: %s",
                    label, attempt + 1, cfg.max_retries, delay, exc,
                )
                time.sleep(delay)
            else:
                _logger.error("[%s] ошибка — все попытки исчерпаны: %s", label, exc)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"[{label}] retry loop exhausted without exception")


class Collector:
    def __init__(self, cfg: TrackerConfig = DEFAULT_CONFIG) -> None:
        self.cfg = cfg
        _setup_error_log()

    def _collect_pair(
        self,
        exchange: str,
        asset: str,
        fiat: str,
        trade_type: str,
        rows: int,
    ) -> list[AnyOrder] | None:
        """Fetch orders for one (exchange, asset, fiat, trade_type). Returns None on failure."""
        label = f"{exchange.upper()} {asset}/{fiat} {trade_type}"
        try:
            if exchange == "binance":
                with BinanceP2PClient() as client:
                    orders = _with_retry(
                        lambda: client.fetch_orders(asset, fiat, trade_type, rows),  # type: ignore[arg-type]
                        self.cfg,
                        label,
                    )
            else:
                with BybitP2PClient() as client:
                    orders = _with_retry(
                        lambda: client.fetch_orders(asset, fiat, trade_type, rows),  # type: ignore[arg-type]
                        self.cfg,
                        label,
                    )

            if orders:
                prices = [o.price for o in orders]
                _logger.info(
                    "%-30s | %2d ордеров | цены %.2f–%.2f",
                    label, len(orders), min(prices), max(prices),
                )
            else:
                _logger.warning("%s | ответ пустой", label)

            return orders

        except Exception as exc:
            _logger.error("%s | сбор провалился после всех попыток: %s", label, exc)
            return None

    def _save_to_db(
        self,
        exchange: str,
        asset: str,
        fiat: str,
        trade_type: str,
        orders: list[AnyOrder],
        is_deep: bool,
    ) -> int:
        """UPSERT makers → create Snapshot → create Orders. Returns saved order count."""
        label = f"{exchange.upper()} {asset}/{fiat} {trade_type}"
        try:
            with get_session() as session:
                now = datetime.now(UTC)

                # Deduplicate makers by external_id (rare duplicates in one response)
                unique_orders: dict[str, AnyOrder] = {}
                for o in orders:
                    if o.external_id not in unique_orders:
                        unique_orders[o.external_id] = o

                # UPSERT each unique maker
                maker_objects: dict[str, Maker] = {}
                for ext_id, o in unique_orders.items():
                    stmt = select(Maker).where(
                        Maker.exchange == exchange,
                        Maker.external_id == ext_id,
                    )
                    maker = session.execute(stmt).scalar_one_or_none()
                    if maker is None:
                        maker = Maker(
                            exchange=exchange,
                            external_id=ext_id,
                            nickname=o.maker_nickname,
                            total_orders=o.trade_count,
                            completion_rate=o.completion_rate,
                            is_merchant=getattr(o, "is_merchant", False),
                            first_seen=now,
                            last_seen=now,
                        )
                        session.add(maker)
                    else:
                        maker.nickname = o.maker_nickname
                        maker.total_orders = o.trade_count
                        maker.completion_rate = o.completion_rate
                        maker.is_merchant = getattr(o, "is_merchant", False)
                        maker.last_seen = now
                    maker_objects[ext_id] = maker

                session.flush()  # assigns .id to new makers

                maker_id_by_external = {ext_id: m.id for ext_id, m in maker_objects.items()}

                # Create Snapshot
                snapshot = Snapshot(
                    exchange=exchange,
                    asset=asset,
                    fiat=fiat,
                    trade_type=trade_type,
                    is_deep=is_deep,
                    collected_at=now,
                    order_count=len(orders),
                )
                session.add(snapshot)
                session.flush()  # assigns snapshot.id

                # Create Orders
                db_orders = [
                    Order(
                        snapshot_id=snapshot.id,
                        maker_id=maker_id_by_external[o.external_id],
                        price=o.price,
                        min_amount=o.min_amount,
                        max_amount=o.max_amount,
                        available_amount=o.available_amount,
                        payment_methods=json.dumps(o.payment_methods, ensure_ascii=False),
                    )
                    for o in orders
                ]
                session.add_all(db_orders)
                saved_count = len(db_orders)
                snapshot_id = snapshot.id

            _logger.info(
                "БД: сохранено %d ордеров (snapshot_id=%d) [%s]",
                saved_count, snapshot_id, label,
            )
            return saved_count

        except Exception as exc:
            _logger.error("[DB_SAVE_ERROR] %s: %s", label, exc, exc_info=True)
            return 0

    def collect_all(self, rows: int, is_deep: bool = False) -> None:
        """Collect all configured pairs and save to DB."""
        ts = now_kyiv().strftime("%H:%M:%S")
        _logger.info("=== Цикл сбора [%s] rows=%d is_deep=%s ===", ts, rows, is_deep)

        total_saved = 0
        for exchange in ["binance", "bybit"]:
            for asset, fiat in self.cfg.pairs:
                for trade_type in self.cfg.trade_types:
                    orders = self._collect_pair(exchange, asset, fiat, trade_type, rows)
                    if orders:
                        total_saved += self._save_to_db(
                            exchange, asset, fiat, trade_type, orders, is_deep,
                        )
                    _pause(self.cfg)

        _logger.info(
            "=== Цикл завершён [%s] — сохранено в БД: %d ордеров ===",
            now_kyiv().strftime("%H:%M:%S"), total_saved,
        )

    def collect_basic(self) -> None:
        self.collect_all(self.cfg.basic_rows, is_deep=False)

    def collect_deep(self) -> None:
        self.collect_all(self.cfg.deep_rows, is_deep=True)
