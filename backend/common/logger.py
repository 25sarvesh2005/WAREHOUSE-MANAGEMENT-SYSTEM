"""
--------------------------------------------------------------------------------
File        : common/logger.py
Purpose     : Provide centralized application logging.

Responsibilities:
    - Configure stream and rotating-file handlers once per logger.
    - Keep UTC timestamps and safe formatting for backend modules.

Flow:
    Module import
        ->
    get_logger() configures handlers
        ->
    Application modules write structured logs

Used By:
    - main.py
    - common/auth.py
    - core modules

Returns:
    get_logger() -> logging.Logger - Configured logger instance.

Raises:
    OSError: When the log directory cannot be created by the runtime.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import gmtime

from core.config.settings import get_settings

# ---- Logger Factory -----------------------------------------------------------


def get_logger(name: str) -> logging.Logger:
    """
    Return a configured logger for the given module name.

    The logger writes INFO+ records to stdout and DEBUG+ records to a rotating
    file while avoiding duplicate handler registration.

    Args:
        name: Python module name requesting a logger.

    Returns:
        logging.Logger: Configured logger instance.

    Raises:
        OSError: If the logs directory cannot be created.
    """
    settings = get_settings()
    logger = logging.getLogger(name)
    logger.setLevel(settings.log_level)
    logger.propagate = False

    if logger.handlers:
        return logger

    logging.Formatter.converter = gmtime
    formatter = logging.Formatter(
        fmt="%(asctime)sZ %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "warehouse.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    return logger
