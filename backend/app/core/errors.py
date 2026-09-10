"""Application-level exceptions and their HTTP translation.

Route handlers raise these instead of building HTTPException objects inline,
and instead of leaking internal details (stack traces, exception messages
from third-party libraries) back to API clients.

Every error response uses one standardized shape:

    {"error": {"code": "...", "message": "...", "request_id": "..."}}

`code` is a stable, machine-readable identifier (e.g.
"ANALYSIS_NOT_FOUND") a frontend can branch on without parsing prose;
`message` is the human-readable detail; `request_id` lets a caller cite
the exact request when reporting an issue, correlating with server-side
logs (see `app.core.request_context`). Field also kept as top-level
`detail` for backward compatibility with existing API consumers/tests
that only read that key - see `JSONResponse` construction below.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.core.request_context import get_request_id

logger = get_logger(__name__)


class AppError(Exception):
    """Base class for expected, handled application errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "BAD_REQUEST"
    detail: str = "Invalid request."

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"
    detail = "Resource not found."


class ValidationError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "VALIDATION_ERROR"
    detail = "Validation error."


class ConflictError(AppError):
    """Raised when a conditional write loses a race (e.g. stale update)."""

    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"
    detail = "The resource was modified by another request. Please retry."


class UnsupportedMediaTypeError(AppError):
    """Raised when an uploaded file's extension/content isn't a supported type."""

    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    code = "UNSUPPORTED_MEDIA_TYPE"
    detail = "Unsupported file type."


class PayloadTooLargeError(AppError):
    """Raised when an uploaded file exceeds the configured size limit."""

    status_code = status.HTTP_413_CONTENT_TOO_LARGE
    code = "PAYLOAD_TOO_LARGE"
    detail = "File is too large."


class RepositoryError(AppError):
    """Raised when the persistence layer fails for reasons outside caller control.

    Never carries the underlying AWS error message/request id - those are
    logged server-side only, so nothing about the database internals leaks
    to API clients.
    """

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "STORAGE_ERROR"
    detail = "A storage error occurred. Please try again."


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    """Build the standardized error envelope.

    `detail` is included alongside `error` purely so existing tests/
    consumers written against the earlier `{"detail": ...}` shape keep
    working unchanged - new consumers should read `error.message`.
    """
    request_id = get_request_id()
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {"code": code, "message": message, "request_id": request_id},
            "detail": message,
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers so every error returns a consistent JSON shape."""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI's own request-schema validation (bad query params, bad
        # JSON body shape, etc.) - never retried automatically by clients,
        # per the "do not blindly retry validation errors" principle.
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "VALIDATION_ERROR",
            "The request could not be validated.",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        # Log the real cause server-side, but never echo internals to the client.
        logger.exception("Unhandled exception while processing request", exc_info=exc)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", "Internal server error."
        )
