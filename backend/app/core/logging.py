"""Structured application logging setup.

Keeps logging configuration in one place so every module gets consistent
formatting. Every log line automatically carries the current request id
(see `app.core.request_context`) via `RequestContextLogFilter`, so a
single request's log lines can be correlated end to end without every
call site passing it explicitly.

Never logged, anywhere in this application:
  - AWS credentials or any secret/API key
  - full uploaded document contents
  - model chain-of-thought or full prompts containing private user data
  - raw provider/AWS error internals (request ids, stack traces) - those
    are logged via bounded, truncated summaries only (see
    `app.agents.orchestrator._MAX_LOGGED_ERROR_CHARS`)
"""

import logging
import sys

from app.core.config import get_settings
from app.core.request_context import get_request_id

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | request_id=%(request_id)s | %(message)s"


class RequestContextLogFilter(logging.Filter):
    """Injects the current request id into every log record.

    `record.request_id` defaults to "-" outside of a request context (e.g.
    at startup/shutdown, or in a background/test process) so the format
    string above never raises a `KeyError`.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


def configure_logging() -> None:
    """Configure the root logger once, at application startup."""
    settings = get_settings()

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    handler.addFilter(RequestContextLogFilter())

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())
    root_logger.handlers = [handler]

    # Quiet down noisy third-party loggers unless we're actively debugging.
    if not settings.debug:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped logger."""
    return logging.getLogger(name)
