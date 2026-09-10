"""Per-request context propagated into log records.

A single `contextvars.ContextVar` holds the current request id so every
log line emitted while handling a request can include it, without every
call site having to thread it through manually. `RequestIdMiddleware`
(see `app.main`) is the only thing that sets it; `RequestContextLogFilter`
(see `app.core.logging`) is the only thing that reads it back out for the
log formatter.

Deliberately minimal: this holds only a request id, never request/response
bodies, headers, or any user content - see `app.core.logging`'s module
docstring for what must never be logged.
"""

import uuid
from contextvars import ContextVar

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# A client-supplied request id must look like this to be trusted and
# echoed back rather than replaced - bounded length, restricted character
# set, so an attacker can't smuggle arbitrary/oversized data into logs via
# this header.
_MAX_REQUEST_ID_LENGTH = 128
_ALLOWED_REQUEST_ID_CHARS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_."
)


def generate_request_id() -> str:
    return str(uuid.uuid4())


def is_valid_client_request_id(candidate: str | None) -> bool:
    """Whether a client-supplied request id is safe to trust and reuse."""
    if not candidate:
        return False
    if len(candidate) > _MAX_REQUEST_ID_LENGTH:
        return False
    return all(char in _ALLOWED_REQUEST_ID_CHARS for char in candidate)


def set_request_id(request_id: str) -> None:
    _request_id_var.set(request_id)


def get_request_id() -> str | None:
    return _request_id_var.get()
