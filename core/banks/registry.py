"""Справочник украинских банків з мітками ризику для P2P-торгівлі.

Джерела:
- Bybit payment type IDs: /fiat/otc/configuration/queryAllPaymentList
- Binance payment method names: строкові назви у відповіді API
- Ризик-мітки: практика P2P-спільноти (блокування рахунків за операції з крипто)
"""
from __future__ import annotations

import json
from enum import Enum


class RiskLevel(str, Enum):
    """Рівень ризику банку для P2P."""
    SAFE    = "safe"     # Зелений — рекомендується
    CAUTION = "caution"  # Жовтий — обережно
    AVOID   = "avoid"    # Червоний — уникати
    UNKNOWN = "unknown"  # Сірий — не класифіковано


# Кожен запис:
#   name          — відображуване ім'я
#   risk          — рівень ризику
#   bybit_ids     — множина Bybit paymentType ID (рядки)
#   binance_keys  — підрядки (lowercase), що зустрічаються у Binance payment_methods
_REGISTRY: list[dict] = [
    # ── SAFE ──────────────────────────────────────────────────────────────────
    {
        "name": "ПриватБанк",
        "risk": RiskLevel.SAFE,
        "bybit_ids": {"60", "660", "661"},        # 60=Privat Bank, 660=card, 661=IBAN
        "binance_keys": ["privat"],
    },
    {
        "name": "Монобанк",
        "risk": RiskLevel.SAFE,
        "bybit_ids": {"43", "659"},               # 43=card, 659=IBAN
        "binance_keys": ["monobank"],
    },
    {
        "name": "А-Банк",
        "risk": RiskLevel.SAFE,
        "bybit_ids": {"1"},
        "binance_keys": ["a-bank"],
    },
    {
        "name": "Raiffeisen Bank Aval",
        "risk": RiskLevel.SAFE,
        "bybit_ids": {"63", "64"},                # 63=Raiffeisen Bank Aval, 64=Raiffeisenbank
        "binance_keys": ["raiffeisen"],
    },
    {
        "name": "Sense Bank",
        "risk": RiskLevel.SAFE,
        "bybit_ids": {"623"},
        "binance_keys": ["sense"],
    },
    {
        "name": "Izibank",
        "risk": RiskLevel.SAFE,
        "bybit_ids": {"544"},
        "binance_keys": ["izibank"],
    },

    # ── CAUTION ───────────────────────────────────────────────────────────────
    {
        "name": "ПУМБ",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": {"61"},
        "binance_keys": ["pumb"],
    },
    {
        "name": "OTP Bank",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": {"49"},
        "binance_keys": ["otp"],
    },
    {
        "name": "Укрсиббанк",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": {"80"},
        "binance_keys": ["ukrsibbank"],
    },
    {
        "name": "Tascombank",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": {"74"},
        "binance_keys": ["tascombank"],
    },
    {
        "name": "Влас. рахунок",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": {"545"},
        "binance_keys": ["vlasnyi"],
    },
    {
        "name": "Idea Bank",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": {"31"},
        "binance_keys": ["idea bank"],
    },
    {
        "name": "Credit Agricole",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": {"22"},
        "binance_keys": ["credit agricole"],
    },
    {
        "name": "KredoBank",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": {"34"},
        "binance_keys": ["kredobank"],
    },
    {
        "name": "Alliance Bank",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": set(),                       # не зустрічається у Bybit в наших даних
        "binance_keys": ["alliance"],
    },
    {
        "name": "Bank Pivdenny",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": {"13"},
        "binance_keys": ["pivdenny"],
    },
    {
        "name": "Ukrgasbank",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": {"548"},
        "binance_keys": ["ukrgasbank"],
    },
    {
        "name": "Pravex Bank",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": {"547"},
        "binance_keys": ["pravex"],
    },
    {
        "name": "Credit Dnipro",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": {"625"},
        "binance_keys": ["credit dnipro"],
    },
    {
        "name": "Accordbank",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": set(),
        "binance_keys": ["accordbank"],
    },
    {
        "name": "Ukreximbank",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": set(),
        "binance_keys": ["ukreximbank"],
    },
    {
        "name": "Unex Bank",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": {"624"},
        "binance_keys": ["unex"],
    },
    {
        "name": "RADABANK",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": set(),
        "binance_keys": ["radabank"],
    },
    {
        "name": "Forward Bank",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": {"546"},
        "binance_keys": ["forward"],
    },
    {
        "name": "Piraeus Bank",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": set(),
        "binance_keys": ["piraeus"],
    },
    {
        "name": "Crystalbank",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": set(),
        "binance_keys": ["crystalbank"],
    },
    {
        "name": "Sportbank",
        "risk": RiskLevel.CAUTION,
        "bybit_ids": set(),
        "binance_keys": ["sportbank"],
    },

    # ── AVOID ─────────────────────────────────────────────────────────────────
    {
        "name": "Ощадбанк",
        "risk": RiskLevel.AVOID,
        "bybit_ids": {"46"},
        "binance_keys": ["oschadbank"],
    },
]

