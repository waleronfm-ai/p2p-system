from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from core.database import Maker, get_session
from core.utils.maker_trust import classify_maker
from api.schemas import MakerDetail

router = APIRouter()


@router.get("/makers/{maker_id}", response_model=MakerDetail, summary="Информация о мейкере по ID")
def get_maker(maker_id: int):
    with get_session() as session:
        maker = session.scalar(select(Maker).where(Maker.id == maker_id))
    if maker is None:
        raise HTTPException(status_code=404, detail=f"Maker {maker_id} not found")
    return MakerDetail(
        id=maker.id,
        exchange=maker.exchange,
        external_id=maker.external_id,
        nickname=maker.nickname,
        total_orders=maker.total_orders,
        completion_rate=maker.completion_rate,
        is_merchant=maker.is_merchant,
        trust_level=classify_maker(maker.total_orders, maker.completion_rate).value,
        first_seen=maker.first_seen,
        last_seen=maker.last_seen,
    )
