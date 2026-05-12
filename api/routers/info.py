from fastapi import APIRouter
from sqlalchemy import func, select

from core.database import Maker, Order, Snapshot, get_session
from core.utils.timezone import now_kyiv

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
