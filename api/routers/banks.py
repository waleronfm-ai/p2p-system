from fastapi import APIRouter

from core.banks.registry import _REGISTRY
from api.schemas import BankListItem, BanksResponse

router = APIRouter(tags=["banks"])


@router.get("/banks", response_model=BanksResponse, summary="Справочник банков с уровнями риска")
def list_banks():
    banks = [
        BankListItem(
            name=entry["name"],
            risk=entry["risk"].value,
            bybit_ids=sorted(entry["bybit_ids"]),
            binance_keys=list(entry["binance_keys"]),
        )
        for entry in _REGISTRY
    ]
    return BanksResponse(total=len(banks), banks=banks)
