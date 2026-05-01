from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Maker(Base):
    __tablename__ = "makers"
    __table_args__ = (
        UniqueConstraint("exchange", "external_id", name="uq_maker_exchange_external_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    exchange: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str] = mapped_column(String(100))
    nickname: Mapped[str] = mapped_column(String(100))
    total_orders: Mapped[int] = mapped_column(Integer, default=0)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0)
    is_merchant: Mapped[bool] = mapped_column(Boolean, default=False)
    first_seen: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    last_seen: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))

    orders: Mapped[list["Order"]] = relationship(back_populates="maker")


class Snapshot(Base):
    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    exchange: Mapped[str] = mapped_column(String(20))
    asset: Mapped[str] = mapped_column(String(10))
    fiat: Mapped[str] = mapped_column(String(10))
    trade_type: Mapped[str] = mapped_column(String(10))
    is_deep: Mapped[bool] = mapped_column(Boolean, default=False)
    collected_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    order_count: Mapped[int] = mapped_column(Integer, default=0)

    orders: Mapped[list["Order"]] = relationship(back_populates="snapshot")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"))
    maker_id: Mapped[int] = mapped_column(ForeignKey("makers.id"))
    price: Mapped[float] = mapped_column(Float)
    min_amount: Mapped[float] = mapped_column(Float)
    max_amount: Mapped[float] = mapped_column(Float)
    available_amount: Mapped[float] = mapped_column(Float)
    payment_methods: Mapped[str] = mapped_column(Text, default="[]")

    snapshot: Mapped["Snapshot"] = relationship(back_populates="orders")
    maker: Mapped["Maker"] = relationship(back_populates="orders")
