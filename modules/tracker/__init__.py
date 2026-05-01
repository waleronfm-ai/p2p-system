from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.utils.logger import get_logger
from .collector import Collector
from .config import DEFAULT_CONFIG

_logger = get_logger("tracker")


def run_tracker() -> None:
    cfg = DEFAULT_CONFIG
    collector = Collector(cfg)

    _logger.info("Трекер стартует. Пары: %s | Интервал базовый: %ds (jitter ±%ds)",
                 cfg.pairs, cfg.basic_interval_seconds, cfg.basic_jitter_seconds)

    scheduler = BlockingScheduler(timezone=ZoneInfo("Europe/Kyiv"))

    scheduler.add_job(
        collector.collect_basic,
        trigger=IntervalTrigger(
            seconds=cfg.basic_interval_seconds,
            jitter=cfg.basic_jitter_seconds,
        ),
        id="collect_basic",
        name="Базовый сбор (топ-20)",
        next_run_time=datetime.now(UTC),   # первый запуск немедленно
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        collector.collect_deep,
        trigger=IntervalTrigger(
            seconds=cfg.deep_interval_seconds,
            jitter=cfg.deep_jitter_seconds,
        ),
        id="collect_deep",
        name="Глубокий снимок (топ-100)",
        max_instances=1,
        coalesce=True,
    )

    _logger.info("Планировщик запущен. Ctrl+C для остановки.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        _logger.info("Трекер остановлен.")


__all__ = ["run_tracker"]
