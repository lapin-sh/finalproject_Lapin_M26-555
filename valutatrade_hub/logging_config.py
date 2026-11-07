"""Настройка логирования приложения."""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_FORMAT = "%(levelname)s %(asctime)s %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
MAX_LOG_BYTES = 512 * 1024
BACKUP_COUNT = 3
LOGGERS = ("actions", "parser")


def setup_logging(logs_dir="logs", level=logging.INFO):
    """Настраивает логгеры actions и parser с ротацией файлов."""
    os.makedirs(logs_dir, exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    for name in LOGGERS:
        logger = logging.getLogger(name)
        logger.setLevel(level)
        if logger.handlers:
            continue
        handler = RotatingFileHandler(
            os.path.join(logs_dir, f"{name}.log"),
            maxBytes=MAX_LOG_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
