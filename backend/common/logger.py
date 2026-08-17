"""
Centralized application logging with stream and rotating-file handlers.

Log records automatically include the active request correlation ID from
REQUEST_ID_CTX_VAR so every log line produced during a request is traceable
without passing the ID through function signatures.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import gmtime

from core.config.settings import get_settings


class _RequestIDFilter(logging.Filter):
    """Inject the active request correlation ID into every log record.

    Reads the ID from the REQUEST_ID_CTX_VAR context variable set by
    RequestIDMiddleware. Falls back to '-' when no request context is active
    (e.g. during startup, background jobs, or tests).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Attach request_id attribute to the log record.

        Args:
            record: Log record to augment.

        Returns:
            bool: Always True — every record is allowed through.
        """
        try:
            # Import here to avoid a circular import at module load time.
            from common.request_id import REQUEST_ID_CTX_VAR  # noqa: PLC0415

            record.request_id = REQUEST_ID_CTX_VAR.get("-")
        except Exception:  # noqa: BLE001
            record.request_id = "-"
        return True


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name.

    The logger writes INFO+ records to stdout and DEBUG+ records to a rotating
    file while avoiding duplicate handler registration. Every emitted record
    includes the active ``X-Request-ID`` correlation value.

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
    # Include request_id in every log line for production traceability.
    formatter = logging.Formatter(
        fmt="%(asctime)sZ %(levelname)s [%(name)s] [rid=%(request_id)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(_RequestIDFilter())

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
    file_handler.addFilter(_RequestIDFilter())

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    return logger