# Швидкі індекси для O(1) пошуку
_BYBIT_ID_INDEX: dict[str, dict] = {}
_BINANCE_KEY_INDEX: list[tuple[str, dict]] = []  # (lowercase_key, bank_entry)

for _entry in _REGISTRY:
    for _bid in _entry["bybit_ids"]:
        _BYBIT_ID_INDEX[_bid] = _entry
    for _bk in _entry["binance_keys"]:
        _BINANCE_KEY_INDEX.append((_bk.lower(), _entry))


def _resolve(method: str) -> tuple[str, RiskLevel]:
    """Визначає банк та ризик для одного методу оплати."""
    m = method.strip()
    if not m or m.lower() == "none":
        return ("—", RiskLevel.UNKNOWN)

    # Bybit: числовий ID
    if m.isdigit():
        entry = _BYBIT_ID_INDEX.get(m)
        if entry:
            return (entry["name"], entry["risk"])
        # Нефінансові/generic методи Bybit
        _GENERIC_BYBIT: dict[str, str] = {
            "14": "Bank Transfer", "18": "Cash/Bank",
            "40": "Mobile Top-up", "90": "Cash",
        }
        label = _GENERIC_BYBIT.get(m, f"Bybit#{m}")
        return (label, RiskLevel.UNKNOWN)

    # Binance: текстова назва
    m_lower = m.lower()
    for key, entry in _BINANCE_KEY_INDEX:
        if key in m_lower:
            return (entry["name"], entry["risk"])

    # Binance: не-банківські текстові методи
    if any(s in m_lower for s in ("bank transfer", "cash", "mobile top")):
        return ("—", RiskLevel.UNKNOWN)

    return (m, RiskLevel.UNKNOWN)


# ── Публічний API ─────────────────────────────────────────────────────────────

def classify_payment_methods(methods: list[str]) -> list[tuple[str, RiskLevel]]:
    """Класифікує список методів оплати. Повертає список (назва_банку, ризик)."""
    seen: set[str] = set()
    result: list[tuple[str, RiskLevel]] = []
    for m in methods:
        name, risk = _resolve(m)
        if name != "—" and name not in seen:
            seen.add(name)
            result.append((name, risk))
    return result


_RISK_PRIORITY = {
    RiskLevel.AVOID:   3,
    RiskLevel.CAUTION: 2,
    RiskLevel.UNKNOWN: 1,
    RiskLevel.SAFE:    0,
}


def get_worst_risk(methods: list[str]) -> tuple[str, RiskLevel]:
    """Повертає (назва, ризик) найгіршого банку зі списку методів оплати.

    Якщо методів немає або всі невідомі — повертає ('—', UNKNOWN).
    """
    classified = classify_payment_methods(methods)
    if not classified:
        return ("—", RiskLevel.UNKNOWN)
    return max(classified, key=lambda x: _RISK_PRIORITY[x[1]])
