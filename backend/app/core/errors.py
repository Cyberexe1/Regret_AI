"""Application-level exceptions and their HTTP translation.

Route handlers raise these instead of building HTTPException objects inline,
and instead of leaking internal details (stack traces, exception messages
from third-party libraries) back to API clients.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base class for expected, handled application errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    detail: str = "Invalid request."

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found."


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation error."


class ConflictError(AppError):
    """Raised when a conditional write loses a race (e.g. stale update)."""

    status_code = status.HTTP_409_CONFLICT
    detail = "The resource was modified by another request. Please retry."


class RepositoryError(AppError):
    """Raised when the persistence layer fails for reasons outside caller control.

    Never carries the underlying AWS error message/request id - those are
    logged server-side only, so nothing about the database internals leaks
    to API clients.
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "A storage error occurred. Please try again."


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers so every error returns a consistent JSON shape."""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        # Log the real cause server-side, but never echo internals to the client.
        logger.exception("Unhandled exception while processing request", exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error."},
        )
