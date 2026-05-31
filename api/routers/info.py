import os
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from config.settings import settings
from core.database import Maker, Order, Snapshot, get_session
from core.utils.timezone import now_kyiv, to_kyiv

router = APIRouter()


@router.get("/info")
def project_info():
    with get_session() as session:
        snapshot_count = session.execute(select(func.count(Snapshot.id))).scalar_one()
        order_count = session.execute(select(func.count(Order.id))).scalar_one()
        maker_count = session.execute(select(func.count(Maker.id))).scalar_one()

        latest_snapshot = session.execute(
            select(Snapshot.collected_at).order_by(Snapshot.collected_at.desc()).limit(1)
        ).scalar_one_or_none()

    return {
        "project": "p2p-system",
        "version": "0.3.0",
        "description": "P2P crypto price monitoring: Binance + Bybit / USDT + USDC / UAH",
        "exchanges": ["Binance", "Bybit"],
        "assets": ["USDT", "USDC"],
        "fiat": "UAH",
        "stats": {
            "snapshots": snapshot_count,
            "orders": order_count,
            "makers": maker_count,
            "latest_snapshot": (
                now_kyiv().isoformat() if latest_snapshot is None
                else latest_snapshot.astimezone().isoformat()
            ),
        },
        "server_time": now_kyiv().isoformat(),
    }


class TrackerHealthResponse(BaseModel):
    tracker_alive: bool
    minutes_since_last_snapshot: float | None
    last_snapshot_at: str | None
    snapshots_last_hour: int
    orders_last_hour: int
    total_snapshots: int
    total_orders: int
    db_size_mb: float
    server_time: str


@router.get("/info/tracker-health", response_model=TrackerHealthResponse)
def tracker_health():
    db_path = settings.database_url.removeprefix("sqlite:///")
    db_size_mb = round(os.path.getsize(db_path) / 1_048_576, 2) if os.path.exists(db_path) else 0.0

    with get_session() as session:
        latest_at: datetime | None = session.execute(
            select(Snapshot.collected_at).order_by(Snapshot.collected_at.desc()).limit(1)
        ).scalar_one_or_none()

        if latest_at is None:
            total_snapshots = session.execute(select(func.count(Snapshot.id))).scalar_one()
            total_orders = session.execute(select(func.count(Order.id))).scalar_one()
            return TrackerHealthResponse(
                tracker_alive=False,
                minutes_since_last_snapshot=None,
                last_snapshot_at=None,
                snapshots_last_hour=0,
                orders_last_hour=0,
                total_snapshots=total_snapshots,
                total_orders=total_orders,
                db_size_mb=db_size_mb,
                server_time=now_kyiv().isoformat(),
            )

        if latest_at.tzinfo is None:
            latest_at = latest_at.replace(tzinfo=UTC)
        now_utc = datetime.now(UTC)
        minutes_since = round((now_utc - latest_at).total_seconds() / 60, 1)
        tracker_alive = minutes_since < 5

        one_hour_ago = now_utc - timedelta(hours=1)

        snapshots_last_hour: int = session.execute(
            select(func.count(Snapshot.id)).where(Snapshot.collected_at >= one_hour_ago)
        ).scalar_one()

        snap_ids_subq = select(Snapshot.id).where(Snapshot.collected_at >= one_hour_ago).scalar_subquery()
        orders_last_hour: int = session.execute(
            select(func.count(Order.id)).where(Order.snapshot_id.in_(snap_ids_subq))
        ).scalar_one()

        total_snapshots: int = session.execute(select(func.count(Snapshot.id))).scalar_one()
        total_orders: int = session.execute(select(func.count(Order.id))).scalar_one()

    return TrackerHealthResponse(
        tracker_alive=tracker_alive,
        minutes_since_last_snapshot=minutes_since,
        last_snapshot_at=to_kyiv(latest_at).isoformat(),
        snapshots_last_hour=snapshots_last_hour,
        orders_last_hour=orders_last_hour,
        total_snapshots=total_snapshots,
        total_orders=total_orders,
        db_size_mb=db_size_mb,
        server_time=now_kyiv().isoformat(),
    )
