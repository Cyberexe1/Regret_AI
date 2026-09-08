"""Structured application logging setup.

Keeps logging configuration in one place so every module gets consistent
formatting. Deliberately avoids logging request/response bodies, since those
may contain user-submitted decision text or, eventually, credentials.
"""

import logging
import sys

from app.core.config import get_settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging() -> None:
    """Configure the root logger once, at application startup."""
    settings = get_settings()

    logging.basicConfig(
        level=settings.log_level.upper(),
        format=_LOG_FORMAT,
        stream=sys.stdout,
        force=True,
    )

    # Quiet down noisy third-party loggers unless we're actively debugging.
    if not settings.debug:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name)
