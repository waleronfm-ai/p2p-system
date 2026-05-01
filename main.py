from pathlib import Path

from config.settings import settings
from core.utils.logger import get_logger

logger = get_logger("main")

_DB_FILE = Path(__file__).parent / "data" / "p2p.db"


def main() -> None:
    logger.info("[bold green]p2p-system запущен[/bold green]")
    logger.info("Мониторинг P2P курсов USDT/USDC → UAH | Binance & Bybit")
    logger.info("Текущие настройки:")
    logger.info("  database_url                   = %s", settings.database_url)
    logger.info("  log_level                      = %s", settings.log_level)
    logger.info("  tracker_interval_seconds       = %s", settings.tracker_interval_seconds)
    logger.info("  deep_snapshot_interval_seconds = %s", settings.deep_snapshot_interval_seconds)

    if _DB_FILE.exists():
        logger.info("БД найдена: %s", _DB_FILE)
    else:
        logger.warning("БД не найдена. Запусти: python scripts/init_db.py")


if __name__ == "__main__":
    main()
