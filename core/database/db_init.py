from sqlalchemy import inspect

from core.utils.logger import get_logger

from .base import Base, engine
from . import models  # noqa: F401 — registers ORM classes with Base.metadata

_logger = get_logger("database")


def init_db() -> None:
    existing_before = set(inspect(engine).get_table_names())
    Base.metadata.create_all(engine)
    existing_after = set(inspect(engine).get_table_names())
    created = existing_after - existing_before
    if created:
        _logger.info("Таблиц создано: %d (%s)", len(created), ", ".join(sorted(created)))
    else:
        _logger.info("Таблицы уже существуют: %s", ", ".join(sorted(existing_after)))
