import logging
from rich.logging import RichHandler
from rich.console import Console

_console = Console(stderr=True)
_initialized: set[str] = set()


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if name in _initialized:
        return logger

    try:
        from config.settings import settings
        level = getattr(logging, settings.log_level.upper(), logging.INFO)
    except Exception:
        level = logging.INFO

    logger.setLevel(level)

    if not logger.handlers:
        handler = RichHandler(
            console=_console,
            rich_tracebacks=True,
            show_path=False,
            markup=True,
        )
        handler.setLevel(level)
        logger.addHandler(handler)
        logger.propagate = False

    _initialized.add(name)
    return logger
