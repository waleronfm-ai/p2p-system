from dataclasses import dataclass, field
from typing import Literal

TradeType = Literal["BUY", "SELL"]


@dataclass
class TrackerConfig:
    # Pairs: (asset, fiat)
    pairs: list[tuple[str, str]] = field(default_factory=lambda: [
        ("USDT", "UAH"),
        ("USDC", "UAH"),
    ])
    trade_types: list[TradeType] = field(default_factory=lambda: ["BUY", "SELL"])

    # Basic collection
    basic_rows: int = 20
    basic_interval_seconds: int = 60
    basic_jitter_seconds: int = 15

    # Deep snapshot
    deep_rows: int = 100
    deep_interval_seconds: int = 900
    deep_jitter_seconds: int = 30

    # Anti-detection: random pause between exchange requests
    min_pause_seconds: float = 1.5
    max_pause_seconds: float = 4.0

    # Retry / exponential backoff
    max_retries: int = 3
    retry_base_delay: float = 2.0
    retry_max_delay: float = 30.0


DEFAULT_CONFIG = TrackerConfig()
