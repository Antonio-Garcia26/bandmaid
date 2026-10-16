"""Shared file logging configuration for the Band-Maid scraper."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import OUTPUT_DIR_NAME


LOGGER_NAME = "bandmaid"
LOG_FILE_NAME = "selenium.log"
MAX_LOG_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 3
LOG_FORMAT = (
    "[%(process)d] [%(asctime)s] %(levelname)s "
    "[%(filename)s:%(lineno)d] ==> %(message)s"
)


def configure_logging() -> logging.Logger:
    """Configure the shared Band-Maid logger and return it."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if not any(getattr(handler, "_bandmaid_file_handler", False) for handler in logger.handlers):
        log_dir = Path(__file__).resolve().parent / OUTPUT_DIR_NAME
        log_dir.mkdir(parents=True, exist_ok=True)

        handler = RotatingFileHandler(
            log_dir / LOG_FILE_NAME,
            maxBytes=MAX_LOG_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
            mode="a",
        )
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        handler._bandmaid_file_handler = True
        logger.addHandler(handler)

    return logger


def get_logger(component: str | None = None) -> logging.Logger:
    """Return a logger under the shared Band-Maid logger namespace."""
    if not component:
        return logging.getLogger(LOGGER_NAME)
    return logging.getLogger(f"{LOGGER_NAME}.{component}")
