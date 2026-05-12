from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import text

from core.database import get_session
from core.utils.timezone import format_kyiv

router = APIRouter()


@router.get("/health")
def health_check():
    db_status = "ok"
    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "ok",
        "timestamp": format_kyiv(datetime.now(UTC)),
        "db": db_status,
    }
