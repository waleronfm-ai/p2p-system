from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, func, select

from core.database import Maker, Order, Snapshot, get_session


def clear_all() -> None:
    answer = input("Удалить все данные из БД? (yes/no): ").strip().lower()
    if answer != "yes":
        print("Отменено.")
        return

    with get_session() as session:
        n_orders = session.execute(select(func.count()).select_from(Order)).scalar() or 0
        n_snapshots = session.execute(select(func.count()).select_from(Snapshot)).scalar() or 0
        n_makers = session.execute(select(func.count()).select_from(Maker)).scalar() or 0

        print(f"Будет удалено: {n_orders} ордеров, {n_snapshots} снимков, {n_makers} мейкеров")

        session.execute(delete(Order))
        session.execute(delete(Snapshot))
        session.execute(delete(Maker))

    print("БД очищена.")


if __name__ == "__main__":
    clear_all()
