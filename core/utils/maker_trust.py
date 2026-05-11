"""Класифікація мейкерів за надійністю на основі їхньої статистики."""
from __future__ import annotations

from enum import Enum


class TrustLevel(str, Enum):
    EXPERT = "expert"   # ★ зелений  — досвідчений
    NORMAL = "normal"   # · жовтий   — середній
    NOVICE = "novice"   # ! червоний — новачок або слабкий
    UNKNOWN = "unknown" # ? сірий    — немає даних


# Пороги (включно)
_EXPERT_MIN_ORDERS = 500
_EXPERT_MIN_RATE   = 95.0
_NORMAL_MIN_ORDERS = 50
_NORMAL_MIN_RATE   = 80.0


def classify_maker(total_orders: int, completion_rate: float) -> TrustLevel:
    """Визначає рівень довіри до мейкера."""
    if total_orders <= 0:
        return TrustLevel.UNKNOWN
    if total_orders >= _EXPERT_MIN_ORDERS and completion_rate >= _EXPERT_MIN_RATE:
        return TrustLevel.EXPERT
    if total_orders >= _NORMAL_MIN_ORDERS and completion_rate >= _NORMAL_MIN_RATE:
        return TrustLevel.NORMAL
    return TrustLevel.NOVICE


# Символ і колір для rich
_TRUST_SYMBOL = {
    TrustLevel.EXPERT:  ("★", "green"),
    TrustLevel.NORMAL:  ("·", "yellow"),
    TrustLevel.NOVICE:  ("!", "red"),
    TrustLevel.UNKNOWN: ("?", "dim"),
}

MERCHANT_MARK = "⊕"


def trust_label(total_orders: int, completion_rate: float) -> str:
    """Rich-рядок з символом рівня довіри, наприклад '[green]★[/green]'."""
    level = classify_maker(total_orders, completion_rate)
    symbol, color = _TRUST_SYMBOL[level]
    return f"[{color}]{symbol}[/{color}]"


def format_nickname(
    nickname: str,
    total_orders: int,
    completion_rate: float,
    is_merchant: bool,
) -> str:
    """Повертає відформатований рядок: 'МІТКА\xa0НІК ⊕'."""
    label = trust_label(total_orders, completion_rate)
    # \xa0 (non-breaking space) prevents Rich from wrapping between symbol and nickname
    merchant = f"\xa0[yellow]{MERCHANT_MARK}[/yellow]" if is_merchant else ""
    return f"{label}\xa0{nickname}{merchant}"
