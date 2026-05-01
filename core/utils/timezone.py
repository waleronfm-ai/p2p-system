from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

_KYIV = ZoneInfo("Europe/Kyiv")


def now_kyiv() -> datetime:
    return datetime.now(_KYIV)


def to_kyiv(dt: datetime) -> datetime:
    """Convert a UTC-aware datetime to Europe/Kyiv."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(_KYIV)


def format_kyiv(dt: datetime, fmt: str = "%H:%M:%S") -> str:
    return to_kyiv(dt).strftime(fmt)
