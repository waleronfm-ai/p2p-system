import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.database import init_db
from core.utils.logger import get_logger

logger = get_logger("init_db")

if __name__ == "__main__":
    init_db()
    logger.info("БД инициализирована")
